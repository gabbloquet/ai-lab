from collections.abc import Sequence
from typing import Protocol

from exp001_mcp_server.catalog.domain.entities.product import Product
from exp001_mcp_server.catalog.domain.vo.sku_code import SkuCode


class ProductRepository(Protocol):
    def find_by_sku(self, sku: SkuCode) -> Product | None: ...

    def find_all(self) -> Sequence[Product]: ...
