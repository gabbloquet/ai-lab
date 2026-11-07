"""Levier « recherche hybride » : BM25 sur le texte indexé, fusionné avec la recherche dense
par Reciprocal Rank Fusion (RRF).

BM25 retrouve les termes exacts (numéros, mots rares) que l'embedding peut manquer ; la fusion
par rangs évite de comparer des scores d'échelles différentes.
"""

from __future__ import annotations

import math
import re
from collections import Counter

from ailab_evals.rag_qa import normalize
from ailab_rag.corpus import Passage
from ailab_rag.embeddings import Embedder
from ailab_rag.retrieval import Index

RRF_K = 60  # valeur usuelle de la RRF (Cormack et al., 2009)
DEPTH = 50  # nombre de passages pris dans chaque classement avant la fusion

_WORDS = re.compile(r"[^\W_]+")


def _tokens(text: str) -> list[str]:
    return _WORDS.findall(normalize(text))


class Bm25Index:
    """BM25 (Okapi, k1 = 1,5, b = 0,75) sur `indexed_text`, après la normalisation N de la spec
    (casse, accents). Un passage sans aucun terme commun avec la requête n'est pas classé."""

    def __init__(self, passages: list[Passage], k1: float = 1.5, b: float = 0.75) -> None:
        self._passages = passages
        self._docs = [Counter(_tokens(p.indexed_text)) for p in passages]
        self._lengths = [sum(doc.values()) for doc in self._docs]
        self._average = sum(self._lengths) / len(self._lengths)
        frequency: Counter[str] = Counter()
        for doc in self._docs:
            frequency.update(doc.keys())
        n = len(self._docs)
        self._idf = {t: math.log(1 + (n - f + 0.5) / (f + 0.5)) for t, f in frequency.items()}
        self._k1, self._b = k1, b

    def rank(self, query: str, k: int) -> list[Passage]:
        terms = set(_tokens(query))
        scored = []
        for i, doc in enumerate(self._docs):
            norm = self._k1 * (1 - self._b + self._b * self._lengths[i] / self._average)
            score = sum(
                self._idf[t] * doc[t] * (self._k1 + 1) / (doc[t] + norm) for t in terms if t in doc
            )
            if score > 0:
                scored.append((-score, i))
        return [self._passages[i] for _, i in sorted(scored)[:k]]


def reciprocal_rank_fusion(rankings: list[list[Passage]], k: int = RRF_K) -> list[Passage]:
    """Score d'un passage : somme de 1 / (k + rang) sur les classements où il apparaît (rang
    compté à partir de 1). Égalités départagées par l'ordre de première apparition."""
    scores: dict[Passage, float] = {}
    for ranking in rankings:
        for rank, passage in enumerate(ranking, start=1):
            scores[passage] = scores.get(passage, 0.0) + 1.0 / (k + rank)
    order = list(scores)
    return sorted(order, key=lambda p: (-scores[p], order.index(p)))


class HybridRetriever:
    def __init__(
        self, dense: Index, lexical: Bm25Index, embedder: Embedder, depth: int = DEPTH
    ) -> None:
        self._dense = dense
        self._lexical = lexical
        self._embedder = embedder
        self._depth = depth

    def retrieve(self, question: str, k: int) -> list[Passage]:
        dense = self._dense.search(self._embedder.embed([question])[0], self._depth)
        lexical = self._lexical.rank(question, self._depth)
        return reciprocal_rank_fusion([dense, lexical])[:k]
