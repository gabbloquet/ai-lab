from dataclasses import dataclass
from decimal import Decimal

from exp001_mcp_server.catalog.domain.entities.alternative import Alternative
from exp001_mcp_server.catalog.infra.inbound.mcp.intent.dto.product_details import EURO


@dataclass(frozen=True, slots=True)
class AlternativeOffer:
    sku: str
    name: str
    brand: str
    price: Decimal
    currency: str
    available: int


@dataclass(frozen=True, slots=True)
class InStockAlternatives:
    alternatives: list[AlternativeOffer]

    @staticmethod
    def of(alternatives: list[Alternative]) -> "InStockAlternatives":
        return InStockAlternatives(
            [
                AlternativeOffer(
                    sku=alternative.product.sku.value,
                    name=alternative.product.name,
                    brand=alternative.product.brand,
                    price=alternative.product.price,
                    currency=EURO,
                    available=alternative.available,
                )
                for alternative in alternatives
            ]
        )
