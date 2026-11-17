"""Les embeddings du RAG : mistral-embed (le RAG naïf), gemini-embedding-2 et Cohere Embed 5
(pré-étude d'un autre modèle d'embedding de la 002), avec un cache disque.

Les vecteurs sont normalisés (norme 1) dès leur création : la similarité cosinus devient un
produit scalaire. Le cache garantit que A et B, et chaque répétition, voient les mêmes vecteurs,
et qu'un texte n'est envoyé qu'une fois à l'API.
"""

from __future__ import annotations

import hashlib
import os
import time
from collections.abc import Callable
from pathlib import Path
from typing import Any, Protocol

import httpx
import numpy as np

MODEL = "mistral-embed"
# Lots prudents : la taille de lot maximale de l'API n'est pas documentée (non vérifié).
BATCH_SIZE = 32
MAX_BATCH_CHARS = 48_000


class Embedder(Protocol):
    model: str

    def embed(self, texts: list[str]) -> np.ndarray: ...


def _unit_rows(vectors: np.ndarray) -> np.ndarray:
    return vectors / np.linalg.norm(vectors, axis=1, keepdims=True)


def _batches(texts: list[str], size: int, max_chars: int) -> list[list[str]]:
    batches: list[list[str]] = []
    current: list[str] = []
    chars = 0
    for text in texts:
        if current and (len(current) == size or chars + len(text) > max_chars):
            batches.append(current)
            current, chars = [], 0
        current.append(text)
        chars += len(text)
    if current:
        batches.append(current)
    return batches


class MistralEmbedder:
    """Adaptateur du SDK mistralai (`client.embeddings.create`, lu dans mistralai 3.7.0)."""

    def __init__(
        self,
        client: Any = None,
        model: str = MODEL,
        batch_size: int = BATCH_SIZE,
        max_batch_chars: int = MAX_BATCH_CHARS,
    ) -> None:
        if client is None:
            from mistralai.client import Mistral

            client = Mistral(api_key=os.environ["MISTRAL_API_KEY"])
        self._client = client
        self.model = model
        self._batch_size = batch_size
        self._max_batch_chars = max_batch_chars

    def embed(self, texts: list[str]) -> np.ndarray:
        rows: list[list[float]] = []
        for batch in _batches(texts, self._batch_size, self._max_batch_chars):
            response = self._client.embeddings.create(model=self.model, inputs=batch)
            rows.extend(item.embedding for item in sorted(response.data, key=lambda d: d.index))
        if not rows:
            return np.empty((0, 0), dtype=np.float32)
        return _unit_rows(np.array(rows, dtype=np.float32))


# --- Autres fournisseurs : pré-étude « un autre modèle d'embedding » de la 002 (2026-11-17) ---
# Les formats viennent de la documentation de chaque fournisseur, vérifiée le 2026-11-17 :
# https://aistudio.google.com/docs/embeddings et https://docs.cohere.com/reference/embed.
# Dimensions par défaut (3 072 et 2 048) : aucun paramètre de dimension n'est envoyé.

GEMINI_MODEL = "gemini-embedding-2"


def gemini_query(question: str) -> str:
    """Le format documenté d'une requête de recherche pour gemini-embedding-2, qui n'a pas de
    `task_type` : la tâche s'écrit dans le texte."""
    return f"task: search result | query: {question}"


def gemini_document(title: str, text: str) -> str:
    """Le format documenté d'un document ; « none » quand il n'a pas de titre."""
    return f"title: {title or 'none'} | text: {text}"


class GeminiEmbedder:
    """Adaptateur du SDK google-genai (`client.models.embed_content`, lu dans google-genai
    2.34.0). Les textes arrivent déjà formatés (`gemini_query`, `gemini_document`) : le format
    entre ainsi dans l'empreinte du cache.

    Chaque texte part dans son propre `Content` : une liste de chaînes donnerait un seul vecteur
    agrégé (documentation de gemini-embedding-2). Un refus pour quota (429) est relancé après
    `retry_wait` secondes, `max_attempts` fois au plus ; les autres erreurs remontent.
    """

    def __init__(
        self,
        client: Any = None,
        model: str = GEMINI_MODEL,
        batch_size: int = BATCH_SIZE,
        max_batch_chars: int = MAX_BATCH_CHARS,
        retry_wait: float = 60.0,
        max_attempts: int = 5,
        sleep: Callable[[float], None] = time.sleep,
    ) -> None:
        if client is None:
            from google import genai

            client = genai.Client(api_key=os.environ["GOOGLE_API_KEY"])
        self._client = client
        self.model = model
        self._batch_size = batch_size
        self._max_batch_chars = max_batch_chars
        self._retry_wait = retry_wait
        self._max_attempts = max_attempts
        self._sleep = sleep
        # Tokens comptés par l'API quand elle les renvoie ; None dès qu'une réponse ne les a pas.
        self.input_tokens: float | None = 0

    def embed(self, texts: list[str]) -> np.ndarray:
        from google.genai import types

        rows: list[list[float]] = []
        for batch in _batches(texts, self._batch_size, self._max_batch_chars):
            contents = [types.Content(parts=[types.Part.from_text(text=t)]) for t in batch]
            response = self._call(contents)
            if len(response.embeddings) != len(batch):
                raise ValueError(f"{len(response.embeddings)} vecteurs pour {len(batch)} textes")
            for embedding in response.embeddings:
                self._count(embedding.statistics)
                rows.append(list(embedding.values))
        if not rows:
            return np.empty((0, 0), dtype=np.float32)
        return _unit_rows(np.array(rows, dtype=np.float32))

    def _call(self, contents: list[Any]) -> Any:
        from google.genai import errors

        for attempt in range(1, self._max_attempts + 1):
            try:
                return self._client.models.embed_content(model=self.model, contents=contents)
            except errors.ClientError as error:
                if error.code != 429 or attempt == self._max_attempts:
                    raise
                self._sleep(self._retry_wait)
        raise AssertionError("inatteignable")

    def _count(self, statistics: Any) -> None:
        if statistics is not None and statistics.truncated:
            raise ValueError("gemini-embedding-2 a tronqué un texte : le protocole l'interdit")
        tokens = None if statistics is None else statistics.token_count
        if tokens is None or self.input_tokens is None:
            self.input_tokens = None
        else:
            self.input_tokens += tokens


