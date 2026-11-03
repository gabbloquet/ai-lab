from dataclasses import dataclass

from exp001_mcp_server.catalog.domain.entities.product import Product
from exp001_mcp_server.catalog.domain.entities.store import Store


@dataclass(frozen=True, slots=True)
class Availability:
    sku: str
    name: str
    store_id: str
    store_name: str
    available: int
    in_stock: bool

    @staticmethod
    def of(product: Product, store: Store, available: int) -> "Availability":
        return Availability(
            sku=product.sku.value,
            name=product.name,
            store_id=store.store_id.value,
            store_name=store.name,
            available=available,
            in_stock=available > 0,
        )
