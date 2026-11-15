"""Une requête de recherche : non vide, 500 caractères au plus (protocole de l'étape 8)."""

from __future__ import annotations

from dataclasses import dataclass

from exp002_mcp_server.corpus.domain.errors import InvalidQuery

MAX_QUERY_CHARS = 500


@dataclass(frozen=True)
class SearchQuery:
    text: str

    @classmethod
    def parse(cls, written: str) -> SearchQuery:
        text = written.strip()
        if not text:
            raise InvalidQuery("empty")
        if len(text) > MAX_QUERY_CHARS:
            raise InvalidQuery("too_long")
        return cls(text)
