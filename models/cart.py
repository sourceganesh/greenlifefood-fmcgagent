from dataclasses import dataclass
from typing import List

from models.cart_item import CartItem


@dataclass
class Cart:
    items: List[CartItem]
    total: float
    status: str

    # We should include methods for changing the cart within the cart