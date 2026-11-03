from collections.abc import Iterable

from exp001_mcp_server.catalog.domain.catalog import Catalog
from exp001_mcp_server.catalog.domain.entities.product import Product
from exp001_mcp_server.catalog.domain.entities.stock_line import StockLine
from exp001_mcp_server.catalog.domain.entities.store import Store
from exp001_mcp_server.catalog.infra.outbound.memory.in_memory_product_repository import (
    InMemoryProductRepository,
)
from exp001_mcp_server.catalog.infra.outbound.memory.in_memory_stock_repository import (
    InMemoryStockRepository,
)
from exp001_mcp_server.catalog.infra.outbound.memory.in_memory_store_repository import (
    InMemoryStoreRepository,
)


def in_memory_catalog(
    products: Iterable[Product], stores: Iterable[Store], stock_lines: Iterable[StockLine]
) -> Catalog:
    return Catalog(
        InMemoryProductRepository(products),
        InMemoryStoreRepository(stores),
        InMemoryStockRepository(stock_lines),
    )
