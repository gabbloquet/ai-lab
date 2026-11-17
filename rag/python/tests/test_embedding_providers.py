"""Les adaptateurs d'embedding de Google (gemini-embedding-2) et de Cohere (Embed 5).

Pré-étude « un autre modèle d'embedding » de la 002 (protocole du 2026-11-17) : les formats de
requête et de document viennent de la documentation de chaque fournisseur, sans réglage.
"""

import json
from collections.abc import Callable
from types import SimpleNamespace
from typing import Any

import httpx
import numpy as np
import pytest
from google.genai import errors

from ailab_rag.embeddings import (
    CohereEmbedder,
    GeminiEmbedder,
    gemini_document,
    gemini_query,
)


class FakeClock:
    """Horloge et sommeil factices : `sleep` avance l'horloge et garde trace des attentes."""

    def __init__(self) -> None:
        self.now = 0.0
        self.waits: list[float] = []

    def time(self) -> float:
        return self.now

    def sleep(self, seconds: float) -> None:
        self.waits.append(seconds)
        self.now += seconds


# --- Google : gemini-embedding-2 ----------------------------------------------------------------


class FakeGeminiModels:
    """Imite `client.models` du SDK google-genai : un vecteur [longueur, 1] par `Content`, avec
    les statistiques que l'API peut renvoyer. `failures` fait échouer les premiers appels."""

    def __init__(self, failures: list[Exception] | None = None, truncated: bool = False) -> None:
        self.calls: list[dict[str, Any]] = []
        self._failures = list(failures or [])
        self._truncated = truncated

    def embed_content(self, *, model: str, contents: list[Any], config: Any = None) -> Any:
        texts = [content.parts[0].text for content in contents]
        self.calls.append({"model": model, "texts": texts, "config": config})
        if self._failures:
            raise self._failures.pop(0)
        return SimpleNamespace(
            embeddings=[
                SimpleNamespace(
                    values=[float(len(t)), 1.0],
                    statistics=SimpleNamespace(truncated=self._truncated, token_count=len(t)),
                )
                for t in texts
            ]
        )


def gemini(models: FakeGeminiModels, clock: FakeClock | None = None, **kwargs: Any) -> Any:
    clock = clock or FakeClock()
    return GeminiEmbedder(client=SimpleNamespace(models=models), sleep=clock.sleep, **kwargs)


def test_gemini_query_and_document_follow_the_documented_formats() -> None:
    assert gemini_query("Quel délai ?") == "task: search result | query: Quel délai ?"
    assert gemini_document("L. 221-18", "Le consommateur dispose") == (
        "title: L. 221-18 | text: Le consommateur dispose"
    )


def test_gemini_document_without_title_uses_none() -> None:
    assert gemini_document("", "texte") == "title: none | text: texte"


def test_gemini_sends_one_content_per_text_and_returns_unit_vectors_in_order() -> None:
    models = FakeGeminiModels()

    vectors = gemini(models).embed(["abc", "abcdefg"])

    assert models.calls[0]["texts"] == ["abc", "abcdefg"]
    expected = np.array([[3.0, 1.0], [7.0, 1.0]])
    expected /= np.linalg.norm(expected, axis=1, keepdims=True)
    np.testing.assert_allclose(vectors, expected, rtol=1e-6)


def test_gemini_keeps_the_default_dimensions() -> None:
    models = FakeGeminiModels()

    gemini(models).embed(["abc"])

    config = models.calls[0]["config"]
    assert config is None or getattr(config, "output_dimensionality", None) is None


def test_gemini_uses_the_model_of_the_protocol() -> None:
    models = FakeGeminiModels()
    embedder = gemini(models)

    embedder.embed(["abc"])

    assert embedder.model == "gemini-embedding-2"
    assert models.calls[0]["model"] == "gemini-embedding-2"


def test_gemini_texts_are_sent_in_batches_of_the_given_size() -> None:
    models = FakeGeminiModels()

    gemini(models, batch_size=2).embed(["a", "b", "c"])

    assert [call["texts"] for call in models.calls] == [["a", "b"], ["c"]]


def test_gemini_no_text_means_no_call() -> None:
    models = FakeGeminiModels()

    assert gemini(models).embed([]).shape == (0, 0)
    assert models.calls == []


def test_gemini_refuses_a_truncated_text() -> None:
    with pytest.raises(ValueError, match="tronqué"):
        gemini(FakeGeminiModels(truncated=True)).embed(["abc"])


def test_gemini_counts_the_tokens_reported_by_the_api() -> None:
    embedder = gemini(FakeGeminiModels())

    embedder.embed(["abc", "abcdefg"])

    assert embedder.input_tokens == 10


def test_gemini_retries_a_rate_limit_after_the_wait() -> None:
    clock = FakeClock()
    models = FakeGeminiModels(failures=[errors.ClientError(429, {"error": {"code": 429}})])

    vectors = gemini(models, clock, retry_wait=30.0).embed(["abc"])

    assert vectors.shape == (1, 2)
    assert len(models.calls) == 2
    assert clock.waits == [30.0]


