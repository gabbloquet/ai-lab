"""Pré-étude de la 002 après l'étape 6 (2026-11-10) : où cassent les erreurs qui restent, sur le
`dev` de rag-qa v4 ?

Relit le run `dev` de contrôle du run consolidé (k = 1, trois modèles) et le classe avec la
catégorie `failure` du scorer (spec § 6) : `retrieval_miss` si un article attendu manque au
contexte, `generation_miss` s'ils y sont tous et que la réponse est fausse. Mesure aussi si les
articles manquants sont atteignables par un renvoi entre articles, et ce qui manque aux réponses
du mode `set`. Aucun appel. Les runs sont locaux (`runs/` est ignoré par git). Depuis la racine du
dépôt :

    uv run python experiments/002-leviers-rag/prestudy/failures_v4_dev.py
"""

import re
import sys
from collections import Counter, defaultdict

from ailab_evals.rag_qa import fact_found, score_execution
from ailab_rag.campaign import read_jsonl
from exp002_leviers.paths import ARTICLES, AUDIT, EXPERIMENT_DIR, GOLDEN
from exp006_rag.campaign import excluded_items

MODELS = (
    "mistral-mistral-small-2603",
    "mistral-ministral-14b-2512",
    "google-gemini-3.5-flash-lite",
)
VARIANTS = ("naive_rag", "top_k_20", "rerank_cohere")
# Un renvoi : « article L. 221-5 », « R.* 112-1 », « D. 312-4 »… vers le `num` d'un article.
REFERENCE = re.compile(r"\b([LRD])\.?\s*\*?\s*(\d+(?:-\d+)+|\d+)")

excl = excluded_items(AUDIT)
items = {i["id"]: i for i in read_jsonl(GOLDEN) if i["split"] == "dev" and i["id"] not in excl}
articles = {a["id"]: a for a in read_jsonl(ARTICLES)}
by_num: dict[str, set[str]] = defaultdict(set)
for a in articles.values():
    by_num[a["num"]].add(a["id"])


def cited(article_id: str) -> set[str]:
    """Les articles du corpus qu'un article cite dans son texte."""
    found = REFERENCE.findall(articles[article_id]["text"])
    return set().union(*(by_num.get(f"{letter}{number}", set()) for letter, number in found))


runs = {}
for model in MODELS:
    path = EXPERIMENT_DIR / "runs" / f"2026-11-09-{model}-dev" / "executions.jsonl"
    if not path.exists():
        sys.exit(f"run dev de contrôle absent : {path}")
    runs[model] = [
        e for e in read_jsonl(path) if e["item_id"] in items and e["variant"] in VARIANTS
    ]

failures: dict[tuple[str, str], Counter] = defaultdict(Counter)
invented: dict[tuple[str, str], Counter] = defaultdict(Counter)
for model, executions in runs.items():
    for e in executions:
        item = items[e["item_id"]]
        score = score_execution(item, e).as_dict()
        if item["answerable"]:
            failures[(e["variant"], item["mode"])][score["failure"]] += 1
        else:
            invented[(e["variant"], model)]["abstention" if score["correct"] else "inventée"] += 1

modes = sorted({mode for _, mode in failures})
print("Exécutions avec réponse, trois modèles cumulés (k = 1)")
for variant in VARIANTS:
    print(f"\n== {variant} ==")
    print(f"{'mode':15} {'n':>4} {'correct':>8} {'gen_miss':>9} {'retr_miss':>10} {'error':>6}")
    total: Counter = Counter()
    for mode in modes:
        c = failures[(variant, mode)]
        total.update(c)
        print(
            f"{mode:15} {sum(c.values()):4} {c['correct']:8} {c['generation_miss']:9}"
            f" {c['retrieval_miss']:10} {c['error']:6}"
        )
    print(
        f"{'TOTAL':15} {sum(total.values()):4} {total['correct']:8} {total['generation_miss']:9}"
        f" {total['retrieval_miss']:10} {total['error']:6}"
    )

# Le contexte de top_k_20 ne dépend pas du générateur : un seul modèle suffit pour les renvois.
print("\n== Renvois, top_k_20 : articles attendus absents du contexte ==")
for e in runs[MODELS[0]]:
    item = items[e["item_id"]]
    if e["variant"] != "top_k_20" or not item["answerable"]:
        continue
    context = set(e["context"])
    outcome = score_execution(item, e).as_dict()["failure"]
    for gold in {a["id"] for a in item["expected"]["articles"]} - context:
        cited_by_context = any(gold in cited(c) for c in context if c in articles)
        cites_context = bool(cited(gold) & context)
        print(
            f"{item['id']} {item['mode']:13} {articles[gold]['num']:9} {outcome:15}"
            f" cité par le contexte : {cited_by_context!s:5}  cite le contexte : {cites_context}"
        )

print("\n== set, top_k_20 : faits trouvés, et ce qui manque ==")
for model, executions in runs.items():
    for e in executions:
        item = items[e["item_id"]]
        if e["variant"] != "top_k_20" or item["mode"] != "set":
            continue
        facts = item["expected"]["facts"]
        missing = [f["accepted"][0] for f in facts if not fact_found(f, e["answer"])]
        flag = " abstention" if e["abstained"] else ""
        print(f"{model:30} {item['id']} {len(facts) - len(missing)}/{len(facts)}{flag}  {missing}")

print("\n== Sans réponse : abstention ou réponse inventée ==")
for (variant, model), c in sorted(invented.items()):
    print(f"{variant:14} {model:30} abstention {c['abstention']:2}  inventée {c['inventée']:2}")
