# finalapp.py
import streamlit as st
import json
from dataclasses import dataclass
from typing import List, Dict, Optional
from groq import Groq
import logging
from datetime import datetime
from pathlib import Path
from memory import Memory
from context import ContextManager
from tools.tools import tools
from tools.parser import parse_tool_response
# Configuration Loader Class
class ConfigLoader:
    def __init__(self, config_dir: str = "config"):
        self.config_dir = Path(config_dir)
        self.configs = {}
        
        # Create config directory if it doesn't exist
        self.config_dir.mkdir(exist_ok=True)

    def load_all_configs(self):
        """Load all configuration files from the config directory."""
        try:
            for config_file in self.config_dir.glob("*.json"):
                config_name = config_file.stem
                try:
                    with open(config_file, 'r', encoding='utf-8') as f:
                        self.configs[config_name] = json.load(f)
                except Exception as e:
                    logging.error(f"Error loading {config_file}: {str(e)}")
                    raise ValueError(f"Failed to load config file: {config_file}")
            return self.configs
        except Exception as e:
            logging.error(f"Error in load_all_configs: {str(e)}")
            raise

    def get_config(self, config_name: str):
        """Get a specific configuration by name."""
        try:
            if config_name not in self.configs:
                config_file = self.config_dir / f"{config_name}.json"
                if not config_file.exists():
                    raise FileNotFoundError(f"Config file not found: {config_file}")
                try:
                    with open(config_file, 'r', encoding='utf-8') as f:
                        self.configs[config_name] = json.load(f)
                except json.JSONDecodeError as e:
                    logging.error(f"Invalid JSON in {config_file}: {str(e)}")
                    raise
            return self.configs[config_name]
        except Exception as e:
            logging.error(f"Error getting config {config_name}: {str(e)}")
            raise

# Initialize memory and context
memory = Memory()
context_manager = ContextManager()

@dataclass
class Product:
    id: str
    name: str
    description: str
    price: float
    category: str
    unit_size: str
    stock: int
    min_order_quantity: int

@dataclass
class CartItem:
    product_id: str
    quantity: int
    unit_price: float
    total_price: float

@dataclass
class Cart:
    items: List[CartItem]
    total: float
    status: str

class ProductCatalog:
    def __init__(self, config_loader: ConfigLoader):
        self.products = {}
        product_data = config_loader.get_config("products")
        for category, items in product_data.items():
            for product_id, details in items.items():
                self.products[product_id] = Product(
                    id=product_id,
                    name=details["name"],
                    description=details["description"],
                    price=details["price"],
                    category=details["category"],
                    unit_size=details["unit_size"],
                    stock=details["stock"],
                    min_order_quantity=details["min_order_quantity"]
                )
    
    def get_product(self, product_id: str) -> Optional[Product]:
        return self.products.get(product_id)

    def get_all_products(self) -> List[Product]:
        return list(self.products.values())
    
    def get_products_by_category(self, category: str) -> List[Product]:
        return [p for p in self.products.values() if p.category.lower() == category.lower()]
    
    def search_products(self, search_term: str) -> List[Product]:
        return [p for p in self.products.values() 
                if search_term.lower() in p.name.lower() or 
                   search_term.lower() in p.description.lower()]

class CartManager:
    def __init__(self):
        self.cart = Cart(items=[], total=0.0, status="active")

    def add_item(self, product: Product, quantity: int) -> bool:
        if quantity < product.min_order_quantity:
            raise ValueError(f"Minimum order quantity is {product.min_order_quantity} packs")
        
        if product.stock < quantity:
            raise ValueError(f"Insufficient stock. Available: {product.stock} packs")
        
        # Check if item already exists in cart
        for item in self.cart.items:
            if item.product_id == product.id:
                item.quantity += quantity
                item.total_price = item.quantity * item.unit_price
                self._update_total()
                return True
        
        # Add new item
        cart_item = CartItem(
            product_id=product.id,
            quantity=quantity,
            unit_price=product.price,
            total_price=product.price * quantity
        )
        self.cart.items.append(cart_item)
        self._update_total()
        return True

    def remove_item(self, product_id: str) -> bool:
        self.cart.items = [item for item in self.cart.items if item.product_id != product_id]
        self._update_total()
        return True

    def _update_total(self):
        self.cart.total = sum(item.total_price for item in self.cart.items)

    def clear_cart(self):
        self.cart = Cart(items=[], total=0.0, status="active")

    def get_cart_summary(self) -> Dict:
        return {
            "items": [{"product_id": item.product_id, 
                      "quantity": item.quantity,
                      "unit_price": item.unit_price,
                      "total_price": item.total_price} for item in self.cart.items],
            "total": self.cart.total
        }