def test_gemini_gives_up_after_the_last_attempt() -> None:
    limit = errors.ClientError(429, {"error": {"code": 429}})
    models = FakeGeminiModels(failures=[limit, limit])

    with pytest.raises(errors.ClientError):
        gemini(models, max_attempts=2).embed(["abc"])
    assert len(models.calls) == 2


def test_gemini_does_not_retry_another_client_error() -> None:
    models = FakeGeminiModels(failures=[errors.ClientError(400, {"error": {"code": 400}})])

    with pytest.raises(errors.ClientError):
        gemini(models).embed(["abc"])
    assert len(models.calls) == 1


# --- Cohere : Embed 5 ---------------------------------------------------------------------------


def embed_response(texts: list[str], tokens: float = 4.0) -> httpx.Response:
    return httpx.Response(
        200,
        json={
            "id": "x",
            "embeddings": {"float": [[float(len(t)), 1.0] for t in texts]},
            "texts": texts,
            "meta": {"billed_units": {"input_tokens": tokens}},
        },
    )


def cohere(
    handler: Callable[[httpx.Request], httpx.Response],
    input_type: str = "search_document",
    clock: FakeClock | None = None,
    **kwargs: Any,
) -> CohereEmbedder:
    clock = clock or FakeClock()
    return CohereEmbedder(
        "embed-v5.0-pro",
        input_type=input_type,
        api_key="test-key",
        client=httpx.Client(transport=httpx.MockTransport(handler)),
        clock=clock.time,
        sleep=clock.sleep,
        **kwargs,
    )


def echo(requests: list[dict[str, Any]]) -> Callable[[httpx.Request], httpx.Response]:
    def handler(request: httpx.Request) -> httpx.Response:
        body = json.loads(request.content)
        requests.append({"url": str(request.url), "headers": request.headers, "body": body})
        return embed_response(body["texts"])

    return handler


def test_cohere_sends_the_documented_request_without_truncation() -> None:
    requests: list[dict[str, Any]] = []

    cohere(echo(requests), input_type="search_query").embed(["abc"])

    request = requests[0]
    assert request["url"] == "https://api.cohere.com/v2/embed"
    assert request["headers"]["authorization"] == "Bearer test-key"
    assert request["body"] == {
        "model": "embed-v5.0-pro",
        "texts": ["abc"],
        "input_type": "search_query",
        "embedding_types": ["float"],
        "truncate": "NONE",
    }


def test_cohere_returns_unit_vectors_in_the_order_of_the_texts() -> None:
    vectors = cohere(echo([])).embed(["abc", "abcdefg"])

    expected = np.array([[3.0, 1.0], [7.0, 1.0]])
    expected /= np.linalg.norm(expected, axis=1, keepdims=True)
    np.testing.assert_allclose(vectors, expected, rtol=1e-6)


def test_cohere_sends_at_most_96_texts_per_call() -> None:
    requests: list[dict[str, Any]] = []

    cohere(echo(requests)).embed([f"t{i}" for i in range(100)])

    assert [len(r["body"]["texts"]) for r in requests] == [96, 4]


def test_cohere_is_named_after_its_model_and_input_type() -> None:
    assert cohere(echo([]), input_type="search_query").model == "embed-v5.0-pro:search_query"
    assert cohere(echo([])).model == "embed-v5.0-pro:search_document"


def test_cohere_refuses_an_input_type_outside_retrieval() -> None:
    with pytest.raises(ValueError, match="input_type"):
        cohere(echo([]), input_type="clustering")


def test_cohere_counts_the_billed_tokens() -> None:
    embedder = cohere(lambda r: embed_response(json.loads(r.content)["texts"], tokens=4.0))

    embedder.embed([f"t{i}" for i in range(100)])

    assert embedder.input_tokens == 8


def test_cohere_must_return_one_vector_per_text() -> None:
    embedder = cohere(lambda r: embed_response(["seul"]))

    with pytest.raises(ValueError, match="vecteurs"):
        embedder.embed(["a", "b"])


def test_cohere_calls_are_spaced_by_the_minimum_interval() -> None:
    clock = FakeClock()
    embedder = cohere(echo([]), clock=clock, min_interval=6.0, batch_size=1)

    embedder.embed(["a", "b"])

    assert clock.waits == [6.0]


def test_cohere_retries_a_rate_limit_after_the_wait() -> None:
    clock = FakeClock()
    answers = [httpx.Response(429), None]

    def handler(request: httpx.Request) -> httpx.Response:
        answer = answers.pop(0)
        return (
            answer if answer is not None else embed_response(json.loads(request.content)["texts"])
        )

    vectors = cohere(handler, clock=clock, retry_wait=60.0, min_interval=0.0).embed(["abc"])

    assert vectors.shape == (1, 2)
    assert clock.waits == [60.0]


def test_cohere_raises_another_http_error_without_retry() -> None:
    calls: list[int] = []

    def handler(request: httpx.Request) -> httpx.Response:
        calls.append(1)
        return httpx.Response(400, json={"message": "too long"})

    with pytest.raises(httpx.HTTPStatusError):
        cohere(handler).embed(["abc"])
    assert len(calls) == 1


def test_cohere_no_text_means_no_call() -> None:
    requests: list[dict[str, Any]] = []

    assert cohere(echo(requests)).embed([]).shape == (0, 0)
    assert requests == []
