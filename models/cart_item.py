from dataclasses import dataclass

@dataclass
class CartItem:
    product_id: str
    quantity: int
    unit_price: float
    total_price: float

    # total_price seems like a redundant data, and also as the suggested with cart, we should consider updating total_price as a method of the product class
    # would it be helpful to attach an object of the product instead? 
