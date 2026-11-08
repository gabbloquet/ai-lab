"""Levier « reclassement » : la recherche dense propose un lot de candidats, un modèle de
reclassement les note, et seuls les mieux notés vont au générateur."""

import json
from collections.abc import Callable
from pathlib import Path

import httpx
import numpy as np
import pytest

from ailab_rag.corpus import Passage
from ailab_rag.reranking import CohereReranker, CrossEncoderReranker, RerankingRetriever

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


# --- Les deux modèles de la pré-étude ---------------------------------------------------------


def cohere(handler: Callable[[httpx.Request], httpx.Response]) -> CohereReranker:
    client = httpx.Client(transport=httpx.MockTransport(handler))
    return CohereReranker("rerank-v5.0-pro", api_key="test-key", client=client)


def test_cohere_receives_the_query_and_every_document_with_the_api_key() -> None:
    seen: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(request)
        return httpx.Response(200, json={"results": [{"index": 0, "relevance_score": 0.5}]})

    cohere(handler).score("une question", ["doc a"])

    (request,) = seen
    assert request.url == "https://api.cohere.com/v2/rerank"
    assert request.headers["authorization"] == "Bearer test-key"
    assert json.loads(request.content) == {
        "model": "rerank-v5.0-pro",
        "query": "une question",
        "documents": ["doc a"],
    }


def test_cohere_scores_are_put_back_in_the_order_of_the_documents() -> None:
    """L'API renvoie les résultats du plus au moins pertinent ; `index` donne leur place."""

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json={
                "results": [
                    {"index": 2, "relevance_score": 0.9},
                    {"index": 0, "relevance_score": 0.4},
                    {"index": 1, "relevance_score": 0.1},
                ]
            },
        )

    assert cohere(handler).score("q", ["a", "b", "c"]) == [0.4, 0.1, 0.9]


def test_cohere_must_score_every_document() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"results": [{"index": 0, "relevance_score": 0.4}]})

    with pytest.raises(ValueError, match="2 documents"):
        cohere(handler).score("q", ["a", "b"])


def test_a_cohere_http_error_is_raised_without_retry() -> None:
    calls = []

    def handler(request: httpx.Request) -> httpx.Response:
        calls.append(request)
        return httpx.Response(401, json={"message": "clé refusée"})

    with pytest.raises(httpx.HTTPStatusError):
        cohere(handler).score("q", ["a"])
    assert len(calls) == 1


def test_the_cohere_reranker_is_named_after_its_model() -> None:
    assert cohere(lambda r: httpx.Response(200)).name == "cohere:rerank-v5.0-pro"


class FakeCrossEncoder:
    def __init__(self) -> None:
        self.pairs: list[tuple[str, str]] = []

    def predict(self, pairs: list[tuple[str, str]]) -> list[float]:
        self.pairs = pairs
        return [float(len(d)) for _, d in pairs]


def test_the_cross_encoder_scores_each_question_document_pair() -> None:
    model = FakeCrossEncoder()
    reranker = CrossEncoderReranker(
        "BAAI/bge-reranker-v2-m3", revision="abc123", model_object=model
    )

    assert reranker.score("q", ["a", "bbb"]) == [1.0, 3.0]
    assert model.pairs == [("q", "a"), ("q", "bbb")]


def test_the_cross_encoder_is_named_after_its_model_and_its_weights_revision() -> None:
    reranker = CrossEncoderReranker(
        "BAAI/bge-reranker-v2-m3", revision="abc123", model_object=FakeCrossEncoder()
    )

    assert reranker.name == "hf:BAAI/bge-reranker-v2-m3@abc123"


class FakeClock:
    """Horloge et sommeil factices : `sleep` avance l'horloge et garde trace des attentes."""

    def __init__(self) -> None:
        self.now = 0.0
        self.slept: list[float] = []

    def time(self) -> float:
        return self.now

    def sleep(self, seconds: float) -> None:
        self.slept.append(seconds)
        self.now += seconds


def paced_cohere(
    handler: Callable[[httpx.Request], httpx.Response], clock: FakeClock
) -> CohereReranker:
    client = httpx.Client(transport=httpx.MockTransport(handler))
    return CohereReranker(
        "rerank-v5.0-pro",
        api_key="test-key",
        client=client,
        min_interval=6.0,
        retry_wait=60.0,
        max_attempts=3,
        clock=clock.time,
        sleep=clock.sleep,
    )


def ok(request: httpx.Request) -> httpx.Response:
    return httpx.Response(200, json={"results": [{"index": 0, "relevance_score": 0.5}]})


def test_cohere_calls_are_spaced_by_the_minimum_interval() -> None:
    """La clé d'essai de Cohere accepte 10 requêtes par minute pour le reclassement."""
    clock = FakeClock()
    reranker = paced_cohere(ok, clock)

    reranker.score("q", ["a"])
    clock.now += 2.0
    reranker.score("q", ["a"])

    assert clock.slept == [4.0]


def test_a_rate_limited_call_waits_and_is_retried() -> None:
    clock = FakeClock()
    answers = iter([httpx.Response(429), ok(httpx.Request("POST", CohereReranker.URL))])

    reranker = paced_cohere(lambda request: next(answers), clock)

    assert reranker.score("q", ["a"]) == [0.5]
    assert clock.slept == [60.0]


def test_a_call_still_rate_limited_after_the_last_attempt_is_raised() -> None:
    clock = FakeClock()
    reranker = paced_cohere(lambda request: httpx.Response(429), clock)

    with pytest.raises(httpx.HTTPStatusError):
        reranker.score("q", ["a"])
    assert clock.slept == [60.0, 60.0]
