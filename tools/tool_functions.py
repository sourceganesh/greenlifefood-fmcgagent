# This is a wrapper of the tool functions, we should consider moving the non ingeral functions of the class to this file completely, and keeping only the core logic with the classes

def get_product_info(category: str = None):
    """Fetch and return product details based on category."""
    if category:
        return f"Fetching products in category: {category}"
    return "Fetching all available products."

def add_to_cart(product_name: str, quantity: int):
    """Simulate adding a product to the cart."""
    return f"Added {quantity} packs of {product_name} to the cart."

def get_cart_summary():
    """Return a summary of the current cart contents."""
    return "Your cart contains multiple items."

def remove_from_cart(product_name: str):
    """Simulate removing a product from the cart."""
    return f"Removed {product_name} from the cart."

def checkout():
    """Simulate checkout process."""
    return "Checkout complete. Your order has been placed!"