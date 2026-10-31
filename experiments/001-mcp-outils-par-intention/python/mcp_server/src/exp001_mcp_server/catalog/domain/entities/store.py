from dataclasses import dataclass

from exp001_mcp_server.catalog.domain.vo.store_id import StoreId


@dataclass(frozen=True, slots=True)
class Store:
    store_id: StoreId
    name: str
    city: str
