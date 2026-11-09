"""Pré-étude de la 005 : rappel au top-5 après reclassement de 50 candidats, et temps par question.

Récupération seule, sur les items `dev` avec réponse (README de la 005). Depuis la racine du dépôt :

    uv run --env-file .env python experiments/005-reclassement/prestudy/prestudy.py cohere bge qwen

Les notes sont mises en cache (`.cache/ailab_rag/rerank`, ou `RERANK_CACHE`) : pour mesurer les
temps, il faut un cache vide.
"""

import os
import sys
import time
from pathlib import Path
from statistics import median

from ailab_rag.bench import retrieval_report
from ailab_rag.campaign import read_jsonl
from ailab_rag.corpus import passages
from ailab_rag.embeddings import CachedEmbedder, MistralEmbedder
from ailab_rag.reranking import CohereReranker, CrossEncoderReranker, RerankingRetriever
from ailab_rag.retrieval import build_index

CANDIDATES = {
    "bge": lambda: CrossEncoderReranker(
        "BAAI/bge-reranker-v2-m3", revision="953dc6f6f85a1b2dbfca4c34a2796e7dde08d41e"
    ),
    "qwen": lambda: CrossEncoderReranker(
        "Qwen/Qwen3-Reranker-0.6B", revision="e61197ed45024b0ed8a2d74b80b4d909f1255473"
    ),
    "cohere": lambda: CohereReranker("rerank-v5.0-pro", api_key=os.environ["COHERE_API_KEY"]),
}


class Timed:
    def __init__(self, inner):
        self.inner, self.name, self.durations = inner, inner.name, []

    def score(self, query, documents):
        t = time.perf_counter()
        s = self.inner.score(query, documents)
        self.durations.append(time.perf_counter() - t)
        return s


class TimedCohere(Timed):
    """Exclut l'attente imposée par la limite de la clé d'essai : seul l'appel HTTP compte."""

    def score(self, query, documents):
        inner = self.inner
        post = inner._client.post
        spent = []

        def timed_post(*a, **k):
            t = time.perf_counter()
            r = post(*a, **k)
            spent.append(time.perf_counter() - t)
            return r

        inner._client.post = timed_post
        try:
            s = inner.score(query, documents)
        finally:
            inner._client.post = post
        self.durations.append(spent[-1])
        return s


ROOT = Path(__file__).resolve().parents[3]
C = ROOT / ".cache/ailab_rag"
emb = CachedEmbedder(MistralEmbedder(), C / "embeddings")
idx = build_index(
    passages(read_jsonl(ROOT / "domains/droit-consommation/data/v1/articles.jsonl")), emb
)
items = [
    i
    for i in read_jsonl(ROOT / "domains/droit-consommation/golden/rag-qa/v1/items-dev.jsonl")
    if i["split"] == "dev"
]
cache = Path(os.environ.get("RERANK_CACHE", C / "rerank"))
for key in sys.argv[1:]:
    t0 = time.perf_counter()
    inner = CANDIDATES[key]()
    load = time.perf_counter() - t0
    r = (TimedCohere if key == "cohere" else Timed)(inner)
    report = retrieval_report(items, RerankingRetriever(idx, emb, r, cache_dir=cache, k=10))
    d, o = r.durations, report["overall"]
    timing = (
        f"{len(d)} appels, médiane {median(d) if d else 0:.2f} s, max {max(d) if d else 0:.2f} s"
    )
    print(
        f"{key}: rappel@5 {o['evidence_recall@5']:.3f} tous@5 {o['all_evidence@5']:.3f} "
        f"rappel@1 {o['evidence_recall@1']:.3f} | chargement {load:.0f} s, {timing}",
        {m: round(v["evidence_recall@5"], 2) for m, v in report["by_mode"].items()},
        flush=True,
    )
