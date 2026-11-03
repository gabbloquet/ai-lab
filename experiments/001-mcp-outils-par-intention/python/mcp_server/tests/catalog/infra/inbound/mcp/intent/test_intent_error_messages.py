from decimal import Decimal

from exp001_mcp_server.catalog.domain.entities.product import Product
from exp001_mcp_server.catalog.domain.entities.store import Store
from exp001_mcp_server.catalog.domain.errors import (
    DepartmentNotFoundError,
    InvalidIdentifierError,
    InvalidSearchQueryError,
    ProductNotFoundError,
    StoreNotFoundError,
)
from exp001_mcp_server.catalog.domain.vo.sku_code import SkuCode
from exp001_mcp_server.catalog.domain.vo.store_id import StoreId
from exp001_mcp_server.catalog.infra.inbound.mcp.intent.intent_error_messages import (
    IntentErrorMessages,
)
from exp001_mcp_server.catalog.infra.outbound.memory.in_memory_catalog import in_memory_catalog

UNKNOWN_STORE = StoreNotFoundError(StoreId("S99"))


def with_stores(count: int) -> IntentErrorMessages:
    stores = [
        Store(StoreId(f"S{i:02d}"), f"Magasin {i}", f"Ville {i}") for i in range(1, count + 1)
    ]
    return IntentErrorMessages(in_memory_catalog([], stores, []))


def with_departments(*departments: str) -> IntentErrorMessages:
    products = [
        Product(
            sku=SkuCode(f"P-{i:05d}"),
            name=f"Produit {i}",
            brand="Marque",
            department=department,
            type="Type",
            price=Decimal("10.00"),
        )
        for i, department in enumerate(departments, start=1)
    ]
    return IntentErrorMessages(in_memory_catalog(products, [], []))


def test_points_to_the_search_tool_for_an_unknown_product():
    assert with_stores(5).message_for(ProductNotFoundError(SkuCode("P-00000"))) == (
        "Product not found: P-00000. Use search_catalog to find the SKU of a product."
    )


def test_lists_every_known_store_with_its_city_when_there_are_few():
    assert with_stores(5).message_for(UNKNOWN_STORE) == (
        "Store not found: S99. Known stores: S01 (Ville 1), S02 (Ville 2), S03 (Ville 3),"
        " S04 (Ville 4), S05 (Ville 5)."
    )


def test_lists_the_known_stores_in_id_order():
    messages = IntentErrorMessages(
        in_memory_catalog(
            [],
            [
                Store(StoreId("S03"), "Magasin 3", "Lille"),
                Store(StoreId("S01"), "Magasin 1", "Lyon"),
                Store(StoreId("S02"), "Magasin 2", "Nantes"),
            ],
            [],
        )
    )

    assert messages.message_for(UNKNOWN_STORE) == (
        "Store not found: S99. Known stores: S01 (Lyon), S02 (Nantes), S03 (Lille)."
    )


def test_lists_ten_stores_without_mentioning_others_at_the_limit():
    assert with_stores(10).message_for(UNKNOWN_STORE).endswith("S09 (Ville 9), S10 (Ville 10).")


def test_caps_the_list_and_counts_the_others_beyond_ten():
    assert (
        with_stores(12)
        .message_for(UNKNOWN_STORE)
        .endswith("S09 (Ville 9), S10 (Ville 10) and 2 more.")
    )


def test_names_it_a_category_and_lists_each_known_one_once():
    messages = with_departments("Maison", "Audio", "Maison")

    assert messages.message_for(DepartmentNotFoundError("Hifi")) == (
        "Category not found: Hifi. Known categories: Audio, Maison."
    )


def test_caps_the_categories_and_counts_the_others_beyond_five():
    messages = with_departments(*(f"Rayon {i}" for i in range(1, 8)))

    assert messages.message_for(DepartmentNotFoundError("Hifi")) == (
        "Category not found: Hifi. Known categories: Rayon 1, Rayon 2, Rayon 3, Rayon 4, Rayon 5"
        " and 2 more."
    )


def test_guides_the_model_after_a_blank_search_query():
    error = InvalidSearchQueryError("Search query must not be blank")

    assert with_stores(5).message_for(error) == (
        "Search query must not be blank. Provide at least one word of a product name,"
        " brand or type. To narrow the results to a department, use category."
    )


def test_passes_an_invalid_identifier_message_as_is():
    error = InvalidIdentifierError("SKU must not be blank")

    assert with_stores(5).message_for(error) == "SKU must not be blank"
