from typing import Protocol

from exp001_mcp_server.catalog.domain.entities.stock_line import StockLine
from exp001_mcp_server.catalog.domain.vo.sku_code import SkuCode
from exp001_mcp_server.catalog.domain.vo.store_id import StoreId


class StockRepository(Protocol):
    def find(self, sku: SkuCode, store_id: StoreId) -> StockLine | None: ...