COHERE_INPUT_TYPES = ("search_document", "search_query")
COHERE_MAX_TEXTS = 96


class CohereEmbedder:
    """L'API Embed de Cohere (`POST /v2/embed`, vérifiée le 2026-11-17), par `httpx` comme le
    reclassement. `truncate = NONE` : un texte trop long fait échouer l'appel au lieu d'être
    coupé en silence. `model` porte aussi l'`input_type`, pour que le cache sépare requêtes et
    documents.

    La limite de débit de la clé n'est pas vérifiée pour cet endpoint : les appels sont espacés
    d'au moins `min_interval` secondes, et un refus pour quota (429) est relancé après
    `retry_wait` secondes, `max_attempts` fois au plus.
    """

    URL = "https://api.cohere.com/v2/embed"

    def __init__(
        self,
        model: str,
        *,
        input_type: str,
        api_key: str,
        client: httpx.Client | None = None,
        timeout: float = 120.0,
        batch_size: int = COHERE_MAX_TEXTS,
        max_batch_chars: int = MAX_BATCH_CHARS,
        min_interval: float = 6.0,
        retry_wait: float = 60.0,
        max_attempts: int = 5,
        clock: Callable[[], float] = time.monotonic,
        sleep: Callable[[float], None] = time.sleep,
    ) -> None:
        if input_type not in COHERE_INPUT_TYPES:
            raise ValueError(f"input_type doit valoir {' ou '.join(COHERE_INPUT_TYPES)}")
        self.model = f"{model}:{input_type}"
        self._model = model
        self._input_type = input_type
        self._api_key = api_key
        self._client = client or httpx.Client(timeout=timeout)
        self._batch_size = min(batch_size, COHERE_MAX_TEXTS)
        self._max_batch_chars = max_batch_chars
        self._min_interval = min_interval
        self._retry_wait = retry_wait
        self._max_attempts = max_attempts
        self._clock = clock
        self._sleep = sleep
        self._last_call: float | None = None
        self.input_tokens: float = 0

    def embed(self, texts: list[str]) -> np.ndarray:
        rows: list[list[float]] = []
        for batch in _batches(texts, self._batch_size, self._max_batch_chars):
            body = self._post(
                {
                    "model": self._model,
                    "texts": batch,
                    "input_type": self._input_type,
                    "embedding_types": ["float"],
                    "truncate": "NONE",
                }
            ).json()
            vectors = body["embeddings"]["float"]
            if len(vectors) != len(batch):
                raise ValueError(f"{len(vectors)} vecteurs pour {len(batch)} textes")
            self.input_tokens += body.get("meta", {}).get("billed_units", {}).get("input_tokens", 0)
            rows.extend(vectors)
        if not rows:
            return np.empty((0, 0), dtype=np.float32)
        return _unit_rows(np.array(rows, dtype=np.float32))

    def _post(self, body: dict[str, Any]) -> httpx.Response:
        for attempt in range(1, self._max_attempts + 1):
            if self._last_call is not None:
                wait = self._last_call + self._min_interval - self._clock()
                if wait > 0:
                    self._sleep(wait)
            self._last_call = self._clock()
            response = self._client.post(
                self.URL, headers={"Authorization": f"Bearer {self._api_key}"}, json=body
            )
            if response.status_code != 429 or attempt == self._max_attempts:
                response.raise_for_status()
                return response
            self._sleep(self._retry_wait)
        raise AssertionError("inatteignable")


class CachedEmbedder:
    """Garde chaque vecteur sur disque, sous l'empreinte du modèle et du texte."""

    def __init__(self, inner: Embedder, directory: Path) -> None:
        self._inner = inner
        self._directory = directory
        self.model = inner.model

    def _path(self, text: str) -> Path:
        key = hashlib.sha256(f"{self.model}\n{text}".encode()).hexdigest()
        return self._directory / f"{key}.npy"

    def embed(self, texts: list[str]) -> np.ndarray:
        if not texts:
            return np.empty((0, 0), dtype=np.float32)
        missing = list(dict.fromkeys(t for t in texts if not self._path(t).exists()))
        if missing:
            self._directory.mkdir(parents=True, exist_ok=True)
            for text, vector in zip(missing, self._inner.embed(missing), strict=True):
                np.save(self._path(text), vector)
        return np.stack([np.load(self._path(t)) for t in texts])
