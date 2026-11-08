"""Levier « reclassement » : la recherche dense propose un lot de candidats, un modèle de
reclassement les note, et seuls les mieux notés vont au générateur."""

from pathlib import Path

import numpy as np

from ailab_rag.corpus import Passage
from ailab_rag.reranking import RerankingRetriever

# 25 passages, du plus proche au moins proche de la question en recherche dense.
PASSAGES = [Passage(f"LEGIARTI{i:012d}", f"L{i}", f"texte {i}", 0) for i in range(25)]
INDEX_VECTORS = np.array([[25.0 - i, 1.0] for i in range(25)], dtype=np.float32)


class FixedEmbedder:
    model = "fake"

    def embed(self, texts: list[str]) -> np.ndarray:
        return np.array([[1.0, 0.0] for _ in texts], dtype=np.float32)


class ScriptedReranker:
    """Note chaque document avec la table `scores` (0 par défaut) et garde trace des appels."""

    def __init__(self, scores: dict[str, float] | None = None, name: str = "fake-reranker") -> None:
        self.name = name
        self._scores = scores or {}
        self.calls: list[tuple[str, list[str]]] = []

    def score(self, query: str, documents: list[str]) -> list[float]:
        self.calls.append((query, documents))
        return [self._scores.get(d, 0.0) for d in documents]


def retriever(reranker: ScriptedReranker, cache_dir: Path, **kwargs: int) -> RerankingRetriever:
    from ailab_rag.retrieval import Index

    return RerankingRetriever(
        Index(PASSAGES, INDEX_VECTORS), FixedEmbedder(), reranker, cache_dir=cache_dir, **kwargs
    )


def test_the_best_scored_candidates_are_kept_in_score_order(tmp_path: Path) -> None:
    reranker = ScriptedReranker({"Article L7\ntexte 7": 0.9, "Article L3\ntexte 3": 0.5})

    found = retriever(reranker, tmp_path, pool=10, k=2)("une question")

    assert found == [PASSAGES[7], PASSAGES[3]]


def test_ties_keep_the_dense_order(tmp_path: Path) -> None:
    found = retriever(ScriptedReranker(), tmp_path, pool=10, k=3)("une question")

    assert found == PASSAGES[:3]


def test_the_reranker_sees_the_pool_as_the_generator_would_read_it(tmp_path: Path) -> None:
    """Numéro et texte, comme dans les extraits du prompt ; le lot compte `pool` candidats."""
    reranker = ScriptedReranker()

    retriever(reranker, tmp_path, pool=4, k=2)("une question")

    assert reranker.calls == [
        ("une question", [f"Article L{i}\ntexte {i}" for i in range(4)]),
    ]


def test_a_reranking_is_computed_once_and_then_read_from_the_cache(tmp_path: Path) -> None:
    """Les répétitions et les trois générateurs voient le même classement."""
    first = ScriptedReranker({"Article L7\ntexte 7": 0.9})
    retriever(first, tmp_path, pool=10, k=2)("une question")

    second = ScriptedReranker()
    found = retriever(second, tmp_path, pool=10, k=2)("une question")

    assert second.calls == []
    assert found == [PASSAGES[7], PASSAGES[0]]


def test_the_cache_depends_on_the_reranker(tmp_path: Path) -> None:
    retriever(ScriptedReranker({"Article L7\ntexte 7": 0.9}, name="a"), tmp_path, pool=10, k=1)(
        "une question"
    )
    other = ScriptedReranker(name="b")

    retriever(other, tmp_path, pool=10, k=1)("une question")

    assert len(other.calls) == 1
