import re
from dataclasses import dataclass

from exp001_mcp_server.catalog.domain.errors import InvalidIdentifierError

SKU_FORMAT = re.compile(r"P-[0-9]{5}")


@dataclass(frozen=True, slots=True)
class SkuCode:
    value: str

    def __post_init__(self) -> None:
        typed = self.value.strip()
        if not typed:
            raise InvalidIdentifierError("SKU must not be blank")

        normalized = typed.upper()
        if not SKU_FORMAT.fullmatch(normalized):
            raise InvalidIdentifierError(f"Invalid SKU: {typed}. A SKU is P- followed by 5 digits.")

        object.__setattr__(self, "value", normalized)

    def __str__(self) -> str:
        return self.value
