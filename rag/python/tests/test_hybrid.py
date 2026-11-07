"""Recherche hybride : BM25 sur le texte indexé, fusionné avec la recherche dense par RRF."""

import numpy as np
import pytest

from ailab_rag.corpus import Passage
from ailab_rag.hybrid import Bm25Index, HybridRetriever, reciprocal_rank_fusion
from ailab_rag.retrieval import Index


def passage(i: int, text: str) -> Passage:
    return Passage(f"LEGIARTI{i:012d}", f"L{i}-1", text, 0)


P1 = passage(1, "Le consommateur dispose d'un délai de rétractation de quatorze jours.")
P2 = passage(2, "Le vendeur rembourse le consommateur dans les quatorze jours.")
P3 = passage(3, "Les services financiers à distance obéissent à des règles propres.")
CORPUS = [P1, P2, P3]


def test_bm25_ranks_first_the_passage_sharing_the_rare_terms() -> None:
    index = Bm25Index(CORPUS)

    assert index.rank("consommateur quatorze rétractation", 3)[0] == P1
    assert index.rank("délai de rétractation", 1) == [P1]


def test_bm25_ignores_case_and_accents() -> None:
    assert Bm25Index(CORPUS).rank("RETRACTATION", 1) == [P1]


def test_bm25_reads_the_indexed_text_header_included() -> None:
    headed = Passage("LEGIARTI000000000009", "L9-1", "Texte sans le mot.", 0, header="Article L9-1")

    assert Bm25Index([P1, headed]).rank("L9-1", 1) == [headed]


def test_rrf_sums_one_over_k_plus_rank_and_keeps_passages_seen_once() -> None:
    fused = reciprocal_rank_fusion([[P1, P2], [P2, P3]], k=60)

    # P2 : 1/62 + 1/61 ; P1 : 1/61 ; P3 : 1/62
    assert fused == [P2, P1, P3]


def test_rrf_breaks_ties_by_order_of_first_appearance() -> None:
    assert reciprocal_rank_fusion([[P1], [P3]], k=60) == [P1, P3]


class FixedEmbedder:
    model = "fake"

    def __init__(self, vectors: dict[str, list[float]]) -> None:
        self.vectors = vectors

    def embed(self, texts: list[str]) -> np.ndarray:
        return np.array([self.vectors[t] for t in texts], dtype=np.float32)


def test_hybrid_retriever_fuses_the_dense_and_the_lexical_rankings() -> None:
    question = "services financiers"
    embedder = FixedEmbedder({question: [1.0, 0.0]})
    dense = Index(CORPUS, np.array([[1.0, 0.0], [0.9, 0.1], [0.0, 1.0]], dtype=np.float32))
    retriever = HybridRetriever(dense, Bm25Index(CORPUS), embedder, depth=3)

    found = retriever.retrieve(question, k=2)

    # Dense : P1, P2, P3 ; BM25 : P3 seul (les autres n'ont aucun terme commun).
    # P3 : 1/63 + 1/61 > P1 : 1/61, donc P3 passe devant.
    assert found == [P3, P1]


def test_bm25_leaves_out_passages_without_any_common_term() -> None:
    assert Bm25Index(CORPUS).rank("services financiers", 3) == [P3]


@pytest.mark.parametrize("k", [1, 2, 3])
def test_hybrid_retriever_returns_k_passages(k: int) -> None:
    question = "délai"
    embedder = FixedEmbedder({question: [1.0, 0.0]})
    dense = Index(CORPUS, np.eye(3, 2, dtype=np.float32))

    assert len(HybridRetriever(dense, Bm25Index(CORPUS), embedder).retrieve(question, k)) == k
