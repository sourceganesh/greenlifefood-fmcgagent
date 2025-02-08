from typing import List, Optional
from models.config_loader import ConfigLoader
from models.product import Product

class ProductCatalog:
    def __init__(self, config_loader: ConfigLoader):
        self.products = {}
        product_data = config_loader.get_config("products")
        # as discussed earlier, the data should be more consistent, we don't need a two layered dataset
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
    
    # what happens when the product doesn't exist?
    def get_product(self, product_id: str) -> Optional[Product]:
        return self.products.get(product_id)

    def get_all_products(self) -> List[Product]:
        return list(self.products.values())
    
    def get_products_by_category(self, category: str) -> List[Product]:
        return [p for p in self.products.values() if p.category.lower() == category.lower()] # this completely defeats the point the current dataset! We are iterating over the products to match the category, and we don't have a mechanism to simply return category wise products
    
    # this function seems unused
    def search_products(self, search_term: str) -> List[Product]:
        return [p for p in self.products.values() 
                if search_term.lower() in p.name.lower() or 
                   search_term.lower() in p.description.lower()]