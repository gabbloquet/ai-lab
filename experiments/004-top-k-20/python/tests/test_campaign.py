"""La campagne de la 004 : le même RAG naïf, avec 5 passages (A) ou 20 (B)."""

import numpy as np

from ailab_rag.corpus import Passage
from ailab_rag.retrieval import Index
from exp004_rag.campaign import BASELINE, VARIANT, build_retrievers

# 25 passages, du plus proche au moins proche de la question : le passage i a pour vecteur
# (25 − i, 1), et la question (1, 0).
PASSAGES = [Passage(f"LEGIARTI{i:012d}", f"L{i}", f"texte {i}", 0) for i in range(25)]
INDEX = Index(PASSAGES, np.array([[25.0 - i, 1.0] for i in range(25)], dtype=np.float32))


class FixedEmbedder:
    model = "fake"

    def embed(self, texts: list[str]) -> np.ndarray:
        return np.array([[1.0, 0.0] for _ in texts], dtype=np.float32)


def test_the_two_variants_are_the_naive_rag_and_the_twenty_passage_rag() -> None:
    assert (BASELINE, VARIANT) == ("naive_rag", "top_k_20")


def test_the_baseline_sends_five_passages_and_the_variant_twenty() -> None:
    retrievers = build_retrievers(INDEX, FixedEmbedder())

    assert retrievers[BASELINE]("une question") == PASSAGES[:5]
    assert retrievers[VARIANT]("une question") == PASSAGES[:20]


def test_the_variant_starts_with_exactly_the_passages_of_the_baseline() -> None:
    """Seule la profondeur change : B garde le classement de A et le prolonge."""
    retrievers = build_retrievers(INDEX, FixedEmbedder())

    assert retrievers[VARIANT]("une question")[:5] == retrievers[BASELINE]("une question")
