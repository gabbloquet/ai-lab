from typing import Annotated

from mcp.server.mcpserver import MCPServer
from mcp.types import CallToolResult, ToolAnnotations
from pydantic import Field

from exp001_mcp_server.catalog.domain.catalog import Catalog
from exp001_mcp_server.catalog.domain.vo.sku_code import SkuCode
from exp001_mcp_server.catalog.domain.vo.store_id import StoreId
from exp001_mcp_server.catalog.infra.inbound.mcp.intent.dto.availability import Availability
from exp001_mcp_server.catalog.infra.inbound.mcp.intent.dto.catalog_search_results import (
    CatalogSearchResults,
)
from exp001_mcp_server.catalog.infra.inbound.mcp.intent.dto.in_stock_alternatives import (
    InStockAlternatives,
)
from exp001_mcp_server.catalog.infra.inbound.mcp.intent.dto.product_details import ProductDetails
from exp001_mcp_server.catalog.infra.inbound.mcp.intent.dto.stores_with_stock import (
    StoresWithStock,
)
from exp001_mcp_server.catalog.infra.inbound.mcp.intent.intent_error_messages import (
    IntentErrorMessages,
)
from exp001_mcp_server.catalog.infra.inbound.mcp.tool_results import ToolResults

READ_ONLY = ToolAnnotations(
    read_only_hint=True, idempotent_hint=True, destructive_hint=False, open_world_hint=False
)

Sku = Annotated[str, Field(description="SKU of the product: P- followed by 5 digits.")]
StoreIdParam = Annotated[str, Field(description="ID of the store: S followed by 2 digits.")]
Query = Annotated[str, Field(description="Words to look for in the product name, brand or type.")]
Category = Annotated[
    str | None,
    Field(description="Department to search in: Audio, Informatique, Maison or Sport."),
]


def register_intent_tools(server: MCPServer, catalog: Catalog) -> None:
    # Enregistrés par ordre alphabétique : le serveur Java publie ses outils dans cet ordre.
    # storeId reste en camelCase : c'est le nom du paramètre dans le schéma, comme en Java.
    results = ToolResults(IntentErrorMessages(catalog).message_for)

    @server.tool(
        name="check_availability",
        description="Returns how many units of a product can be sold in a store"
        " (stock minus reserved units), and whether it is in stock.",
        annotations=READ_ONLY,
    )
    def check_availability(sku: Sku, storeId: StoreIdParam) -> CallToolResult:
        def run() -> Availability:
            product = catalog.require_product(SkuCode(sku))
            store = catalog.require_store(StoreId(storeId))
            line = catalog.stock(product.sku, store.store_id)
            return Availability.of(product, store, line.available if line else 0)

        return results.run(run)

    @server.tool(
        name="find_in_stock_alternative",
        description="Returns up to 3 products of the same type, priced within 20% of the requested"
        " product, that can be sold in the store, closest price first. The list is empty when"
        " there is no such product.",
        annotations=READ_ONLY,
    )
    def find_in_stock_alternative(sku: Sku, storeId: StoreIdParam) -> CallToolResult:
        def run() -> InStockAlternatives:
            product = catalog.require_product(SkuCode(sku))
            store = catalog.require_store(StoreId(storeId))
            return InStockAlternatives.of(catalog.alternatives(product.sku, store.store_id))

        return results.run(run)

    @server.tool(
        name="find_stores_with_stock",
        description="Returns the stores where a product can be sold, with the number of units"
        " available in each store. The list is empty when the product is out of stock everywhere.",
        annotations=READ_ONLY,
    )
    def find_stores_with_stock(sku: Sku) -> CallToolResult:
        def run() -> StoresWithStock:
            product = catalog.require_product(SkuCode(sku))
            return StoresWithStock.of(product, catalog.stores_with_stock(product.sku))

        return results.run(run)

    @server.tool(
        name="get_product_details",
        description="Returns the details of a product from its SKU: name, brand, department, type"
        " and price in euros.",
        annotations=READ_ONLY,
    )
    def get_product_details(sku: Sku) -> CallToolResult:
        return results.run(lambda: ProductDetails.of(catalog.require_product(SkuCode(sku))))

    @server.tool(
        name="search_catalog",
        description="Searches products whose name, brand or type contain every word of the query,"
        " ignoring case and accents. Returns at most 10 products, sorted by name, and the total"
        " number of matches. If total is greater than the number of products returned, refine the"
        " query or use a category.",
        annotations=READ_ONLY,
    )
    def search_catalog(query: Query, category: Category = None) -> CallToolResult:
        return results.run(lambda: CatalogSearchResults.of(catalog.search(query, category)))
