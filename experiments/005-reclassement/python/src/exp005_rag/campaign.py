"""La campagne de la 005 : RAG à 20 passages denses (A) contre 50 candidats reclassés par Cohere,
dont les 5 mieux notés vont au générateur (B).

A est exactement le B gelé de la 004 : le RAG naïf de la 002 avec top-k = 20. B cherche avec la
même question dans le même index, reclasse les 50 premiers passages (`ailab_rag.reranking`) et
garde les 5 mieux notés. Les classements de B sont calculés d'avance, avant la campagne, et
gardés en cache.
"""

from __future__ import annotations

from collections.abc import Iterable
from pathlib import Path

from ailab_rag.answering import Retriever
from ailab_rag.corpus import Passage
from ailab_rag.embeddings import Embedder
from ailab_rag.reranking import Reranker, RerankingRetriever
from ailab_rag.retrieval import Index

# Redéclarés plutôt qu'importés d'exp004_rag : une expérience ne dépend pas du code d'une autre.
BASELINE = "top_k_20"
BASELINE_TOP_K = 20
VARIANT = "rerank_cohere"
# Modèle retenu par la pré-étude (README) ; il ne change pas pendant l'itération.
RERANKER = "rerank-v5.0-pro"


def build_retrievers(
    index: Index, embedder: Embedder, reranker: Reranker, cache_dir: Path
) -> dict[str, Retriever]:
    def dense(question: str) -> list[Passage]:
        return index.search(embedder.embed([question])[0], BASELINE_TOP_K)

    return {
        BASELINE: dense,
        VARIANT: RerankingRetriever(index, embedder, reranker, cache_dir=cache_dir),
    }


def rerank_all(retrievers: dict[str, Retriever], questions: Iterable[str]) -> None:
    """Reclasse chaque question une fois, avant la campagne : ensuite, B lit le cache, et le
    modèle de reclassement n'est plus appelé pendant les exécutions."""
    for question in dict.fromkeys(questions):
        retrievers[VARIANT](question)
