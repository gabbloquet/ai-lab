import pytest

from exp001_mcp_server.catalog.domain.errors import InvalidIdentifierError
from exp001_mcp_server.catalog.domain.vo.store_id import StoreId


def test_normalizes_case_and_surrounding_spaces():
    assert StoreId(" s01 ").value == "S01"


def test_ids_differing_only_by_case_are_equal():
    assert StoreId("s01") == StoreId("S01")
    assert hash(StoreId("s01")) == hash(StoreId("S01"))


def test_rejects_a_blank_id():
    with pytest.raises(InvalidIdentifierError, match="^Store id must not be blank$"):
        StoreId("   ")


def test_keeps_an_unknown_format_for_the_catalog_to_reject():
    assert StoreId("lille").value == "LILLE"


def test_shows_as_its_value():
    assert str(StoreId("s01")) == "S01"
