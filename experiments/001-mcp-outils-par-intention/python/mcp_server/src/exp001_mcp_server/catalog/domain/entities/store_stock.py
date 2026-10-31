from dataclasses import dataclass

from exp001_mcp_server.catalog.domain.entities.store import Store


@dataclass(frozen=True, slots=True)
class StoreStock:
    store: Store
    available: int
