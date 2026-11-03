from dataclasses import dataclass

from exp001_mcp_server.catalog.domain.entities.product import Product
from exp001_mcp_server.catalog.infra.inbound.mcp.intent.dto.product_details import ProductDetails

MAX_PRODUCTS = 10
NO_MATCH_HINT = (
    "No product matches every word of the query. The query searches product names, brands"
    " and types; use category to restrict to a department."
)


@dataclass(frozen=True, slots=True)
class CatalogSearchResults:
    total: int
    products: list[ProductDetails]
    hint: str | None = None

    @staticmethod
    def of(matches: list[Product]) -> "CatalogSearchResults":
        return CatalogSearchResults(
            total=len(matches),
            products=[ProductDetails.of(product) for product in matches[:MAX_PRODUCTS]],
            hint=None if matches else NO_MATCH_HINT,
        )
