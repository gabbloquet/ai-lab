"""Exporte les réponses de l'oracle (magasin_rules.py) pour un jeu de données.

Les implémentations des expériences (Java, Python) rejouent ces attentes pour vérifier qu'elles
appliquent exactement les mêmes règles métier que l'oracle qui calcule le golden set.

Usage : uv run python domains/magasin/magasin_oracle_export.py --version v1
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from magasin_rules import load_catalog

DOMAIN_DIR = Path(__file__).parent


def export(data_dir: Path, out_dir: Path) -> None:
    catalog = load_catalog(data_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    availability = [
        {
            "sku": sku,
            "storeId": store_id,
            "available": catalog.available(sku, store_id),
            "alternatives": [p.sku for p in catalog.alternatives(sku, store_id)],
        }
        for sku in sorted(catalog.products)
        for store_id in sorted(catalog.stores)
    ]
    stores_with_stock = [
        {"sku": sku, "storeIds": [s.store_id for s in catalog.stores_with_stock(sku)]}
        for sku in sorted(catalog.products)
    ]

    _write_jsonl(out_dir / "availability.jsonl", availability)
    _write_jsonl(out_dir / "stores_with_stock.jsonl", stores_with_stock)


def _write_jsonl(path: Path, rows: list[dict]) -> None:
    with path.open("w", encoding="utf-8") as f:
        for row in rows:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--version", required=True, help="version du jeu de données, ex. v1")
    args = parser.parse_args(argv)
    export(DOMAIN_DIR / "data" / args.version, DOMAIN_DIR / "oracle" / args.version)


if __name__ == "__main__":
    main()
