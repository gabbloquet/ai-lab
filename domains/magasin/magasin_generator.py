"""Génère le jeu de données synthétique du domaine magasin.

Deux couches :
1. un fond aléatoire seedé (produits, prix, stocks) ;
2. des scénarios injectés explicitement, pour garantir les cas limites dont le golden set
   a besoin. Ils sont listés dans scenarios.json.

Usage : uv run python domains/magasin/magasin_generator.py --seed 42 --version v1
"""

from __future__ import annotations

import argparse
import hashlib
import json
import random
from decimal import Decimal
from pathlib import Path

STORES = [
    ("S01", "Magasin Lyon", "Lyon"),
    ("S02", "Magasin Nantes", "Nantes"),
    ("S03", "Magasin Lille", "Lille"),
    ("S04", "Magasin Bordeaux", "Bordeaux"),
    ("S05", "Magasin Strasbourg", "Strasbourg"),
]

# Marques inventées. Non vérifiées auprès des registres de marques déposées.
BRANDS = [
    "Morvelle",
    "Tisanor",
    "Brivaux",
    "Quellan",
    "Ostrane",
    "Veldric",
    "Junaro",
    "Pellisse",
    "Zorvane",
    "Ambrelin",
]

# (rayon, type, nombre de produits, prix minimal, prix maximal en euros)
TYPES = [
    ("Audio", "Casque", 5, 40, 250),
    ("Audio", "Enceinte", 5, 30, 300),
    ("Audio", "Écouteurs", 5, 20, 200),
    ("Informatique", "Clavier", 5, 20, 180),
    ("Informatique", "Souris", 5, 10, 120),
    ("Informatique", "Écran", 5, 120, 600),
    ("Maison", "Bouilloire", 5, 20, 90),
    ("Maison", "Cafetière", 5, 30, 400),
    ("Maison", "Aspirateur", 4, 80, 500),
    ("Sport", "Montre connectée", 5, 60, 450),
    ("Sport", "Vélo d'appartement", 1, 250, 900),
]

CENT = Decimal("0.01")


