from dataclasses import dataclass

from exp001_mcp_server.catalog.domain.vo.sku_code import SkuCode
from exp001_mcp_server.catalog.domain.vo.store_id import StoreId


@dataclass(frozen=True, slots=True)
class StockLine:
    sku: SkuCode
    store_id: StoreId
    on_hand: int
    reserved: int

    @property
    def available(self) -> int:
        return self.on_hand - self.reserved
