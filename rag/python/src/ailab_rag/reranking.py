"""Levier « reclassement » (*reranking*) : la recherche dense propose un lot de candidats, un
modèle de reclassement note chacun face à la question, et seuls les mieux notés vont au
générateur.

Le modèle lit chaque candidat comme le générateur le lira : son numéro puis son texte. Les notes
sont gardées sur disque : une question n'est reclassée qu'une fois par modèle et par lot, et
toutes les répétitions, tous les générateurs, voient le même classement.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Protocol

from ailab_rag.answering import TOP_K
from ailab_rag.corpus import Passage
from ailab_rag.embeddings import Embedder
from ailab_rag.retrieval import Index

# Taille du lot reclassé : au `dev`, le rappel dense vaut 0,95 dans les 50 premiers passages
# (README de la 005, pré-étude).
POOL = 50


class Reranker(Protocol):
    """Un modèle de reclassement : une note par document, plus elle est haute, plus le document
    répond à la question. `name` identifie le modèle dans le cache."""

    name: str

    def score(self, query: str, documents: list[str]) -> list[float]: ...


def document(passage: Passage) -> str:
    """Le candidat tel que le lit le générateur dans les extraits du prompt."""
    return f"Article {passage.num}\n{passage.text}"


class RerankingRetriever:
    def __init__(
        self,
        index: Index,
        embedder: Embedder,
        reranker: Reranker,
        *,
        cache_dir: Path,
        pool: int = POOL,
        k: int = TOP_K,
    ) -> None:
        self._index = index
        self._embedder = embedder
        self._reranker = reranker
        self._cache_dir = cache_dir
        self._pool = pool
        self._k = k

    def __call__(self, question: str) -> list[Passage]:
        candidates = self._index.search(self._embedder.embed([question])[0], self._pool)
        scores = self._scores(question, candidates)
        # Tri stable : à note égale, l'ordre dense départage.
        order = sorted(range(len(candidates)), key=lambda i: -scores[i])
        return [candidates[i] for i in order[: self._k]]

    def _scores(self, question: str, candidates: list[Passage]) -> list[float]:
        ids = [f"{p.article_id}#{p.part}" for p in candidates]
        key = "\n".join([self._reranker.name, question, *ids])
        path = self._cache_dir / f"{hashlib.sha256(key.encode()).hexdigest()}.json"
        if path.exists():
            cached: list[float] = json.loads(path.read_text(encoding="utf-8"))
            return cached
        documents = [document(p) for p in candidates]
        scores = [float(s) for s in self._reranker.score(question, documents)]
        if len(scores) != len(candidates):
            raise ValueError(f"{len(scores)} notes pour {len(candidates)} candidats")
        self._cache_dir.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(scores), encoding="utf-8")
        return scores
