"""Les embeddings du RAG naïf : mistral-embed, avec un cache disque.

Les vecteurs sont normalisés (norme 1) dès leur création : la similarité cosinus devient un
produit scalaire. Le cache garantit que A et B, et chaque répétition, voient les mêmes vecteurs,
et qu'un texte n'est envoyé qu'une fois à l'API.
"""

from __future__ import annotations

import hashlib
import os
from pathlib import Path
from typing import Any, Protocol

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
