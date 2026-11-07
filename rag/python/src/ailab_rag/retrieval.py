"""La recherche du RAG naïf : similarité cosinus exacte en mémoire.

Les vecteurs étant normalisés (embeddings.py), le cosinus est un produit scalaire. Avec quelque
2 000 passages, une base vectorielle n'apporterait rien.
"""

from __future__ import annotations

import numpy as np

from ailab_rag.corpus import Passage
from ailab_rag.embeddings import Embedder


class Index:
    def __init__(self, passages: list[Passage], vectors: np.ndarray) -> None:
        if len(passages) != len(vectors):
            raise ValueError(f"{len(passages)} passages pour {len(vectors)} vecteurs")
        self._passages = passages
        self._vectors = vectors

    def search(self, query: np.ndarray, k: int) -> list[Passage]:
        """Les k passages les plus proches, du plus proche au moins proche. Le tri est stable :
        deux passages à égalité gardent leur ordre dans le corpus."""
        scores = self._vectors @ query
        order = np.argsort(-scores, kind="stable")[:k]
        return [self._passages[i] for i in order]


def build_index(passages: list[Passage], embedder: Embedder) -> Index:
    return Index(passages, embedder.embed([p.indexed_text for p in passages]))
