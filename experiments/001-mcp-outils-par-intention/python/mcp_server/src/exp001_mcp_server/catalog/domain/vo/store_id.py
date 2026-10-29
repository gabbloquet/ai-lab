from dataclasses import dataclass

from exp001_mcp_server.catalog.domain.errors import InvalidIdentifierError


@dataclass(frozen=True, slots=True)
class StoreId:
    value: str

    def __post_init__(self) -> None:
        typed = self.value.strip()
        if not typed:
            raise InvalidIdentifierError("Store id must not be blank")

        object.__setattr__(self, "value", typed.upper())

    def __str__(self) -> str:
        return self.value
