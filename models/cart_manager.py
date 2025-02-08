from typing import Dict
from models.cart import Cart
from models.cart_item import CartItem
from models.product import Product


class CartManager:
    def __init__(self):
        self.cart = Cart(items=[], total=0.0, status="active")

    def add_item(self, product: Product, quantity: int) -> bool:
        if quantity < product.min_order_quantity:
            raise ValueError(f"Minimum order quantity is {product.min_order_quantity} packs")
        
        if product.stock < quantity:
            raise ValueError(f"Insufficient stock. Available: {product.stock} packs")
        
        for item in self.cart.items:
            if item.product_id == product.id:
                item.quantity += quantity
                item.total_price = item.quantity * item.unit_price
                self._update_total()
                return True
        
        cart_item = CartItem(
            product_id=product.id,
            quantity=quantity,
            unit_price=product.price,
            total_price=product.price * quantity
        )
        self.cart.items.append(cart_item)
        self._update_total() # I think this should lie with the cart model, we should tightly tie the update total to the base model to avoid inconsistencies
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