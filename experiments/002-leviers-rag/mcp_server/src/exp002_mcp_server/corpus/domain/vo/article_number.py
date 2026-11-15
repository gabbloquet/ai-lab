"""Le numéro d'un article, tel que le code l'écrit : « L221-18 », « R313-2 », « L242-18-8 »."""

from __future__ import annotations

import re
from dataclasses import dataclass

from ailab_evals.rag_qa_v2 import normalize_citation
from exp002_mcp_server.corpus.domain.errors import InvalidArticleNumber

# Après la normalisation C de la spec rag-qa v2 (§ 6) : lettre, chiffres, segments séparés par
# des tirets, et au plus une lettre finale (« L111-1 A » devient « L111-1A »).
_NUMBER = re.compile(r"^[LRD]\d+(?:-\d+)*[A-Z]?$")


@dataclass(frozen=True)
class ArticleNumber:
    value: str

    @classmethod
    def parse(cls, written: str) -> ArticleNumber:
        """Lit un numéro comme un modèle l'écrit (« Article L. 221-18 », « l221-18 ») avec la
        normalisation C de la spec : un seul format, côté serveur comme côté notation."""
        value = normalize_citation(written)
        if not _NUMBER.match(value):
            raise InvalidArticleNumber(written)
        return cls(value)
