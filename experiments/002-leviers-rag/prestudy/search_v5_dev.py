"""Pré-étude de la 002 après sa clôture (2026-11-17) : tri des pistes de récupération de
`docs/pistes.md`, sur le `dev` de rag-qa v5.

Récupération seule, sans générateur, sur les items `dev` avec réponse. Mesure principale :
`all_evidence` (spec rag-qa v2, § 6), la part des items dont tous les articles attendus sont dans
le contexte. Pistes mesurées :
- la recherche dense à 30 et 50 passages, contre la dense à 20 (`top_k_20`) ;
- le reclassement Cohere de 50 candidats, gardé à 20 passages.

Ne lit que les caches (embeddings, notes Cohere) : un cache manquant arrête le script, sans
appel. Depuis la racine du dépôt :

    uv run python experiments/002-leviers-rag/prestudy/search_v5_dev.py
"""

import json
import sys
from statistics import mean

from ailab_rag.campaign import read_jsonl
from ailab_rag.corpus import passages
from ailab_rag.embeddings import MODEL, CachedEmbedder
from ailab_rag.reranking import RerankingRetriever
from ailab_rag.retrieval import build_index
from exp002_leviers.paths import ARTICLES, AUDIT, CACHE_DIR, EXPERIMENT_DIR, GOLDEN_V5
from exp002_leviers.reproduction import CacheMiss, CacheOnlyEmbedder, CacheOnlyReranker
from exp005_rag.campaign import RERANKER
from exp006_rag.campaign import excluded_items

POOL = 50
# Le run de contrôle `dev` v5 : sa valeur d'`all_evidence` en `top_k_20` doit se retrouver ici.
CONTROL = EXPERIMENT_DIR / "runs/2026-11-12-mistral-mistral-small-2603-dev/summary.json"

excl = excluded_items(AUDIT)
items = [
    i
    for i in read_jsonl(GOLDEN_V5)
    if i["split"] == "dev" and i["answerable"] and i["id"] not in excl
]
emb = CachedEmbedder(CacheOnlyEmbedder(MODEL), CACHE_DIR / "embeddings")
try:
    idx = build_index(passages(read_jsonl(ARTICLES)), emb)
except CacheMiss as e:
    sys.exit(f"index absent du cache : {e}")
rerank = RerankingRetriever(
    idx,
    emb,
    CacheOnlyReranker(f"cohere:{RERANKER}"),
    cache_dir=CACHE_DIR / "rerank",
    pool=POOL,
    k=POOL,
)


def articles_of(ranking):
    return list(dict.fromkeys(p.article_id for p in ranking))


rankings = {"dense": {}, "rerank": {}}
missing = []
for it in items:
    q = it["question"]
    rankings["dense"][it["id"]] = articles_of(idx.search(emb.embed([q])[0], POOL))
    try:
        rankings["rerank"][it["id"]] = articles_of(rerank(q))
    except CacheMiss:
        missing.append(it["id"])
if missing:
    sys.exit(f"notes Cohere absentes du cache pour {len(missing)} items : {missing[:5]}…")

configs = {
    "dense @20 (top_k_20)": ("dense", 20),
    "dense @30": ("dense", 30),
    "dense @50": ("dense", 50),
    "Cohere 50 → 20": ("rerank", 20),
    "Cohere 50 → 5 (rerank_cohere)": ("rerank", 5),
}


def complete(item, arts):
    return {a["id"] for a in item["expected"]["articles"]} <= set(arts)


rows = {
    name: {it["id"]: complete(it, rankings[src][it["id"]][:k]) for it in items}
    for name, (src, k) in configs.items()
}

summary = json.loads(CONTROL.read_text())["configurations"]
control = summary["top_k_20"]["all_evidence"]
base = rows["dense @20 (top_k_20)"]
assert abs(mean(base.values()) - control) < 1e-9, (mean(base.values()), control)
reranked = mean(rows["Cohere 50 → 5 (rerank_cohere)"].values())
assert abs(reranked - summary["rerank_cohere"]["all_evidence"]) < 1e-9, reranked

print(f"{len(items)} items dev v5 avec réponse ; contrôle top_k_20 : all_evidence = {control:.3f}")
print(f"\n{'configuration':<30} | all_evidence | incomplets | gagnés / perdus contre dense @20")
for name, r in rows.items():
    gained = sum(r[i] and not base[i] for i in r)
    lost = sum(base[i] and not r[i] for i in r)
    print(
        f"{name:<30} | {mean(r.values()):.3f}        | {sum(not v for v in r.values()):>10} "
        f"| +{gained} / -{lost}"
    )

modes = sorted({it["mode"] for it in items})
print("\nitems incomplets par mode")
print(
    f"{'configuration':<30} | "
    + " | ".join(f"{m}({sum(it['mode'] == m for it in items)})" for m in modes)
)
for name, r in rows.items():
    print(
        f"{name:<30} | "
        + " | ".join(str(sum(not r[it["id"]] for it in items if it["mode"] == m)) for m in modes)
    )
