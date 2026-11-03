from collections.abc import Iterable, Sequence

from exp001_mcp_server.catalog.domain.entities.store import Store
from exp001_mcp_server.catalog.domain.vo.store_id import StoreId


class InMemoryStoreRepository:
    def __init__(self, stores: Iterable[Store]) -> None:
        self._stores = tuple(stores)
        self._by_id = {store.store_id: store for store in self._stores}

    def find_by_id(self, store_id: StoreId) -> Store | None:
        return self._by_id.get(store_id)

    def find_all(self) -> Sequence[Store]:
        return self._stores
