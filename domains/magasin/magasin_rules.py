"""Règles métier du domaine magasin.

Implémentation de référence : elle calcule les réponses attendues du golden set et sert d'oracle
aux implémentations des expériences. Les règles sont décrites dans domains/magasin/README.md.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from decimal import Decimal
from pathlib import Path

PRICE_TOLERANCE = Decimal("0.20")
MAX_ALTERNATIVES = 3


@dataclass(frozen=True)
class Product:
    sku: str
    name: str
    brand: str
    department: str
    type: str
    price: Decimal


@dataclass(frozen=True)
class Store:
    store_id: str
    name: str
    city: str


@dataclass(frozen=True)
class StockLine:
    sku: str
    store_id: str
    on_hand: int
    reserved: int

    @property
    def available(self) -> int:
        return self.on_hand - self.reserved


@dataclass(frozen=True)
class Catalog:
    products: dict[str, Product]
    stores: dict[str, Store]
    stock: dict[tuple[str, str], StockLine]

    @classmethod
    def of(cls, products: list[Product], stores: list[Store], stock: list[StockLine]) -> Catalog:
        return cls(
            products={p.sku: p for p in products},
            stores={s.store_id: s for s in stores},
            stock={(line.sku, line.store_id): line for line in stock},
        )

    def available(self, sku: str, store_id: str) -> int:
        return self.stock[(sku, store_id)].available

    def in_stock(self, sku: str, store_id: str) -> bool:
        return self.available(sku, store_id) > 0

    def similar(self, sku: str) -> list[Product]:
        reference = self.products[sku]
        low = reference.price * (1 - PRICE_TOLERANCE)
        high = reference.price * (1 + PRICE_TOLERANCE)
        candidates = [
            p
            for p in self.products.values()
            if p.type == reference.type and p.sku != reference.sku and low <= p.price <= high
        ]
        candidates.sort(key=lambda p: (abs(p.price - reference.price), p.sku))
        return candidates

    def alternatives(self, sku: str, store_id: str) -> list[Product]:
        in_stock = [p for p in self.similar(sku) if self.in_stock(p.sku, store_id)]
        return in_stock[:MAX_ALTERNATIVES]

    def stores_with_stock(self, sku: str) -> list[Store]:
        return [
            store for store_id, store in sorted(self.stores.items()) if self.in_stock(sku, store_id)
        ]


def load_catalog(directory: Path) -> Catalog:
    def read(name: str) -> list[dict]:
        with (directory / name).open(encoding="utf-8") as f:
            return [json.loads(line, parse_float=Decimal) for line in f]

    products = [
        Product(r["sku"], r["name"], r["brand"], r["department"], r["type"], Decimal(r["price"]))
        for r in read("products.jsonl")
    ]
    stores = [Store(r["storeId"], r["name"], r["city"]) for r in read("stores.jsonl")]
    stock = [
        StockLine(r["sku"], r["storeId"], r["onHand"], r["reserved"]) for r in read("stock.jsonl")
    ]
    return Catalog.of(products, stores, stock)
