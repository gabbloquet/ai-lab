"""La campagne de la 005 : 20 passages denses (A) contre 50 candidats reclassés, 5 envoyés (B)."""

from pathlib import Path

import numpy as np
import pytest

from ailab_rag.corpus import Passage
from ailab_rag.retrieval import Index
from exp005_rag.campaign import BASELINE, VARIANT, build_retrievers, main, rerank_all

# 60 passages, du plus proche au moins proche de la question en recherche dense : le passage i
# a pour vecteur (60 − i, 1), et la question (1, 0).
PASSAGES = [Passage(f"LEGIARTI{i:012d}", f"L{i}", f"texte {i}", 0) for i in range(60)]
INDEX = Index(PASSAGES, np.array([[60.0 - i, 1.0] for i in range(60)], dtype=np.float32))


class FixedEmbedder:
    model = "fake"

    def embed(self, texts: list[str]) -> np.ndarray:
        return np.array([[1.0, 0.0] for _ in texts], dtype=np.float32)


class ScriptedReranker:
    """Note les passages L<n> par la table `scores` (0 par défaut), et compte ses appels."""

    name = "fake-reranker"

    def __init__(self, scores: dict[int, float] | None = None) -> None:
        self._scores = scores or {}
        self.calls = 0

    def score(self, query: str, documents: list[str]) -> list[float]:
        self.calls += 1
        return [
            self._scores.get(int(d.split("\n")[0].removeprefix("Article L")), 0.0)
            for d in documents
        ]


class FailingReranker:
    name = "fake-reranker"

    def score(self, query: str, documents: list[str]) -> list[float]:
        raise AssertionError("la campagne ne doit plus appeler le modèle de reclassement")


def test_the_two_variants_are_the_twenty_passage_rag_and_the_reranked_rag() -> None:
    """A garde le nom qu'il avait comme variante de la 004."""
    assert (BASELINE, VARIANT) == ("top_k_20", "rerank_cohere")


def test_the_baseline_sends_the_first_twenty_dense_passages(tmp_path: Path) -> None:
    retrievers = build_retrievers(INDEX, FixedEmbedder(), ScriptedReranker(), tmp_path)

    assert retrievers[BASELINE]("une question") == PASSAGES[:20]


def test_the_variant_sends_the_five_best_scored_of_the_first_fifty(tmp_path: Path) -> None:
    """Un passage au-delà du 50e n'est jamais proposé au modèle, même s'il serait le mieux noté."""
    reranker = ScriptedReranker({55: 1.0, 40: 0.9, 30: 0.8, 20: 0.7, 10: 0.6, 2: 0.5})

    found = build_retrievers(INDEX, FixedEmbedder(), reranker, tmp_path)[VARIANT]("une question")

    assert found == [PASSAGES[i] for i in (40, 30, 20, 10, 2)]


def test_rerank_all_reranks_each_question_once_before_the_campaign(tmp_path: Path) -> None:
    reranker = ScriptedReranker({40: 0.9})
    rerank_all(build_retrievers(INDEX, FixedEmbedder(), reranker, tmp_path), ["q1", "q2", "q1"])

    assert reranker.calls == 2

    # Pendant la campagne, tout vient du cache.
    retrievers = build_retrievers(INDEX, FixedEmbedder(), FailingReranker(), tmp_path)
    assert retrievers[VARIANT]("q1")[0] == PASSAGES[40]


def test_the_test_split_needs_the_final_flag() -> None:
    with pytest.raises(SystemExit, match="--final"):
        main(
            ["--split", "test", "--model", "mistral:mistral-small-2603"], git_is_clean=lambda: True
        )


def test_a_final_run_needs_a_clean_git_tree() -> None:
    with pytest.raises(SystemExit, match="gel"):
        main(
            ["--split", "test", "--final", "--model", "mistral:mistral-small-2603"],
            git_is_clean=lambda: False,
        )


def test_a_run_needs_the_cohere_api_key(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("COHERE_API_KEY", raising=False)

    with pytest.raises(SystemExit, match="COHERE_API_KEY"):
        main(["--split", "dev", "--model", "mistral:mistral-small-2603"], git_is_clean=lambda: True)
