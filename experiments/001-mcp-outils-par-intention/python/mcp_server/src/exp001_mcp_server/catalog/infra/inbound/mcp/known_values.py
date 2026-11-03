from exp001_mcp_server.catalog.domain.catalog import Catalog

MAX_LISTED_STORES = 10
MAX_LISTED_DEPARTMENTS = 5


def stores(catalog: Catalog) -> str:
    known = sorted(catalog.stores(), key=lambda store: store.store_id.value)
    return _listed([f"{store.store_id} ({store.city})" for store in known], MAX_LISTED_STORES)


def departments(catalog: Catalog) -> str:
    return _listed(catalog.departments(), MAX_LISTED_DEPARTMENTS)


def _listed(values: list[str], limit: int) -> str:
    listed = ", ".join(values[:limit])
    others = len(values) - limit
    return f"{listed} and {others} more" if others > 0 else listed
