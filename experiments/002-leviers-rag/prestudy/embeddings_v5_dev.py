"""Pré-étude de la 002 : un autre modèle d'embedding, sur le `dev` de rag-qa v5 (protocole du
README de la 002, 2026-11-17).

Récupération seule, sans générateur, sur les items `dev` avec réponse. A = mistral-embed (lu dans
le cache, sans appel) ; B1 = gemini-embedding-2 ; B2 = Cohere embed-v5.0-pro ; B2' = documents
de B2, requêtes par embed-v5.0-fast. Dimensions par défaut, formats documentés, aucun réglage.

Seules les questions du `dev` sont encodées. Chaque vecteur est gardé dans le cache disque : un
second lancement ne fait plus d'appel, sauf le contrôle de stabilité, qui contourne le cache.
Depuis la racine du dépôt :

    uv run --env-file .env python experiments/002-leviers-rag/prestudy/embeddings_v5_dev.py
"""

import json
import os
import sys
import time
from datetime import date
from statistics import mean

import numpy as np

from ailab_rag.campaign import read_jsonl
from ailab_rag.corpus import passages
from ailab_rag.embeddings import (
    MODEL,
    CachedEmbedder,
    CohereEmbedder,
    GeminiEmbedder,
    gemini_document,
    gemini_query,
)
from ailab_rag.retrieval import Index, build_index
from exp002_leviers.paths import ARTICLES, AUDIT, CACHE_DIR, EXPERIMENT_DIR, GOLDEN_V5
from exp002_leviers.reproduction import CacheMiss, CacheOnlyEmbedder
from exp006_rag.campaign import excluded_items

KS = (5, 10, 20)
GEMINI_MAX_TOKENS = 8_192
LONGEST = 20  # passages les plus longs dont on compte les tokens côté Gemini
STABILITY = 20  # textes encodés deux fois, hors cache
SOLDE = 3  # règle de décision : au moins 3 items gagnés de plus que perdus à 20 passages
CONTROL = EXPERIMENT_DIR / "runs/2026-11-12-mistral-mistral-small-2603-dev/summary.json"
OUT = EXPERIMENT_DIR / f"runs/{date.today().isoformat()}-prestudy-embeddings-dev"
EMB_CACHE = CACHE_DIR / "embeddings"

excl = excluded_items(AUDIT)
items = [
    i
    for i in read_jsonl(GOLDEN_V5)
    if i["split"] == "dev" and i["answerable"] and i["id"] not in excl
]
questions = [i["question"] for i in items]
corpus = passages(read_jsonl(ARTICLES))
print(f"{len(items)} items dev v5 avec réponse ; {len(corpus)} passages")

# --- Les configurations ------------------------------------------------------------------------

mistral = CachedEmbedder(CacheOnlyEmbedder(MODEL), EMB_CACHE)
gemini_api = GeminiEmbedder()
gemini = CachedEmbedder(gemini_api, EMB_CACHE)
cohere_key = os.environ["COHERE_API_KEY"]
pro_doc_api = CohereEmbedder("embed-v5.0-pro", input_type="search_document", api_key=cohere_key)
pro_query_api = CohereEmbedder("embed-v5.0-pro", input_type="search_query", api_key=cohere_key)
fast_query_api = CohereEmbedder("embed-v5.0-fast", input_type="search_query", api_key=cohere_key)


def check_gemini_lengths() -> dict:
    """Gemini ne signale pas la troncature (appel réel du 2026-11-17) : on compte les tokens des
    passages les plus longs, et on s'arrête si l'un dépasse la fenêtre."""
    longest = sorted(corpus, key=lambda p: len(p.text), reverse=True)[:LONGEST]
    counts = []
    for p in longest:
        r = gemini_api._client.models.count_tokens(
            model=gemini_api.model, contents=gemini_document(p.num, p.text)
        )
        counts.append(r.total_tokens)
    if max(counts) > GEMINI_MAX_TOKENS:
        sys.exit(f"un passage dépasse {GEMINI_MAX_TOKENS} tokens : {max(counts)}")
    return {"passages": LONGEST, "max_tokens": max(counts), "max_chars": len(longest[0].text)}


try:
    gemini_lengths = check_gemini_lengths()
    print(f"Gemini : {gemini_lengths['max_tokens']} tokens au plus sur les {LONGEST} plus longs")
except SystemExit:
    raise
except Exception as e:  # noqa: BLE001 — le comptage n'est qu'un garde-fou, il est rapporté
    gemini_lengths = {"error": f"{type(e).__name__}: {e}"}
    print("comptage des tokens Gemini impossible :", gemini_lengths["error"])


def timed(label: str, fn):
    start = time.perf_counter()
    result = fn()
    print(f"{label} : {time.perf_counter() - start:.1f} s")
    return result


try:
    index_a = build_index(corpus, mistral)
    queries_a = mistral.embed(questions)
except CacheMiss as e:
    sys.exit(f"A doit se lire dans le cache : {e}")

