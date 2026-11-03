from typing import get_args

from exp001_mcp_server.catalog.domain.errors import DOMAIN_ERRORS, CatalogError, DomainError


def test_every_domain_error_is_listed_like_a_sealed_hierarchy():
    assert set(CatalogError.__subclasses__()) == set(DOMAIN_ERRORS)
    assert set(get_args(DomainError.__value__)) == set(DOMAIN_ERRORS)
