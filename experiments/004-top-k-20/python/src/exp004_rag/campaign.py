"""La campagne de la 004 : RAG naïf à 5 passages (A) contre le même RAG à 20 passages (B).

A est exactement le RAG naïf de la 002 (briques `ailab_rag`). B cherche avec la même question,
dans le même index, et garde les 20 premiers passages au lieu des 5 premiers ; rien d'autre ne
change.
"""

from __future__ import annotations

from ailab_rag.answering import NAIVE_RAG, TOP_K, Retriever
from ailab_rag.corpus import Passage
from ailab_rag.embeddings import Embedder
from ailab_rag.retrieval import Index

BASELINE = NAIVE_RAG
VARIANT = "top_k_20"
# Profondeur de B, fixée par la pré-étude (README) ; elle ne change pas pendant l'itération.
VARIANT_TOP_K = 20


def build_retrievers(index: Index, embedder: Embedder) -> dict[str, Retriever]:
    def search(k: int) -> Retriever:
        def retrieve(question: str) -> list[Passage]:
            return index.search(embedder.embed([question])[0], k)

        return retrieve

    return {BASELINE: search(TOP_K), VARIANT: search(VARIANT_TOP_K)}
