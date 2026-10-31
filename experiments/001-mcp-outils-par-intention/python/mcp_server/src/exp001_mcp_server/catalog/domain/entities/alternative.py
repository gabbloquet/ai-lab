from dataclasses import dataclass

from exp001_mcp_server.catalog.domain.entities.product import Product


@dataclass(frozen=True, slots=True)
class Alternative:
    product: Product
    available: int
