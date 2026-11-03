from typing import assert_never

from exp001_mcp_server.catalog.domain.catalog import Catalog
from exp001_mcp_server.catalog.domain.errors import (
    DepartmentNotFoundError,
    DomainError,
    InvalidIdentifierError,
    InvalidSearchQueryError,
    ProductNotFoundError,
    StoreNotFoundError,
)
from exp001_mcp_server.catalog.infra.inbound.mcp import known_values


class IntentErrorMessages:
    def __init__(self, catalog: Catalog) -> None:
        self._catalog = catalog

    def message_for(self, error: DomainError) -> str:
        match error:
            case ProductNotFoundError():
                return (
                    f"Product not found: {error.sku}."
                    " Use search_catalog to find the SKU of a product."
                )
            case StoreNotFoundError():
                return (
                    f"Store not found: {error.store_id}."
                    f" Known stores: {known_values.stores(self._catalog)}."
                )
            case DepartmentNotFoundError():
                return (
                    f"Category not found: {error.department}."
                    f" Known categories: {known_values.departments(self._catalog)}."
                )
            case InvalidSearchQueryError():
                return (
                    "Search query must not be blank. Provide at least one word of a product name,"
                    " brand or type. To narrow the results to a department, use category."
                )
            case InvalidIdentifierError():
                return str(error)
            case _:
                assert_never(error)
