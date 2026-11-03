import json
import logging
from collections.abc import Callable
from dataclasses import fields, is_dataclass
from decimal import Decimal

from mcp.types import CallToolResult, TextContent

from exp001_mcp_server.catalog.domain.errors import DOMAIN_ERRORS, DomainError

INTERNAL_ERROR = "Internal error while running the tool. Try again later."

type ToolErrorMessages = Callable[[DomainError], str]
"""Le message que le modèle lit pour chaque erreur du domaine, propre à chaque variante."""

logger = logging.getLogger(__name__)


class ToolResults:
    def __init__(self, error_messages: ToolErrorMessages) -> None:
        self._error_messages = error_messages

    def run(self, tool: Callable[[], object]) -> CallToolResult:
        try:
            payload = tool()
        except DOMAIN_ERRORS as error:
            return _error(self._error_messages(error))
        except Exception:
            logger.exception("Erreur inattendue pendant l'exécution d'un outil")
            return _error(INTERNAL_ERROR)
        return CallToolResult(content=[TextContent(type="text", text=to_json(payload))])


def to_json(payload: object) -> str:
    return json.dumps(_plain(payload), ensure_ascii=False, separators=(",", ":"))


def _error(message: str) -> CallToolResult:
    return CallToolResult(content=[TextContent(type="text", text=message)], is_error=True)


def _plain(value: object) -> object:
    if is_dataclass(value) and not isinstance(value, type):
        return {
            _camel_case(field.name): _plain(getattr(value, field.name))
            for field in fields(value)
            if getattr(value, field.name) is not None
        }
    if isinstance(value, list | tuple):
        return [_plain(item) for item in value]
    if isinstance(value, Decimal):
        # Prix de data/v1 : deux décimales au plus, le float s'écrit comme le BigDecimal Java.
        return float(value)
    return value


def _camel_case(name: str) -> str:
    first, *others = name.split("_")
    return first + "".join(word.capitalize() for word in others)
