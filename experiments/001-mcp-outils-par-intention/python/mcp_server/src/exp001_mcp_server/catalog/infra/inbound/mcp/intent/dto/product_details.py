from dataclasses import dataclass
from decimal import Decimal

from exp001_mcp_server.catalog.domain.entities.product import Product

EURO = "EUR"


@dataclass(frozen=True, slots=True)
class ProductDetails:
    sku: str
    name: str
    brand: str
    department: str
    type: str
    price: Decimal
    currency: str

    @staticmethod
    def of(product: Product) -> "ProductDetails":
        return ProductDetails(
            sku=product.sku.value,
            name=product.name,
            brand=product.brand,
            department=product.department,
            type=product.type,
            price=product.price,
            currency=EURO,
        )
