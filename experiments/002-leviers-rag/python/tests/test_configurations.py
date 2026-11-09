"""Le registre du run consolidé : six configurations reprises telles quelles des étapes."""

import numpy as np

from ailab_rag.corpus import Passage
from ailab_rag.prompting import GROUNDING
from ailab_rag.retrieval import Index
from exp002_leviers.configurations import (
    COMPARISONS,
    CONFIGURATIONS,
    GROUNDINGS,
    build_retrievers,
)
from exp003_rag.campaign import build_retrievers as step2_retrievers
from exp004_rag.campaign import build_retrievers as step3_retrievers
from exp005_rag.campaign import build_retrievers as step4_retrievers
from exp006_rag.campaign import STRICT_GROUNDING
from exp006_rag.campaign import build_retrievers as step5_retrievers

PASSAGES = [Passage(f"LEGIARTI{i:012d}", f"L{i}", f"texte {i}", 0) for i in range(60)]
INDEX = Index(PASSAGES, np.array([[60.0 - i, float(i % 7)] for i in range(60)], dtype=np.float32))


class FakeEmbedder:
    """La question et sa reformulation n'ont pas le même vecteur : la fusion RRF a du travail."""

    model = "fake"

    def embed(self, texts: list[str]) -> np.ndarray:
        return np.array([[0.0, 1.0] if "reformulée" in t else [1.0, 0.0] for t in texts])


class FakeRewriter:
    def rewrite(self, question: str) -> str:
        return f"{question} reformulée"


class ReversedReranker:
    """Note plus haut les derniers candidats denses : le reclassement change l'ordre."""

    name = "fake:reversed"

    def score(self, query: str, documents: list[str]) -> list[float]:
        return [float(i) for i in range(len(documents))]


def _retrievers(tmp_path):
    return build_retrievers(INDEX, FakeEmbedder(), FakeRewriter(), ReversedReranker(), tmp_path)


def test_the_six_configurations_in_the_order_of_the_steps() -> None:
    assert CONFIGURATIONS == (
        "closed_book",
        "naive_rag",
        "query_rewrite",
        "top_k_20",
        "rerank_cohere",
        "abstain_strict",
    )


def test_every_configuration_but_the_closed_book_has_a_retriever(tmp_path) -> None:
    assert set(_retrievers(tmp_path)) == set(CONFIGURATIONS) - {"closed_book"}


def test_each_retriever_is_the_frozen_one_of_its_step(tmp_path) -> None:
    ours = _retrievers(tmp_path)
    frozen = {
        **step2_retrievers(INDEX, FakeEmbedder(), FakeRewriter()),
        **step3_retrievers(INDEX, FakeEmbedder()),
        "rerank_cohere": step4_retrievers(
            INDEX, FakeEmbedder(), ReversedReranker(), tmp_path / "frozen"
        )["rerank_cohere"],
        "abstain_strict": step5_retrievers(INDEX, FakeEmbedder())["abstain_strict"],
    }
    for name, retrieve in ours.items():
        assert retrieve("question") == frozen[name]("question"), name


def test_the_retrievers_send_the_number_of_passages_of_their_step(tmp_path) -> None:
    sizes = {name: len(r("question")) for name, r in _retrievers(tmp_path).items()}
    assert sizes == {
        "naive_rag": 5,
        "query_rewrite": 5,
        "top_k_20": 20,
        "rerank_cohere": 5,
        "abstain_strict": 20,
    }


def test_only_the_abstention_configuration_changes_the_grounding_sentence() -> None:
    assert GROUNDINGS == {"abstain_strict": STRICT_GROUNDING}
    assert STRICT_GROUNDING.startswith(GROUNDING)


def test_the_six_comparisons_fixed_by_the_protocol() -> None:
    assert [(c.baseline, c.variant, c.step, c.reading) for c in COMPARISONS] == [
        ("closed_book", "naive_rag", 1, "isolée et cumulative"),
        ("naive_rag", "query_rewrite", 2, "isolée"),
        ("naive_rag", "top_k_20", 3, "isolée et cumulative"),
        ("top_k_20", "rerank_cohere", 4, "cumulative"),
        ("naive_rag", "rerank_cohere", 4, "isolée"),
        ("top_k_20", "abstain_strict", 5, "cumulative"),
    ]


def test_the_smallest_difference_that_matters_is_the_one_of_each_step() -> None:
    assert {(c.baseline, c.variant): c.smallest_effect for c in COMPARISONS} == {
        ("closed_book", "naive_rag"): 0.10,
        ("naive_rag", "query_rewrite"): 0.05,
        ("naive_rag", "top_k_20"): 0.03,
        ("top_k_20", "rerank_cohere"): 0.03,
        ("naive_rag", "rerank_cohere"): 0.03,
        # Étape 5 : critères à deux mesures, pas d'écart de `correct` (README).
        ("top_k_20", "abstain_strict"): None,
    }