index_b1 = timed(
    "B1, corpus",
    lambda: Index(corpus, gemini.embed([gemini_document(p.num, p.text) for p in corpus])),
)
queries_b1 = timed("B1, questions", lambda: gemini.embed([gemini_query(q) for q in questions]))
index_b2 = timed("B2, corpus", lambda: build_index(corpus, CachedEmbedder(pro_doc_api, EMB_CACHE)))
queries_b2 = timed(
    "B2, questions", lambda: CachedEmbedder(pro_query_api, EMB_CACHE).embed(questions)
)
queries_b2f = timed(
    "B2', questions", lambda: CachedEmbedder(fast_query_api, EMB_CACHE).embed(questions)
)

configs = {
    "A mistral-embed": (index_a, queries_a),
    "B1 gemini-embedding-2": (index_b1, queries_b1),
    "B2 embed-v5.0-pro": (index_b2, queries_b2),
    "B2' pro + fast": (index_b2, queries_b2f),
}

# --- Mesures -----------------------------------------------------------------------------------


def articles_of(ranking):
    return list(dict.fromkeys(p.article_id for p in ranking))


rows: dict[str, list[dict]] = {}
for name, (index, queries) in configs.items():
    rows[name] = []
    for it, q in zip(items, queries, strict=True):
        arts = articles_of(index.search(q, max(KS)))
        want = {a["id"] for a in it["expected"]["articles"]}
        r = {"id": it["id"], "mode": it["mode"]}
        for k in KS:
            got = set(arts[:k]) & want
            r[f"recall@{k}"] = len(got) / len(want)
            r[f"all@{k}"] = got == want
        rows[name].append(r)

control = json.loads(CONTROL.read_text())["configurations"]["top_k_20"]["all_evidence"]
a20 = mean(r["all@20"] for r in rows["A mistral-embed"])
assert abs(a20 - control) < 1e-9, (a20, control)


def stability(embedder, texts: list[str]) -> float:
    """Écart maximal entre deux encodages du même texte, hors cache."""
    return float(np.max(np.abs(embedder.embed(texts) - embedder.embed(texts))))


stab = {
    "B1": stability(gemini_api, [gemini_query(q) for q in questions[:STABILITY]]),
    "B2": stability(pro_query_api, questions[:STABILITY]),
    "B2'": stability(fast_query_api, questions[:STABILITY]),
}

# --- Rapport -----------------------------------------------------------------------------------

base = {r["id"]: r for r in rows["A mistral-embed"]}
summary: dict = {
    "date": date.today().isoformat(),
    "n_items": len(items),
    "control_all_evidence_top_k_20": control,
    "gemini_lengths": gemini_lengths,
    "stability_max_abs_diff": stab,
    "billed_tokens": {
        "B1": gemini_api.input_tokens,
        "B2 documents": pro_doc_api.input_tokens,
        "B2 questions": pro_query_api.input_tokens,
        "B2' questions": fast_query_api.input_tokens,
    },
    "configurations": {},
}
print(f"\ncontrôle : A retrouve all_evidence = {control:.3f} à 20 passages")
header = " | ".join(f"tous@{k}" for k in KS) + " | " + " | ".join(f"r@{k}" for k in KS)
print(f"\n{'configuration':<24} | {header} | gagnés / perdus @20 | solde | décision")
for name, rs in rows.items():
    gained = sum(r["all@20"] and not base[r["id"]]["all@20"] for r in rs)
    lost = sum(base[r["id"]]["all@20"] and not r["all@20"] for r in rs)
    survives = name != "A mistral-embed" and gained - lost >= SOLDE
    decision = "—" if name.startswith("A ") else ("survit" if survives else "retombe")
    conf = {f"all_evidence@{k}": mean(r[f"all@{k}"] for r in rs) for k in KS}
    conf |= {f"evidence_recall@{k}": mean(r[f"recall@{k}"] for r in rs) for k in KS}
    conf |= {"gained@20": gained, "lost@20": lost, "decision": decision}
    conf["incomplete@20_by_mode"] = {
        m: sum(not r["all@20"] for r in rs if r["mode"] == m)
        for m in sorted({r["mode"] for r in rs})
    }
    conf["incomplete@20"] = [r["id"] for r in rs if not r["all@20"]]
    summary["configurations"][name] = conf
    print(
        f"{name:<24} | "
        + " | ".join(f"{conf[f'all_evidence@{k}']:.3f}" for k in KS)
        + " | "
        + " | ".join(f"{conf[f'evidence_recall@{k}']:.3f}" for k in KS)
        + f" | +{gained} / -{lost} | {gained - lost:+d} | {decision}"
    )

print("\nitems incomplets à 20 passages, par mode")
for name, conf in summary["configurations"].items():
    print(f"{name:<24} | {conf['incomplete@20_by_mode']}")
print("\nstabilité (écart maximal, hors cache) :", stab)
print("tokens facturés :", summary["billed_tokens"])

OUT.mkdir(parents=True, exist_ok=True)
(OUT / "summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2))
print(f"\nrésumé : {OUT.relative_to(EXPERIMENT_DIR)}/summary.json")