class ChatBot:
    def __init__(self, api_key: str, config_loader: ConfigLoader):
        self.client = Groq(api_key=api_key)
        self.config_loader = config_loader
        self.model_config = config_loader.get_config("model_config")
        self.system_prompts = config_loader.get_config("system_prompts")
        self.product_catalog = ProductCatalog(config_loader)
        self.cart_manager = CartManager()
        self.conversation_history = []
        
        # Initialize memory with cart state
        memory.update_memory("cart", self.cart_manager)
        context_manager.update_context("last_action", None)

    def _create_context(self) -> str:
        """Create current context for LLM"""
        # Get cart state
        cart = memory.retrieve_memory("cart")
        cart_summary = self.cart_manager.get_cart_summary() if cart else {"items": [], "total": 0}
        
        # Get available products
        products = self.product_catalog.get_all_products()
        product_info = {}
        for product in products:
            product_info[product.id] = {
                "name": product.name,
                "price": product.price,
                "unit_size": product.unit_size,
                "stock": product.stock,
                "min_order": product.min_order_quantity
            }

        return json.dumps({
            "cart": cart_summary,
            "products": product_info,
            "last_action": context_manager.retrieve_context("last_action")
        })

    def process_message(self, user_message: str) -> str:
        # Add message to history
        self.conversation_history.append({"role": "user", "content": user_message})
        
        try:
            # Create context-aware prompt
            system_prompt = f"""You are GreenLife Assistant, helping customers shop for organic Indian food products.

Current Context: {self._create_context()}

Your capabilities:
1. Show available products and their details
2. Add items to cart (check minimum order quantities)
3. Remove items from cart
4. Process checkout
5. Answer questions about products

Guidelines:
- Be concise and natural in responses
- Maintain context of the conversation
- Verify stock before suggesting products
- Guide users through the ordering process
- Keep track of cart state
- Use Indian Rupee (₹) for prices

Previous conversation:
{json.dumps(self.conversation_history[-5:] if len(self.conversation_history) > 0 else [])}

Respond naturally to the user's message. Do not expose technical details or function calls in your response."""

            # Get LLM response
            completion = self.client.chat.completions.create(
                model=self.model_config["model"],
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_message}
                ],
                temperature=self.model_config["temperature"],
                max_tokens=self.model_config["max_tokens"]
            )
            
            response = completion.choices[0].message.content
            
            # Update conversation history and context
            self.conversation_history.append({"role": "assistant", "content": response})
            context_manager.update_context("last_message", user_message)
            context_manager.update_context("last_response", response)
            
            # Detect and execute any tool-based actions based on the user's message
            action_result = self._handle_actions(user_message)
            
            # If tool actions produced a user-friendly result, append it to the model response
            if action_result:
                response = f"{response}\n\n{action_result}"

            return response

        except Exception as e:
            logging.error(f"Error processing message: {str(e)}")
            return "I apologize, but I'm having trouble processing your request. Please try again."

    def _handle_actions(self, user_message: str):
        """Detect and execute tool calls derived from the user's message"""
        try:
            # Ask LLM to analyze the user's message and propose tool calls in XML
            tool_selection = self.client.chat.completions.create(
                model=self.model_config["model"],
                messages=[
                    {
                        "role": "system",
                        "content": f"""{self.system_prompts['base_prompt']}
                        
                        Current context: {self._create_context()}
                        Product format: {self.system_prompts['product_format']}
                        Cart format: {self.system_prompts['cart_format']}
                        
                        Available tools: {json.dumps(tools, indent=2)}
                        
                        Rules for tool usage:
                        1. Use exact product names and prices from the catalog
                        2. Respect minimum order quantities
                        3. Verify stock availability before actions
                        4. Calculate totals based on unit price × quantity
                        5. Format currency as ₹ with 2 decimal places
                        
                        Return tool calls in XML format:
                        <tool>tool_name</tool><arguments>{{json args}}</arguments>"""
                    },
                    {"role": "user", "content": user_message}
                ],
                temperature=0,
                max_tokens=self.model_config["max_tokens"]
            )
            
            # Parse tool calls from LLM response
            tool_calls = parse_tool_response(tool_selection.choices[0].message.content)
            
            # Execute each tool call and collect results
            results = []
            for tool_call in tool_calls:
                try:
                    tool_name = tool_call.get("tool_name")
                    args = tool_call.get("arguments", {})
                    result_msg = self._execute_tool(tool_name, args)
                    if result_msg:
                        results.append(result_msg)
                    # Update context with action
                    context_manager.update_context("last_action", {
                        "tool": tool_name,
                        "arguments": args,
                        "result": result_msg
                    })
                except Exception as e:
                    error_msg = self.system_prompts["error_messages"]["general"]
                    logging.error(f"Error executing tool {tool_call.get('tool_name')}: {str(e)}")
                    results.append(error_msg)
            
            # Update memory with cart state
            memory.update_memory("cart", self.cart_manager)
            
            return "\n".join(results) if results else None
                
        except Exception as e:
            logging.error(f"Error in tool calling: {str(e)}")
            return self.system_prompts["error_messages"]["general"]

    def _execute_tool(self, tool_name: str, args: Dict) -> Optional[str]:
        """Map tool names to concrete operations and return user-friendly messages"""
        try:
            if tool_name == "get_product_info":
                category = args.get("category")
                return self._tool_get_product_info(category)
            elif tool_name == "add_to_cart":
                product_name = args.get("product_name")
                quantity = int(args.get("quantity", 0))
                return self._tool_add_to_cart(product_name, quantity)
            elif tool_name == "remove_from_cart":
                product_name = args.get("product_name")
                return self._tool_remove_from_cart(product_name)
            elif tool_name == "get_cart_summary":
                return self._tool_get_cart_summary()
            elif tool_name == "checkout":
                return self._tool_checkout()
            else:
                logging.warning(f"Unknown tool requested: {tool_name}")
                return None
        except Exception as e:
            logging.error(f"Tool execution error for {tool_name}: {str(e)}")
            return self.system_prompts["error_messages"]["general"]

    def _tool_get_product_info(self, category: Optional[str]) -> str:
        """Return formatted list of products, filtered by category if provided"""
        products = (
            self.product_catalog.get_products_by_category(category)
            if category else self.product_catalog.get_all_products()
        )
        if not products:
            return "No matching products found."
        fmt = self.system_prompts.get("product_format", "• {name} - ₹{price}")
        lines = []
        for p in products:
            line = fmt.format(
                name=p.name,
                description=p.description,
                price=f"{p.price:.2f}",
                unit_size=p.unit_size,
                min_qty=p.min_order_quantity,
            )
            lines.append(line)
        return "\n\n".join(lines)

    def _find_product_by_name(self, product_name: str) -> Optional[Product]:
        if not product_name:
            return None
        name_l = product_name.strip().lower()
        for p in self.product_catalog.get_all_products():
            if p.name.lower() == name_l:
                return p
        return None

    def _tool_add_to_cart(self, product_name: Optional[str], quantity: int) -> str:
        if not product_name or quantity <= 0:
            return self.system_prompts["error_messages"]["general"]
        product = self._find_product_by_name(product_name)
        if not product:
            return self.system_prompts["error_messages"]["product_not_found"]
        try:
            if quantity < product.min_order_quantity:
                return self.system_prompts["error_messages"]["invalid_quantity"].format(
                    min_quantity=product.min_order_quantity
                )
            if product.stock < quantity:
                return self.system_prompts["error_messages"]["out_of_stock"].format(
                    available=product.stock
                )
            self.cart_manager.add_item(product, quantity)
            return f"Added {quantity} pack(s) of {product.name} to your cart.\n\n{self._tool_get_cart_summary()}"
        except Exception as e:
            logging.error(f"Add to cart error: {str(e)}")
            return self.system_prompts["error_messages"]["general"]

    def _tool_remove_from_cart(self, product_name: Optional[str]) -> str:
        if not product_name:
            return self.system_prompts["error_messages"]["general"]
        product = self._find_product_by_name(product_name)
        if not product:
            return self.system_prompts["error_messages"]["product_not_found"]
        try:
            self.cart_manager.remove_item(product.id)
            return f"Removed {product.name} from your cart.\n\n{self._tool_get_cart_summary()}"
        except Exception as e:
            logging.error(f"Remove from cart error: {str(e)}")
            return self.system_prompts["error_messages"]["general"]

    def _tool_get_cart_summary(self) -> str:
        summary = self.cart_manager.get_cart_summary()
        if not summary.get("items"):
            return "Your cart is currently empty."
        items_lines = []
        for item in summary["items"]:
            product = self.product_catalog.get_product(item["product_id"]) if hasattr(self.product_catalog, 'get_product') else None
            name = product.name if product else item["product_id"]
            items_lines.append(f"• {name}: {item['quantity']} pack(s) × ₹{item['unit_price']:.2f} = ₹{item['total_price']:.2f}")
        items_str = "\n".join(items_lines)
        return self.system_prompts["cart_format"].format(items=items_str, total=f"{summary['total']:.2f}")

    def _tool_checkout(self) -> str:
        summary = self.cart_manager.get_cart_summary()
        if not summary.get("items"):
            return "Your cart is empty. Add some products before checkout."
        # Mark as checked out and clear cart
        try:
            self.cart_manager.cart.status = "checked_out"
            total = summary["total"]
            self.cart_manager.clear_cart()
            return f"✅ Checkout complete! Your order total is ₹{total:.2f}."
        except Exception as e:
            logging.error(f"Checkout error: {str(e)}")
            return self.system_prompts["error_messages"]["general"]


