"""Le registre du run consolidé : les six configurations gelées des étapes, et les six comparaisons
fixées par le protocole (README de l'expérience, « Run consolidé sur le golden set v4 »).

Rien n'est réécrit : chaque fonction de recherche vient du paquet de son étape, à son commit de
gel. Le `naive_rag` de l'étape 1 (`exp002_rag`) construit son propre index dans une fonction
privée ; on prend donc celui des étapes 2 et 3, qui lui servent de baseline avec la même
expression (`index.search(embed(question), 5)`). Le contrôle de reproduction le vérifie sur les
contextes des runs finaux des étapes 1 à 3.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from ailab_rag.answering import CLOSED_BOOK, NAIVE_RAG, Retriever
from ailab_rag.embeddings import Embedder
from ailab_rag.reranking import Reranker
from ailab_rag.retrieval import Index
from ailab_rag.rewriting import QueryRewriter
from exp003_rag.campaign import build_retrievers as step2_retrievers
from exp004_rag.campaign import build_retrievers as step3_retrievers
from exp005_rag.campaign import build_retrievers as step4_retrievers
from exp006_rag.campaign import GROUNDINGS as STEP5_GROUNDINGS
from exp006_rag.campaign import build_retrievers as step5_retrievers

QUERY_REWRITE = "query_rewrite"
TOP_K_20 = "top_k_20"
RERANK_COHERE = "rerank_cohere"
ABSTAIN_STRICT = "abstain_strict"

CONFIGURATIONS = (CLOSED_BOOK, NAIVE_RAG, QUERY_REWRITE, TOP_K_20, RERANK_COHERE, ABSTAIN_STRICT)

# Seule l'étape 5 change la phrase d'ancrage ; les autres gardent celle de `ailab_rag.prompting`.
GROUNDINGS: dict[str, str] = dict(STEP5_GROUNDINGS)


@dataclass(frozen=True)
class Comparison:
    baseline: str
    variant: str
    step: int
    reading: str
    # Plus petit écart de `correct` qui compte (README) ; `None` pour l'étape 5, jugée sur ses
    # deux critères d'abstention.
    smallest_effect: float | None


COMPARISONS = (
    Comparison(CLOSED_BOOK, NAIVE_RAG, 1, "isolée et cumulative", 0.10),
    Comparison(NAIVE_RAG, QUERY_REWRITE, 2, "isolée", 0.05),
    Comparison(NAIVE_RAG, TOP_K_20, 3, "isolée et cumulative", 0.03),
    Comparison(TOP_K_20, RERANK_COHERE, 4, "cumulative", 0.03),
    Comparison(NAIVE_RAG, RERANK_COHERE, 4, "isolée", 0.03),
    Comparison(TOP_K_20, ABSTAIN_STRICT, 5, "cumulative", None),
)


def build_retrievers(
    index: Index,
    embedder: Embedder,
    rewriter: QueryRewriter,
    reranker: Reranker,
    rerank_cache: Path,
) -> dict[str, Retriever]:
    """Une fonction de recherche par configuration RAG ; `closed_book` n'en a pas."""
    step2 = step2_retrievers(index, embedder, rewriter)
    step3 = step3_retrievers(index, embedder)
    step4 = step4_retrievers(index, embedder, reranker, rerank_cache)
    step5 = step5_retrievers(index, embedder)
    return {
        NAIVE_RAG: step2[NAIVE_RAG],
        QUERY_REWRITE: step2[QUERY_REWRITE],
        TOP_K_20: step3[TOP_K_20],
        RERANK_COHERE: step4[RERANK_COHERE],
        ABSTAIN_STRICT: step5[ABSTAIN_STRICT],
    }
