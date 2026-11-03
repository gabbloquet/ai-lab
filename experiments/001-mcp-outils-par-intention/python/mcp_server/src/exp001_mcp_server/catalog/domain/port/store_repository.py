from collections.abc import Sequence
from typing import Protocol

from exp001_mcp_server.catalog.domain.entities.store import Store
from exp001_mcp_server.catalog.domain.vo.store_id import StoreId


class StoreRepository(Protocol):
    def find_by_id(self, store_id: StoreId) -> Store | None: ...

    def find_all(self) -> Sequence[Store]: ...
