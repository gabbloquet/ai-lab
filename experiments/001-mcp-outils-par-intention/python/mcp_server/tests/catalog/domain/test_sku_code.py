import pytest

from exp001_mcp_server.catalog.domain.errors import InvalidIdentifierError
from exp001_mcp_server.catalog.domain.vo import SkuCode


def test_normalizes_case_and_surrounding_spaces():
    assert SkuCode(" p-00001 ").value == "P-00001"


def test_codes_differing_only_by_case_are_equal():
    assert SkuCode("p-00001") == SkuCode("P-00001")
    assert hash(SkuCode("p-00001")) == hash(SkuCode("P-00001"))


def test_rejects_a_blank_code():
    with pytest.raises(InvalidIdentifierError, match="^SKU must not be blank$"):
        SkuCode("   ")


@pytest.mark.parametrize(
    ("typed", "shown"),
    [("80284", "80284"), ("P80284", "P80284"), ("P-1234", "P-1234"), (" p80284 ", "p80284")],
)
def test_rejects_a_malformed_code_with_the_expected_format(typed, shown):
    with pytest.raises(InvalidIdentifierError) as error:
        SkuCode(typed)
    assert str(error.value) == f"Invalid SKU: {shown}. A SKU is P- followed by 5 digits."


def test_accepts_only_ascii_digits_like_the_java_server():
    with pytest.raises(InvalidIdentifierError):
        SkuCode("P-١٢٣٤٥")


def test_shows_as_its_value():
    assert str(SkuCode("p-00001")) == "P-00001"
