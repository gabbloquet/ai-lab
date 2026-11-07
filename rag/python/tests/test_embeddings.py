from pathlib import Path
from types import SimpleNamespace

import numpy as np
import pytest

from ailab_rag.embeddings import CachedEmbedder, MistralEmbedder


class FakeEmbeddingsApi:
    """Imite `client.embeddings` du SDK mistralai : un vecteur [longueur, 1] par texte, renvoyé
    dans le désordre pour vérifier que l'adaptateur s'appuie sur `index`."""

    def __init__(self) -> None:
        self.calls: list[list[str]] = []

    def create(self, *, model: str, inputs: list[str]) -> SimpleNamespace:
        self.calls.append(list(inputs))
        data = [
            SimpleNamespace(index=i, embedding=[float(len(text)), 1.0])
            for i, text in enumerate(inputs)
        ]
        return SimpleNamespace(model=model, data=list(reversed(data)))


def fake_client() -> SimpleNamespace:
    return SimpleNamespace(embeddings=FakeEmbeddingsApi())


class CountingEmbedder:
    """Un embedder en mémoire qui compte les textes qu'il reçoit."""

    def __init__(self, model: str = "fake-embed") -> None:
        self.model = model
        self.seen: list[str] = []

    def embed(self, texts: list[str]) -> np.ndarray:
        self.seen.extend(texts)
        return np.array([[float(len(t)), 1.0] for t in texts], dtype=np.float32)


# --- Adaptateur Mistral -------------------------------------------------------------------------


def test_vectors_have_unit_norm() -> None:
    embedder = MistralEmbedder(client=fake_client())

    vectors = embedder.embed(["abc", "abcdefg"])

    assert vectors.shape == (2, 2)
    np.testing.assert_allclose(np.linalg.norm(vectors, axis=1), [1.0, 1.0], rtol=1e-6)


def test_vectors_follow_the_order_of_the_texts_whatever_the_api_order() -> None:
    vectors = MistralEmbedder(client=fake_client()).embed(["abc", "abcdefg"])

    expected = np.array([[3.0, 1.0], [7.0, 1.0]])
    expected /= np.linalg.norm(expected, axis=1, keepdims=True)
    np.testing.assert_allclose(vectors, expected, rtol=1e-6)


def test_texts_are_sent_in_batches_of_the_given_size() -> None:
    client = fake_client()

    MistralEmbedder(client=client, batch_size=2).embed(["a", "b", "c", "d", "e"])

    assert [len(batch) for batch in client.embeddings.calls] == [2, 2, 1]


def test_a_batch_never_exceeds_the_character_budget() -> None:
    client = fake_client()

    MistralEmbedder(client=client, batch_size=10, max_batch_chars=10).embed(["x" * 6] * 3)

    assert [len(batch) for batch in client.embeddings.calls] == [1, 1, 1]


def test_no_text_means_no_call() -> None:
    client = fake_client()

    vectors = MistralEmbedder(client=client).embed([])

    assert vectors.shape[0] == 0
    assert client.embeddings.calls == []


# --- Cache --------------------------------------------------------------------------------------


def test_a_cached_text_is_not_sent_again(tmp_path: Path) -> None:
    inner = CountingEmbedder()
    cached = CachedEmbedder(inner, tmp_path)

    first = cached.embed(["alpha", "beta"])
    second = cached.embed(["beta", "alpha"])

    assert inner.seen == ["alpha", "beta"]
    np.testing.assert_array_equal(second, first[[1, 0]])


def test_only_missing_texts_are_sent_and_order_is_kept(tmp_path: Path) -> None:
    inner = CountingEmbedder()
    cached = CachedEmbedder(inner, tmp_path)
    cached.embed(["beta"])

    vectors = cached.embed(["alpha", "beta", "gamma", "alpha"])

    assert inner.seen == ["beta", "alpha", "gamma"]
    np.testing.assert_array_equal(vectors[:, 0], [5.0, 4.0, 5.0, 5.0])


def test_the_cache_keeps_models_apart(tmp_path: Path) -> None:
    CachedEmbedder(CountingEmbedder("model-a"), tmp_path).embed(["alpha"])
    other = CountingEmbedder("model-b")

    CachedEmbedder(other, tmp_path).embed(["alpha"])

    assert other.seen == ["alpha"]


def test_the_cache_survives_a_new_instance(tmp_path: Path) -> None:
    CachedEmbedder(CountingEmbedder(), tmp_path).embed(["alpha"])
    inner = CountingEmbedder()

    CachedEmbedder(inner, tmp_path).embed(["alpha"])

    assert inner.seen == []


def test_the_cached_embedder_reports_the_model_of_its_inner_embedder(tmp_path: Path) -> None:
    assert CachedEmbedder(CountingEmbedder("model-a"), tmp_path).model == "model-a"


@pytest.mark.parametrize("texts", [[], ["alpha"]])
def test_the_cache_returns_one_row_per_text(tmp_path: Path, texts: list[str]) -> None:
    assert CachedEmbedder(CountingEmbedder(), tmp_path).embed(texts).shape[0] == len(texts)
