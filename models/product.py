from dataclasses import dataclass

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
