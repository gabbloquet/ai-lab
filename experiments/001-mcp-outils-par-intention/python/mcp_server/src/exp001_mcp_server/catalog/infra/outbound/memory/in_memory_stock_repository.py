from collections.abc import Iterable

from exp001_mcp_server.catalog.domain.entities.stock_line import StockLine
from exp001_mcp_server.catalog.domain.vo.sku_code import SkuCode
from exp001_mcp_server.catalog.domain.vo.store_id import StoreId


class InMemoryStockRepository:
    def __init__(self, stock_lines: Iterable[StockLine]) -> None:
        self._by_key = {(line.sku, line.store_id): line for line in stock_lines}

    def find(self, sku: SkuCode, store_id: StoreId) -> StockLine | None:
        return self._by_key.get((sku, store_id))
