"""Génère le golden set tool-selection du domaine magasin (expérience 001).

130 questions, 26 par intention : disponibilité, alternative en stock, magasins qui ont le
produit, fiche produit, recherche. Pour chaque question, les appels attendus de la variante par
intention (`intent`) et de la variante miroir REST (`rest`), calculés par l'oracle
magasin_rules.py. Les règles sont décrites dans golden/tool-selection/README.md.

Usage : uv run python domains/magasin/magasin_golden_tool_selection.py \\
            --seed 42 --version v1 --data-version v1
"""

from __future__ import annotations

import argparse
import hashlib
import json
import random
from pathlib import Path

from jsonschema import Draft202012Validator
from magasin_rules import Catalog, Product, load_catalog

ANY = {"any": True}
SPEC = "evals/spec/tool-selection/v1"
SCHEMA = Path(__file__).resolve().parents[2] / SPEC / "golden.schema.json"

ITEMS_PER_INTENT = 26
DEV_PER_INTENT = 6
OUT_OF_STOCK_AVAILABILITY = 9
WITH_ALTERNATIVE = 18
SEARCH_BY_TYPE = 8
SEARCH_BY_BRAND_AND_TYPE = 14
SEARCH_ABSENT = 4

# Article et pluriel de chaque type, pour écrire les questions en français.
TYPES = {
    "Aspirateur": ("l'aspirateur", "aspirateurs"),
    "Bouilloire": ("la bouilloire", "bouilloires"),
    "Cafetière": ("la cafetière", "cafetières"),
    "Casque": ("le casque", "casques"),
    "Clavier": ("le clavier", "claviers"),
    "Enceinte": ("l'enceinte", "enceintes"),
    "Montre connectée": ("la montre connectée", "montres connectées"),
    "Souris": ("la souris", "souris"),
    "Vélo d'appartement": ("le vélo d'appartement", "vélos d'appartement"),
    "Écouteurs": ("les écouteurs", "écouteurs"),
    "Écran": ("l'écran", "écrans"),
}

# Produits que le catalogue ne vend pas : la recherche doit rester vide.
ABSENT = ["trottinettes électriques", "machines à pain", "imprimantes", "tondeuses", "téléviseurs"]

SKU_PHRASES = ["l'article {sku}", "la référence {sku}", "le produit {sku}"]

# Les questions évitent tout accord avec le produit : « les écouteurs » est pluriel.
TEMPLATES = {
    "availability": [
        "Est-ce qu'on a {p} en stock ici ?",
        "Il nous reste combien d'unités {de_p} dans le magasin ?",
        "{P} : on peut en vendre ici aujourd'hui ?",
        "Un client demande {p}, c'est dispo en magasin ?",
    ],
    "alternative": [
        "Plus de stock ici pour {p} : tu as un équivalent dispo ?",
        "Rupture chez nous sur {p}. Qu'est-ce que je peux proposer à la place, en stock ici ?",
        "Un client voulait {p} mais on n'en a plus. Tu vois un produit proche qu'on a en stock ?",
        "Trouve-moi un produit similaire {a_p}, disponible dans ce magasin.",
    ],
    "stores_with_stock": [
        "Dans quels magasins on trouve {p} en stock ?",
        "{P} : quels magasins en ont en stock ?",
        "Un client cherche {p} : quel magasin du réseau en a ?",
        "Où est-ce qu'il reste du stock {de_p} dans nos magasins ?",
    ],
    "product_details": [
        "Quel est le prix {de_p} ?",
        "Tu peux me donner la fiche {de_p} ?",
        "C'est quelle marque et quel prix, {p} ?",
        "Dans quel rayon on range {p} ?",
    ],
    "search:type": [
        "Qu'est-ce qu'on vend comme {plural} ?",
        "On a quoi en {plural} au catalogue ?",
        "Montre-moi les {plural} qu'on a.",
    ],
    "search:brand_type": [
        "Vous avez des {plural} {brand} ?",
        "Je cherche des {plural} de la marque {brand}, on en vend ?",
        "Il y a des {plural} {brand} au catalogue ?",
    ],
    "search:absent": [
        "Vous vendez des {plural} ?",
        "Un client cherche des {plural}, on en a ?",
    ],
}