def generate(seed: int, out_dir: Path) -> None:
    rng = random.Random(seed)
    products = _products(rng)
    stock = _stock(rng, products)
    scenarios = _inject_scenarios(products, stock)

    out_dir.mkdir(parents=True, exist_ok=True)
    _write_jsonl(
        out_dir / "stores.jsonl",
        [{"storeId": store_id, "name": name, "city": city} for store_id, name, city in STORES],
    )
    _write_jsonl(
        out_dir / "products.jsonl",
        [{**p, "price": float(p["price"])} for p in sorted(products, key=lambda p: p["sku"])],
    )
    _write_jsonl(
        out_dir / "stock.jsonl",
        [
            {"sku": sku, "storeId": store_id, "onHand": on_hand, "reserved": reserved}
            for (sku, store_id), (on_hand, reserved) in sorted(stock.items())
        ],
    )
    (out_dir / "scenarios.json").write_text(
        json.dumps(scenarios, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )


def _products(rng: random.Random) -> list[dict]:
    total = sum(count for _, _, count, _, _ in TYPES)
    # SKU opaques et tirés au hasard : leur ordre ne trahit pas le type du produit.
    skus = [f"P-{n:05d}" for n in rng.sample(range(10000, 100000), total)]
    names: set[str] = set()
    products = []
    for department, type_, count, low, high in TYPES:
        for _ in range(count):
            name = _unique_name(rng, type_, names)
            euros = rng.randint(low, high - 1)
            cents = rng.choice([0, 50, 90, 99])
            products.append(
                {
                    "sku": skus.pop(),
                    "name": name,
                    "brand": name.split(" ")[0],
                    "department": department,
                    "type": type_,
                    "price": Decimal(euros) + Decimal(cents) / 100,
                }
            )
    return products


def _unique_name(rng: random.Random, type_: str, taken: set[str]) -> str:
    while True:
        model = f"{rng.choice('ABCDEFGHKLMNPRSTVX')}{rng.randint(1, 9)}"
        name = f"{rng.choice(BRANDS)} {type_} {model}"
        if name not in taken:
            taken.add(name)
            return name


def _stock(rng: random.Random, products: list[dict]) -> dict[tuple[str, str], tuple[int, int]]:
    stock = {}
    for p in sorted(products, key=lambda p: p["sku"]):
        for store_id, _, _ in STORES:
            on_hand = 0 if rng.random() < 0.15 else rng.randint(1, 20)
            reserved = rng.randint(0, on_hand) if on_hand and rng.random() < 0.3 else 0
            stock[(p["sku"], store_id)] = (on_hand, reserved)
    return stock


def _inject_scenarios(products: list[dict], stock: dict) -> list[dict]:
    def of_type(type_: str) -> list[dict]:
        return sorted((p for p in products if p["type"] == type_), key=lambda p: p["sku"])

    def set_stock(product: dict, store_id: str, on_hand: int, reserved: int = 0) -> None:
        stock[(product["sku"], store_id)] = (on_hand, reserved)

    scenarios = []

    def scenario(id_: str, product: dict, store_id: str, description: str) -> None:
        scenarios.append(
            {"id": id_, "sku": product["sku"], "storeId": store_id, "description": description}
        )

    # Bornes de la fourchette de prix : -20 % et +20 % sont inclus, 1 centime en dessous est exclu.
    reference, low, high, just_below, far = of_type("Casque")
    reference["price"] = Decimal("100.00")
    low["price"], high["price"] = Decimal("80.00"), Decimal("120.00")
    just_below["price"], far["price"] = Decimal("79.99"), Decimal("200.00")
    set_stock(reference, "S02", 0)
    for p in (low, high, just_below):
        set_stock(p, "S02", 4)
    scenario(
        "boundary_prices",
        reference,
        "S02",
        "En rupture ; deux alternatives pile aux bornes, une juste sous la borne basse.",
    )

    reference, alternative, *_ = of_type("Clavier")
    alternative["price"] = (reference["price"] * Decimal("1.10")).quantize(CENT)
    set_stock(reference, "S01", 0)
    set_stock(alternative, "S01", 6)
    scenario(
        "out_of_stock_with_alternative",
        reference,
        "S01",
        "En rupture, avec au moins une alternative en stock.",
    )

    reference, *others = of_type("Bouilloire")
    others[0]["price"] = (reference["price"] * Decimal("0.90")).quantize(CENT)
    set_stock(reference, "S03", 0)
    for p in others:
        if abs(p["price"] - reference["price"]) <= reference["price"] * Decimal("0.20"):
            set_stock(p, "S03", 0)
    scenario(
        "out_of_stock_without_alternative",
        reference,
        "S03",
        "En rupture ; les produits de la même fourchette de prix aussi.",
    )

    reference = of_type("Écran")[0]
    for store_id, _, _ in STORES:
        set_stock(reference, store_id, 0)
    scenario("out_of_stock_everywhere", reference, "S01", "En rupture dans tous les magasins.")

    reference = of_type("Souris")[0]
    set_stock(reference, "S04", 3, reserved=3)
    scenario(
        "fully_reserved",
        reference,
        "S04",
        "Stock physique présent mais entièrement réservé : pas disponible.",
    )

    reference = of_type("Vélo d'appartement")[0]
    set_stock(reference, "S05", 0)
    scenario(
        "single_product_type",
        reference,
        "S05",
        "Seul produit de son type : aucune alternative possible.",
    )

    return scenarios


def _write_jsonl(path: Path, rows: list[dict]) -> None:
    with path.open("w", encoding="utf-8") as f:
        for row in rows:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--seed", type=int, required=True)
    parser.add_argument("--version", required=True, help="ex. v1")
    parser.add_argument("--data-dir", type=Path, default=Path(__file__).parent / "data")
    args = parser.parse_args(argv)

    version_dir = args.data_dir / args.version
    if version_dir.exists() and any(version_dir.iterdir()):
        parser.exit(
            1,
            f"{version_dir} existe déjà : une version publiée est immuable, "
            "créer une nouvelle version.\n",
        )

    generate(args.seed, version_dir)
    files = {
        path.name: hashlib.sha256(path.read_bytes()).hexdigest()
        for path in sorted(version_dir.iterdir())
    }
    manifest = {
        "dataset": "magasin/data",
        "version": args.version,
        "generator": "domains/magasin/magasin_generator.py",
        "seed": args.seed,
        "files": files,
    }
    (version_dir / "MANIFEST.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )


if __name__ == "__main__":
    main()
