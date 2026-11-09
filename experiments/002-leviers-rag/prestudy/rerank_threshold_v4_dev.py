"""Pré-étude de la 002 (2026-11-09) : s'abstenir quand le meilleur score de reclassement Cohere est
sous un seuil, sur le `dev` de rag-qa v4.

Aucun appel : les notes Cohere des 50 candidats viennent du cache, et les réponses du run `dev` de
contrôle du run consolidé (k = 1). Pour un seuil donné, une exécution dont la question a un
meilleur score sous le seuil est remplacée par une abstention, puis notée par la spec. Depuis la
racine du dépôt :

    uv run python experiments/002-leviers-rag/prestudy/rerank_threshold_v4_dev.py
"""

import glob
from statistics import mean

from ailab_evals.rag_qa import score_execution
from ailab_rag.campaign import read_jsonl
from ailab_rag.corpus import passages
from ailab_rag.embeddings import MODEL, CachedEmbedder
from ailab_rag.reranking import POOL, RerankingRetriever
from ailab_rag.retrieval import build_index
from exp002_leviers.paths import ARTICLES, AUDIT, CACHE_DIR, EXPERIMENT_DIR, GOLDEN
from exp002_leviers.reproduction import CacheOnlyEmbedder, CacheOnlyReranker
from exp005_rag.campaign import RERANKER
from exp006_rag.campaign import excluded_items

THRESHOLDS = (0.0, 0.05, 0.1, 0.15, 0.2, 0.25, 0.3, 0.4, 0.5)
CONFIGS = ("top_k_20", "rerank_cohere")

excluded = excluded_items(AUDIT)
items = {i["id"]: i for i in read_jsonl(GOLDEN) if i["split"] == "dev" and i["id"] not in excluded}
embedder = CachedEmbedder(CacheOnlyEmbedder(MODEL), CACHE_DIR / "embeddings")
index = build_index(passages(read_jsonl(ARTICLES)), embedder)
reranker = RerankingRetriever(
    index, embedder, CacheOnlyReranker(f"cohere:{RERANKER}"), cache_dir=CACHE_DIR / "rerank"
)


def best_score(question: str) -> float:
    candidates = index.search(embedder.embed([question])[0], POOL)
    # `_scores` lit le cache des notes ; aucune méthode publique ne les rend (pré-étude seule).
    return max(reranker._scores(question, candidates))


best = {item_id: best_score(item["question"]) for item_id, item in items.items()}

answerable = sorted(best[i] for i, it in items.items() if it["answerable"])
unanswerable = sorted(best[i] for i, it in items.items() if not it["answerable"])
n_a, n_u = len(answerable), len(unanswerable)
print(f"{len(items)} items dev valides : {n_a} avec réponse, {n_u} sans réponse")
for name, values in (("avec réponse", answerable), ("sans réponse", unanswerable)):
    q = [values[int(p * (len(values) - 1))] for p in (0.1, 0.25, 0.5, 0.75, 0.9)]
    print(
        f"  meilleur score {name:<13} : déciles 10/25/50/75/90 = " + " ".join(f"{x:.3f}" for x in q)
    )
pairs = sum((a > u) + 0.5 * (a == u) for a in answerable for u in unanswerable)
print(f"  AUC (avec réponse au-dessus) : {pairs / (n_a * n_u):.3f}")


def abstaining(execution: dict) -> dict:
    return {**execution, "answer": "", "abstained": True, "cited": []}


print("\nseuil | questions écartées (avec / sans réponse)")
for t in THRESHOLDS:
    print(
        f"{t:.2f} | {sum(x < t for x in answerable):>2} / {n_a}  ,  "
        f"{sum(x < t for x in unanswerable):>2} / {n_u}"
    )

for path in sorted(glob.glob(str(EXPERIMENT_DIR / "runs" / "*-dev" / "executions.jsonl"))):
    model = path.split("/")[-2].removeprefix("2026-11-09-").removesuffix("-dev")
    executions = [e for e in read_jsonl(__import__("pathlib").Path(path)) if e["item_id"] in items]
    for config in CONFIGS:
        rows = [e for e in executions if e["variant"] == config]
        print(f"\n{model} · {config}")
        print("seuil | correct | hallucination | false_abstention")
        for t in THRESHOLDS:
            scores = [
                score_execution(
                    items[e["item_id"]], abstaining(e) if best[e["item_id"]] < t else e
                ).as_dict()
                for e in rows
            ]
            hall = [s["hallucination"] for s in scores if s["hallucination"] is not None]
            fa = [s["false_abstention"] for s in scores if s["false_abstention"] is not None]
            print(
                f"{t:.2f} | {mean(s['correct'] for s in scores):.3f} | "
                f"{mean(hall):.3f} | {mean(fa):.3f}"
            )