def generate(catalog: Catalog, scenarios: list[dict], seed: int) -> list[dict]:
    rng = random.Random(seed)
    scenario = {row["id"]: (row["sku"], row["storeId"]) for row in scenarios}
    cases = (
        _availability(catalog, scenario, rng)
        + _alternative(catalog, scenario, rng)
        + _stores_with_stock(catalog, scenario, rng)
        + _product_details(catalog, rng)
    )
    items = [_product_item(catalog, case, rng) for case in _assign_references(cases, rng)]
    items += _search(catalog, rng)
    _assign_splits(items, rng)
    _write_questions(catalog, items, rng)
    rng.shuffle(items)
    for number, item in enumerate(items, start=1):
        item["id"] = f"ts-{number:03d}"
    items = [_ordered(item) for item in items]
    _check(items)
    return items


def _availability(catalog: Catalog, scenario: dict, rng: random.Random) -> list[dict]:
    pairs = [(sku, store) for sku in sorted(catalog.products) for store in sorted(catalog.stores)]
    chosen = [scenario["fully_reserved"]]
    out_of_stock = [p for p in pairs if not catalog.in_stock(*p)]
    in_stock = [p for p in pairs if catalog.in_stock(*p)]
    rng.shuffle(out_of_stock)
    rng.shuffle(in_stock)
    _take_distinct_products(chosen, out_of_stock, OUT_OF_STOCK_AVAILABILITY)
    _take_distinct_products(chosen, in_stock, ITEMS_PER_INTENT)
    return [{"intent": "availability", "sku": sku, "store": store} for sku, store in chosen]


def _alternative(catalog: Catalog, scenario: dict, rng: random.Random) -> list[dict]:
    pairs = [
        (sku, store)
        for sku in sorted(catalog.products)
        for store in sorted(catalog.stores)
        if not catalog.in_stock(sku, store)
    ]
    with_alternative = [p for p in pairs if catalog.alternatives(*p)]
    without_alternative = [p for p in pairs if not catalog.alternatives(*p)]
    rng.shuffle(with_alternative)
    rng.shuffle(without_alternative)
    chosen = [
        scenario[name]
        for name in (
            "boundary_prices",
            "out_of_stock_with_alternative",
            "out_of_stock_without_alternative",
            "single_product_type",
        )
    ]
    some = [pair for pair in chosen if catalog.alternatives(*pair)]
    none = [pair for pair in chosen if not catalog.alternatives(*pair)]
    _take_distinct_pairs(some, with_alternative, WITH_ALTERNATIVE)
    _take_distinct_pairs(none, without_alternative, ITEMS_PER_INTENT - WITH_ALTERNATIVE)
    return [{"intent": "alternative", "sku": sku, "store": store} for sku, store in some + none]


def _stores_with_stock(catalog: Catalog, scenario: dict, rng: random.Random) -> list[dict]:
    everywhere = scenario["out_of_stock_everywhere"][0]
    others = [sku for sku in sorted(catalog.products) if sku != everywhere]
    skus = [everywhere] + rng.sample(others, ITEMS_PER_INTENT - 1)
    stores = sorted(catalog.stores)
    return [
        {"intent": "stores_with_stock", "sku": sku, "store": rng.choice(stores)} for sku in skus
    ]


def _product_details(catalog: Catalog, rng: random.Random) -> list[dict]:
    skus = rng.sample(sorted(catalog.products), ITEMS_PER_INTENT)
    stores = sorted(catalog.stores)
    return [{"intent": "product_details", "sku": sku, "store": rng.choice(stores)} for sku in skus]


def _take_distinct_products(chosen: list, candidates: list, until: int) -> None:
    used = {sku for sku, _ in chosen}
    for sku, store in candidates:
        if len(chosen) >= until:
            return
        if sku not in used:
            chosen.append((sku, store))
            used.add(sku)


def _take_distinct_pairs(chosen: list, candidates: list, until: int) -> None:
    """Complète `chosen` jusqu'à `until` couples (produit, magasin) distincts : des produits
    encore absents d'abord, puis, faute de mieux, un produit déjà pris dans un autre magasin."""
    _take_distinct_products(chosen, candidates, until)
    for pair in candidates:
        if len(chosen) >= until:
            return
        if pair not in chosen:
            chosen.append(pair)


def _assign_references(cases: list[dict], rng: random.Random) -> list[dict]:
    for intent in ("availability", "alternative", "stores_with_stock", "product_details"):
        group = [case for case in cases if case["intent"] == intent]
        rng.shuffle(group)
        for index, case in enumerate(group):
            case["ref"] = "sku" if index < len(group) // 2 else "name"
    return cases


