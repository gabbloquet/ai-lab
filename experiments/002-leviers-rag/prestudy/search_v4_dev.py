"""Pré-étude de la 002 après le run consolidé (2026-11-09) : d'autres types de recherche que la
recherche dense, sur le `dev` de rag-qa v4.

Récupération seule, sans générateur, sur les items `dev` avec réponse (README de la 002). Ne lit
que les caches (embeddings, notes Cohere) : un cache manquant arrête le script, sans appel. Depuis
la racine du dépôt :

    uv run python experiments/002-leviers-rag/prestudy/search_v4_dev.py
"""

import sys
from statistics import mean

from ailab_evals.rag_qa import score_execution
from ailab_rag.campaign import read_jsonl
from ailab_rag.corpus import passages
from ailab_rag.embeddings import MODEL, CachedEmbedder
from ailab_rag.hybrid import DEPTH, Bm25Index, reciprocal_rank_fusion
from ailab_rag.reranking import RerankingRetriever
from ailab_rag.retrieval import build_index
from exp002_leviers.paths import ARTICLES, AUDIT, CACHE_DIR, GOLDEN
from exp002_leviers.reproduction import CacheMiss, CacheOnlyEmbedder, CacheOnlyReranker
from exp005_rag.campaign import RERANKER
from exp006_rag.campaign import excluded_items

KS = (5, 10, 20)
excl = excluded_items(AUDIT)
items = [
    i for i in read_jsonl(GOLDEN) if i["split"] == "dev" and i["answerable"] and i["id"] not in excl
]
articles = read_jsonl(ARTICLES)
emb = CachedEmbedder(CacheOnlyEmbedder(MODEL), CACHE_DIR / "embeddings")
plain = passages(articles)
try:
    idx = build_index(plain, emb)
except CacheMiss as e:
    sys.exit(f"index sans en-tête : {e}")
try:
    headed = passages(articles, header=True)
    idx_h = build_index(headed, emb)
except CacheMiss as e:
    idx_h = None
    print("index avec en-tête absent du cache :", e)
bm25 = Bm25Index(plain)
bm25_h = Bm25Index(headed)
rerank = RerankingRetriever(
    idx, emb, CacheOnlyReranker(f"cohere:{RERANKER}"), cache_dir=CACHE_DIR / "rerank", pool=50, k=50
)


def dense(index):
    return lambda q: index.search(emb.embed([q])[0], 50)


def hybrid(index, lex):
    return lambda q: reciprocal_rank_fusion(
        [index.search(emb.embed([q])[0], DEPTH), lex.rank(q, DEPTH)]
    )


configs = {"dense": dense(idx), "hybride": hybrid(idx, bm25), "rerank Cohere (50)": rerank}
if idx_h is not None:
    configs["dense + en-tête"] = dense(idx_h)
    configs["hybride + en-tête"] = hybrid(idx_h, bm25_h)


def articles_of(ranking):
    return list(dict.fromkeys(p.article_id for p in ranking))


def check_spec(item, arts):
    e = {
        "item_id": item["id"],
        "variant": "b",
        "model": "none",
        "repeat": 0,
        "answer": "",
        "abstained": False,
        "cited": [],
        "context": arts,
        "usage": {},
        "error": None,
    }
    return score_execution(item, e).as_dict()


res = {}
for name, retrieve in configs.items():
    rows = []
    for it in items:
        arts = articles_of(retrieve(it["question"]))
        want = {a["id"] for a in it["expected"]["articles"]}
        r = {"mode": it["mode"]}
        for k in KS:
            got = set(arts[:k]) & want
            r[f"r@{k}"] = len(got) / len(want)
            r[f"all@{k}"] = float(got == want)
        s = check_spec(it, arts)
        assert (
            abs(s["evidence_recall@5"] - r["r@5"]) < 1e-9
            and abs(s["evidence_recall@10"] - r["r@10"]) < 1e-9
        ), it["id"]
        rows.append(r)
    res[name] = rows

print(f"{len(items)} items dev v4 avec réponse")
hdr = " | ".join(f"r@{k}" for k in KS) + " | " + " | ".join(f"tous@{k}" for k in KS)
print(f"{'config':<20} | {hdr}")
for name, rows in res.items():
    print(
        f"{name:<20} | "
        + " | ".join(f"{mean(r[f'r@{k}'] for r in rows):.3f}" for k in KS)
        + " | "
        + " | ".join(f"{mean(r[f'all@{k}'] for r in rows):.3f}" for k in KS)
    )
modes = sorted({r["mode"] for r in res["dense"]})
for k in (5, 20):
    print(f"\nrappel @{k} par mode")
    print(
        f"{'config':<20} | "
        + " | ".join(f"{m[:10]}({sum(r['mode'] == m for r in res['dense'])})" for m in modes)
    )
    for name, rows in res.items():
        print(
            f"{name:<20} | "
            + " | ".join(f"{mean(r[f'r@{k}'] for r in rows if r['mode'] == m):.2f}" for m in modes)
        )
# gains/pertes par item vs dense @5 et @20
for name, rows in res.items():
    if name == "dense":
        continue
    for k in (5, 20):
        d = [a[f"r@{k}"] - b[f"r@{k}"] for a, b in zip(rows, res["dense"], strict=True)]
        print(f"{name} vs dense @{k}: +{sum(x > 0 for x in d)} / -{sum(x < 0 for x in d)} items")
