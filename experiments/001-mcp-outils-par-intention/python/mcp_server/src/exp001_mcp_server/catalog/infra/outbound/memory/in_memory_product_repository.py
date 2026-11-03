from collections.abc import Iterable, Sequence

from exp001_mcp_server.catalog.domain.entities.product import Product
from exp001_mcp_server.catalog.domain.vo.sku_code import SkuCode


class InMemoryProductRepository:
    def __init__(self, products: Iterable[Product]) -> None:
        self._products = tuple(products)
        self._by_sku = {product.sku: product for product in self._products}

    def find_by_sku(self, sku: SkuCode) -> Product | None:
        return self._by_sku.get(sku)

    def find_all(self) -> Sequence[Product]:
        return self._products