def _product_item(catalog: Catalog, case: dict, rng: random.Random) -> dict:
    sku, store, intent = case["sku"], case["store"], case["intent"]
    by_name = case["ref"] == "name"
    one = {"sku": [sku]}
    here = {"sku": [sku], "storeId": [store]}
    if intent == "availability":
        intent_required = [{"tool": "check_availability", "args": here}]
        rest_required = [{"tool": "get_stock", "args": here}]
    elif intent == "alternative":
        intent_required = [{"tool": "find_in_stock_alternative", "args": here}]
        alternatives = [p.sku for p in catalog.alternatives(sku, store)]
        rest_required = [{"tool": "get_similar", "args": one}]
        if alternatives:
            rest_required.append(
                {"tool": "get_stock", "args": {"sku": alternatives, "storeId": [store]}}
            )
        else:
            rest_required += [
                {"tool": "get_stock", "args": {"sku": [p.sku], "storeId": [store]}}
                for p in catalog.similar(sku)
            ]
    elif intent == "stores_with_stock":
        intent_required = [{"tool": "find_stores_with_stock", "args": one}]
        rest_required = [
            {"tool": "get_stock", "args": {"sku": [sku], "storeId": [store_id]}}
            for store_id in sorted(catalog.stores)
        ]
    else:
        intent_required = [{"tool": "get_product_details", "args": one}]
        rest_required = [{"tool": "get_product", "args": one}]

    intent_tolerated, rest_tolerated = [], []
    if intent != "product_details":
        intent_tolerated.append({"tool": "get_product_details", "args": one})
        rest_tolerated.append({"tool": "get_product", "args": one})
    if intent == "stores_with_stock":
        rest_tolerated.append({"tool": "list_stores", "args": {}})
    if by_name:
        intent_tolerated.append(
            {"tool": "search_catalog", "args": {"query": ANY}, "optional": {"category": ANY}}
        )
        rest_tolerated.append(
            {"tool": "list_products", "args": {}, "optional": {"query": ANY, "category": ANY}}
        )

    tags = [intent, f"ref:{case['ref']}"]
    if intent == "availability":
        tags.append("stock:in" if catalog.in_stock(sku, store) else "stock:out")
    if intent == "alternative":
        tags.append("alternative:some" if catalog.alternatives(sku, store) else "alternative:none")
    return {
        "context": {"storeId": store},
        "tags": tags,
        "expected": {
            "intent": {"required": intent_required, "tolerated": intent_tolerated},
            "rest": {"required": rest_required, "tolerated": rest_tolerated},
        },
        "_subject": {"sku": sku},
    }


def _search(catalog: Catalog, rng: random.Random) -> list[dict]:
    products = sorted(catalog.products.values(), key=lambda p: p.sku)
    department = {p.type: p.department for p in products}
    brand_types = sorted({(p.brand, p.type) for p in products})
    stores = sorted(catalog.stores)
    subjects = (
        [{"kind": "type", "type": t} for t in rng.sample(sorted(TYPES), SEARCH_BY_TYPE)]
        + [
            {"kind": "brand_type", "brand": b, "type": t}
            for b, t in rng.sample(brand_types, SEARCH_BY_BRAND_AND_TYPE)
        ]
        + [{"kind": "absent", "plural": plural} for plural in rng.sample(ABSENT, SEARCH_ABSENT)]
    )
    items = []
    for subject in subjects:
        category = ANY if subject["kind"] == "absent" else [department[subject["type"]]]
        pattern = {"args": {"query": ANY}, "optional": {"category": category}}
        items.append(
            {
                "context": {"storeId": rng.choice(stores)},
                "tags": ["search", f"search:{subject['kind']}"],
                "expected": {
                    "intent": {
                        "required": [{"tool": "search_catalog", **pattern}],
                        "tolerated": [],
                    },
                    "rest": {"required": [{"tool": "list_products", **pattern}], "tolerated": []},
                },
                "_subject": subject,
            }
        )
    return items


def _assign_splits(items: list[dict], rng: random.Random) -> None:
    """Split stratifié par intention et, hors recherche, par type de référence (SKU ou nom)."""
    groups: dict[tuple[str, str], list[dict]] = {}
    for item in items:
        groups.setdefault((item["tags"][0], _reference(item)), []).append(item)
    for key in sorted(groups):
        group = groups[key]
        dev_count = DEV_PER_INTENT if key[1] == "" else DEV_PER_INTENT // 2
        dev = rng.sample(range(len(group)), dev_count)
        for index, item in enumerate(group):
            item["split"] = "dev" if index in dev else "test"


