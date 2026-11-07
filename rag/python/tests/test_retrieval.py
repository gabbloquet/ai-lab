import numpy as np
import pytest

from ailab_rag.corpus import Passage
from ailab_rag.retrieval import Index, build_index


def passage(i: int, text: str = "") -> Passage:
    return Passage(article_id=f"LEGIARTI{i:012d}", num=f"L{i}-1", text=text or f"texte {i}", part=0)


PASSAGES = [passage(1), passage(2), passage(3), passage(4)]
VECTORS = np.array(
    [
        [1.0, 0.0],
        [0.0, 1.0],
        [0.6, 0.8],
        [0.8, 0.6],
    ],
    dtype=np.float32,
)


def test_search_returns_the_closest_passages_first() -> None:
    index = Index(PASSAGES, VECTORS)

    found = index.search(np.array([1.0, 0.0], dtype=np.float32), k=3)

    assert [p.num for p in found] == ["L1-1", "L4-1", "L3-1"]


def test_ties_are_broken_by_corpus_order() -> None:
    twins = [passage(1), passage(2), passage(3)]
    vectors = np.array([[0.0, 1.0], [1.0, 0.0], [1.0, 0.0]], dtype=np.float32)

    found = Index(twins, vectors).search(np.array([1.0, 0.0], dtype=np.float32), k=2)

    assert [p.num for p in found] == ["L2-1", "L3-1"]


def test_a_k_larger_than_the_corpus_returns_every_passage() -> None:
    found = Index(PASSAGES, VECTORS).search(np.array([1.0, 0.0], dtype=np.float32), k=10)

    assert len(found) == 4


def test_passages_and_vectors_must_have_the_same_length() -> None:
    with pytest.raises(ValueError, match="4 passages"):
        Index(PASSAGES, VECTORS[:3])


class RecordingEmbedder:
    model = "fake-embed"

    def __init__(self) -> None:
        self.texts: list[str] = []

    def embed(self, texts: list[str]) -> np.ndarray:
        self.texts = list(texts)
        return np.eye(len(texts), dtype=np.float32)


def test_build_index_embeds_the_indexed_text_header_included() -> None:
    embedder = RecordingEmbedder()
    headed = Passage(
        "LEGIARTI000000000001", "L1-1", "Le délai.", 0, header="Article L1-1\nLivre Ier"
    )

    build_index([headed], embedder)

    assert embedder.texts == ["Article L1-1\nLivre Ier\n\nLe délai."]


def test_build_index_embeds_the_text_of_each_passage_only() -> None:
    embedder = RecordingEmbedder()
    passages = [passage(1, "Le délai est de quatorze jours."), passage(2, "Les coûts de renvoi.")]

    index = build_index(passages, embedder)

    assert embedder.texts == ["Le délai est de quatorze jours.", "Les coûts de renvoi."]
    assert [p.num for p in index.search(np.array([0.0, 1.0], dtype=np.float32), k=1)] == ["L2-1"]
