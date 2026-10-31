from dataclasses import dataclass
from decimal import Decimal

from exp001_mcp_server.catalog.domain.vo.sku_code import SkuCode


@dataclass(frozen=True, slots=True)
class Product:
    sku: SkuCode
    name: str
    brand: str
    department: str
    type: str
    price: Decimal