def _reference(item: dict) -> str:
    return next((tag for tag in item["tags"] if tag.startswith("ref:")), "")


def _write_questions(catalog: Catalog, items: list[dict], rng: random.Random) -> None:
    asked: set[str] = set()
    for item in items:
        templates = TEMPLATES[_template_key(item)][:]
        rng.shuffle(templates)
        values = _phrase(catalog, item, rng)
        for template in templates:
            question = template.format(**values)
            if question not in asked:
                break
        else:
            raise ValueError(f"aucune formulation libre pour {item['_subject']}")
        asked.add(question)
        item["question"] = question


def _template_key(item: dict) -> str:
    # Une recherche se formule selon son sujet (type, marque et type, produit absent).
    return item["tags"][1] if item["tags"][0] == "search" else item["tags"][0]


def _phrase(catalog: Catalog, item: dict, rng: random.Random) -> dict:
    subject = item["_subject"]
    if "search" in item["tags"]:
        plural = subject.get("plural") or TYPES[subject["type"]][1]
        return {"plural": plural, "brand": subject.get("brand", "")}
    product = catalog.products[subject["sku"]]
    if "ref:sku" in item["tags"]:
        phrase = rng.choice(SKU_PHRASES).format(sku=product.sku)
    else:
        phrase = _named(product)
    return {
        "p": phrase,
        "P": phrase[0].upper() + phrase[1:],
        "de_p": _de(phrase),
        "a_p": _a(phrase),
    }


def _named(product: Product) -> str:
    article_and_type = TYPES[product.type][0]
    model = product.name.removeprefix(f"{product.brand} {product.type} ")
    return f"{article_and_type} {product.brand} {model}"


def _de(phrase: str) -> str:
    if phrase.startswith("le "):
        return "du " + phrase[3:]
    if phrase.startswith("les "):
        return "des " + phrase[4:]
    return "de " + phrase


def _a(phrase: str) -> str:
    if phrase.startswith("le "):
        return "au " + phrase[3:]
    if phrase.startswith("les "):
        return "aux " + phrase[4:]
    return "à " + phrase


def _ordered(item: dict) -> dict:
    keys = ["id", "split", "question", "context", "tags", "expected"]
    return {key: item[key] for key in keys}


def _check(items: list[dict]) -> None:
    validator = Draft202012Validator(json.loads(SCHEMA.read_text(encoding="utf-8")))
    for item in items:
        errors = [error.message for error in validator.iter_errors(item)]
        if errors:
            raise ValueError(f"{item['id']} : {errors}")
        for expectation in item["expected"].values():
            required = {pattern["tool"] for pattern in expectation["required"]}
            tolerated = {pattern["tool"] for pattern in expectation["tolerated"]}
            if required & tolerated:
                raise ValueError(f"{item['id']} : outil requis et toléré {required & tolerated}")


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--seed", type=int, required=True)
    parser.add_argument("--version", required=True, help="version du golden set, ex. v1")
    parser.add_argument("--data-version", required=True, help="version des données, ex. v1")
    domain = Path(__file__).parent
    parser.add_argument("--golden-dir", type=Path, default=domain / "golden" / "tool-selection")
    args = parser.parse_args(argv)

    version_dir = args.golden_dir / args.version
    if version_dir.exists() and any(version_dir.iterdir()):
        raise SystemExit(f"{version_dir} existe déjà : une version publiée ne se réécrit pas.")
    data_dir = domain / "data" / args.data_version
    scenarios = json.loads((data_dir / "scenarios.json").read_text(encoding="utf-8"))
    items = generate(load_catalog(data_dir), scenarios, args.seed)

    version_dir.mkdir(parents=True, exist_ok=True)
    items_path = version_dir / "items.jsonl"
    with items_path.open("w", encoding="utf-8") as f:
        for item in items:
            f.write(json.dumps(item, ensure_ascii=False) + "\n")
    manifest = {
        "dataset": "magasin/golden/tool-selection",
        "version": args.version,
        "generator": "domains/magasin/magasin_golden_tool_selection.py",
        "seed": args.seed,
        "data_version": args.data_version,
        "spec": SPEC,
        "files": {"items.jsonl": hashlib.sha256(items_path.read_bytes()).hexdigest()},
    }
    (version_dir / "MANIFEST.json").write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )


if __name__ == "__main__":
    main()