def main():
    st.set_page_config(
        page_title="GreenLife Foods Assistant",
        page_icon="🌱",
        layout="wide"
    )
    
    config_loader = ConfigLoader()
    config_loader.load_all_configs()
    ui_config = config_loader.get_config("ui_config")

    # Apply styling
    st.markdown(f"""
    <style>
    .stTextInput > div > div > input {{
        background-color: {ui_config["colors"]["background"]};
        border-color: {ui_config["colors"]["secondary"]};
    }}
    .stButton > button {{
        background-color: {ui_config["colors"]["primary"]};
        color: white;
        border-radius: {ui_config["spacing"]["border_radius"]};
    }}
    .chat-message {{
        padding: {ui_config["spacing"]["chat_padding"]};
        border-radius: {ui_config["spacing"]["border_radius"]};
        margin-bottom: {ui_config["spacing"]["message_margin"]};
        background-color: {ui_config["colors"]["background"]};
    }}
    * {{
        font-family: {ui_config["fonts"]["primary"]}, sans-serif;
    }}
    .main {{
        padding: 2rem;
    }}
    </style>
    """, unsafe_allow_html=True)

    st.title("🌱 GreenLife Foods Assistant")

    # Initialize session state
    if 'chatbot' not in st.session_state:
        st.session_state.chatbot = ChatBot(st.secrets["GROQ_API_KEY"], config_loader)
    if 'messages' not in st.session_state:
        st.session_state.messages = []

    # Chat interface
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

    # Chat input
    if prompt := st.chat_input("How can I help you today?"):
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)

        response = st.session_state.chatbot.process_message(prompt)
        st.session_state.messages.append({"role": "assistant", "content": response})
        with st.chat_message("assistant"):
            st.markdown(response)

if __name__ == "__main__":
    main()
