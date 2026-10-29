from decimal import Decimal

from magasin_rules import Catalog, Product, StockLine, Store

STORE = "S01"


def product(sku: str, price: str, type_: str = "Casque") -> Product:
    return Product(sku, f"Produit {sku}", "Marque", "Audio", type_, Decimal(price))


def catalog(products: list[Product], stock: dict[str, tuple[int, int]]) -> Catalog:
    """stock : sku -> (onHand, reserved) dans STORE ; 0 en stock pour les produits absents."""
    lines = [StockLine(p.sku, STORE, *stock.get(p.sku, (0, 0))) for p in products]
    return Catalog.of(products, [Store(STORE, "Magasin test", "Ville")], lines)


def skus(products: list[Product]) -> list[str]:
    return [p.sku for p in products]


def test_available_is_on_hand_minus_reserved() -> None:
    cat = catalog([product("A", "100.00")], {"A": (5, 2)})

    assert cat.available("A", STORE) == 3


def test_fully_reserved_product_is_not_in_stock() -> None:
    cat = catalog([product("A", "100.00")], {"A": (3, 3)})

    assert not cat.in_stock("A", STORE)


def test_price_band_bounds_are_inclusive() -> None:
    cat = catalog(
        [product("P", "100.00"), product("LOW", "80.00"), product("HIGH", "120.00")],
        {"LOW": (1, 0), "HIGH": (1, 0)},
    )

    assert skus(cat.alternatives("P", STORE)) == ["HIGH", "LOW"]


def test_prices_just_outside_the_band_are_excluded() -> None:
    cat = catalog(
        [product("P", "100.00"), product("LOW", "79.99"), product("HIGH", "120.01")],
        {"LOW": (1, 0), "HIGH": (1, 0)},
    )

    assert cat.alternatives("P", STORE) == []


def test_alternatives_exclude_the_product_itself() -> None:
    cat = catalog([product("P", "100.00")], {"P": (5, 0)})

    assert cat.alternatives("P", STORE) == []


def test_alternatives_require_same_type() -> None:
    cat = catalog(
        [product("P", "100.00"), product("Q", "100.00", type_="Enceinte")],
        {"Q": (1, 0)},
    )

    assert cat.alternatives("P", STORE) == []


def test_alternatives_require_available_stock_in_the_store() -> None:
    cat = catalog(
        [product("P", "100.00"), product("EMPTY", "100.00"), product("RESERVED", "100.00")],
        {"EMPTY": (0, 0), "RESERVED": (2, 2)},
    )

    assert cat.alternatives("P", STORE) == []


def test_alternatives_sorted_by_price_gap_then_sku_and_capped_at_three() -> None:
    cat = catalog(
        [
            product("P", "100.00"),
            product("D", "110.00"),
            product("C", "90.00"),
            product("B", "95.00"),
            product("A", "119.00"),
        ],
        {sku: (1, 0) for sku in "ABCD"},
    )

    assert skus(cat.alternatives("P", STORE)) == ["B", "C", "D"]


def test_similar_products_ignore_stock_and_are_sorted_by_price_gap_then_sku() -> None:
    cat = catalog(
        [
            product("P", "100.00"),
            product("D", "110.00"),
            product("C", "90.00"),
            product("B", "95.00"),
            product("A", "120.00"),
            product("OUT", "120.01"),
            product("OTHER", "100.00", "Enceinte"),
        ],
        {"B": (1, 0)},
    )

    assert skus(cat.similar("P")) == ["B", "C", "D", "A"]


def test_alternatives_are_the_similar_products_in_stock() -> None:
    cat = catalog(
        [
            product("P", "100.00"),
            product("B", "95.00"),
            product("C", "90.00"),
            product("D", "110.00"),
        ],
        {"C": (2, 0), "D": (1, 0)},
    )

    assert skus(cat.alternatives("P", STORE)) == [
        s for s in skus(cat.similar("P")) if s in {"C", "D"}
    ]


def test_stores_with_stock_sorted_by_store_id() -> None:
    p = product("P", "100.00")
    stores = [Store(s, f"Magasin {s}", "Ville") for s in ("S02", "S01", "S03")]
    lines = [StockLine("P", "S02", 1, 0), StockLine("P", "S01", 4, 0), StockLine("P", "S03", 2, 2)]
    cat = Catalog.of([p], stores, lines)

    assert [s.store_id for s in cat.stores_with_stock("P")] == ["S01", "S02"]
