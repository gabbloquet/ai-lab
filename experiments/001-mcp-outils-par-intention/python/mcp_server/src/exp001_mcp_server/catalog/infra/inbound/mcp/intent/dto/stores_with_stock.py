from dataclasses import dataclass

from exp001_mcp_server.catalog.domain.entities.product import Product
from exp001_mcp_server.catalog.domain.entities.store_stock import StoreStock


@dataclass(frozen=True, slots=True)
class StoreAvailability:
    store_id: str
    name: str
    city: str
    available: int


@dataclass(frozen=True, slots=True)
class StoresWithStock:
    sku: str
    name: str
    stores: list[StoreAvailability]

    @staticmethod
    def of(product: Product, stores: list[StoreStock]) -> "StoresWithStock":
        return StoresWithStock(
            sku=product.sku.value,
            name=product.name,
            stores=[
                StoreAvailability(
                    store_id=stock.store.store_id.value,
                    name=stock.store.name,
                    city=stock.store.city,
                    available=stock.available,
                )
                for stock in stores
            ],
        )
