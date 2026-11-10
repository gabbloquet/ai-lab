"""Levier « reclassement » (*reranking*) : la recherche dense propose un lot de candidats, un
modèle de reclassement note chacun face à la question, et seuls les mieux notés vont au
générateur.

Le modèle lit chaque candidat comme le générateur le lira : son numéro puis son texte. Les notes
sont gardées sur disque : une question n'est reclassée qu'une fois par modèle et par lot, et
toutes les répétitions, tous les générateurs, voient le même classement.
"""

from __future__ import annotations

import hashlib
import json
import time
from collections.abc import Callable, Sequence
from pathlib import Path
from typing import Any, Protocol

import httpx

from ailab_rag.answering import TOP_K
from ailab_rag.corpus import Passage
from ailab_rag.embeddings import Embedder
from ailab_rag.retrieval import Index

# Taille du lot reclassé : au `dev`, le rappel dense vaut 0,95 dans les 50 premiers passages
# (README de la 005, pré-étude).
POOL = 50


class Reranker(Protocol):
    """Un modèle de reclassement : une note par document, plus elle est haute, plus le document
    répond à la question. `name` identifie le modèle dans le cache."""

    name: str

    def score(self, query: str, documents: list[str]) -> list[float]: ...


class CohereReranker:
    """L'API de reclassement de Cohere (`POST /v2/rerank`, vérifiée le 2026-11-08).

    La clé d'essai accepte 10 requêtes par minute et 1 000 par mois (vérifié le 2026-11-08) :
    les appels sont espacés d'au moins `min_interval` secondes, et un refus pour quota (429)
    est relancé après `retry_wait` secondes, `max_attempts` fois au plus.
    """

    URL = "https://api.cohere.com/v2/rerank"

    def __init__(
        self,
        model: str,
        *,
        api_key: str,
        client: httpx.Client | None = None,
        timeout: float = 60.0,
        min_interval: float = 6.0,
        retry_wait: float = 60.0,
        max_attempts: int = 5,
        clock: Callable[[], float] = time.monotonic,
        sleep: Callable[[float], None] = time.sleep,
    ) -> None:
        self.name = f"cohere:{model}"
        self._model = model
        self._api_key = api_key
        self._client = client or httpx.Client(timeout=timeout)
        self._min_interval = min_interval
        self._retry_wait = retry_wait
        self._max_attempts = max_attempts
        self._clock = clock
        self._sleep = sleep
        self._last_call: float | None = None
        # Durée de chaque appel réussi, attente imposée par la limite de la clé exclue.
        self.latencies: list[float] = []

    def score(self, query: str, documents: list[str]) -> list[float]:
        response = self._post({"model": self._model, "query": query, "documents": documents})
        # Les résultats viennent du plus au moins pertinent : `index` les replace dans l'ordre
        # des documents envoyés.
        scores = {r["index"]: float(r["relevance_score"]) for r in response.json()["results"]}
        if sorted(scores) != list(range(len(documents))):
            raise ValueError(
                f"Cohere a noté {len(scores)} documents sur {len(documents)} documents"
            )
        return [scores[i] for i in range(len(documents))]

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
                self.latencies.append(self._clock() - self._last_call)
                return response
            self._sleep(self._retry_wait)
        raise AssertionError("inatteignable")


class _Predictor(Protocol):
    def predict(
        self, pairs: list[tuple[str, str]], *, batch_size: int
    ) -> Sequence[float] | Any: ...


class CrossEncoderReranker:
    """Un modèle ouvert lancé en local (`sentence_transformers.CrossEncoder`), à une révision
    figée de ses poids sur Hugging Face. Dépendance optionnelle : `ailab-rag[rerank-local]`."""

    def __init__(
        self,
        model: str,
        *,
        revision: str,
        batch_size: int = 8,
        model_object: _Predictor | None = None,
    ) -> None:
        self.name = f"hf:{model}@{revision}"
        # 8 paires par lot : à 32 (défaut de sentence-transformers), les annexes longues font
        # déborder la mémoire d'un Mac de 18 Go et le temps par question passe de 4 à 66 s
        # (pré-étude de la 005). La taille du lot ne change pas les notes.
        self._batch_size = batch_size
        if model_object is None:
            from sentence_transformers import CrossEncoder

            model_object = CrossEncoder(model, revision=revision)
        self._model = model_object

    def score(self, query: str, documents: list[str]) -> list[float]:
        pairs = [(query, d) for d in documents]
        return [float(s) for s in self._model.predict(pairs, batch_size=self._batch_size)]


def document(passage: Passage) -> str:
    """Le candidat tel que le lit le générateur dans les extraits du prompt."""
    return f"Article {passage.num}\n{passage.text}"


class RerankingRetriever:
    def __init__(
        self,
        index: Index,
        embedder: Embedder,
        reranker: Reranker,
        *,
        cache_dir: Path,
        pool: int = POOL,
        k: int = TOP_K,
    ) -> None:
        self._index = index
        self._embedder = embedder
        self._reranker = reranker
        self._cache_dir = cache_dir
        self._pool = pool
        self._k = k

    def __call__(self, question: str) -> list[Passage]:
        candidates = self._index.search(self._embedder.embed([question])[0], self._pool)
        scores = self._scores(question, candidates)
        # Tri stable : à note égale, l'ordre dense départage.
        order = sorted(range(len(candidates)), key=lambda i: -scores[i])
        return [candidates[i] for i in order[: self._k]]

    def best_score(self, question: str) -> float:
        """La meilleure note des `pool` candidats, lue dans le même cache que le reclassement."""
        candidates = self._index.search(self._embedder.embed([question])[0], self._pool)
        return max(self._scores(question, candidates))

    def _scores(self, question: str, candidates: list[Passage]) -> list[float]:
        ids = [f"{p.article_id}#{p.part}" for p in candidates]
        key = "\n".join([self._reranker.name, question, *ids])
        path = self._cache_dir / f"{hashlib.sha256(key.encode()).hexdigest()}.json"
        if path.exists():
            cached: list[float] = json.loads(path.read_text(encoding="utf-8"))
            return cached
        documents = [document(p) for p in candidates]
        scores = [float(s) for s in self._reranker.score(question, documents)]
        if len(scores) != len(candidates):
            raise ValueError(f"{len(scores)} notes pour {len(candidates)} candidats")
        self._cache_dir.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(scores), encoding="utf-8")
        return scores
