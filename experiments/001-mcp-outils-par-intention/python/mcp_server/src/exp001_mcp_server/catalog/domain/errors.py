from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    # Les value objects lèvent ces erreurs : un import à l'exécution serait circulaire.
    from exp001_mcp_server.catalog.domain.vo.sku_code import SkuCode
    from exp001_mcp_server.catalog.domain.vo.store_id import StoreId


class CatalogError(Exception):
    """Exception de base pour toutes les erreurs du domaine Catalogue."""


class InvalidIdentifierError(CatalogError):
    """Levée lorsqu'un identifiant (comme un SkuCode) a un format ou une valeur invalide."""


class InvalidSearchQueryError(CatalogError):
    """Levée lorsqu'une recherche ne contient aucun mot."""


class ProductNotFoundError(CatalogError):
    def __init__(self, sku: SkuCode) -> None:
        super().__init__(f"Unknown product: {sku}")
        self.sku = sku


class StoreNotFoundError(CatalogError):
    def __init__(self, store_id: StoreId) -> None:
        super().__init__(f"Unknown store: {store_id}")
        self.store_id = store_id


class DepartmentNotFoundError(CatalogError):
    def __init__(self, department: str) -> None:
        super().__init__(f"Unknown department: {department}")
        self.department = department


type DomainError = (
    InvalidIdentifierError
    | InvalidSearchQueryError
    | ProductNotFoundError
    | StoreNotFoundError
    | DepartmentNotFoundError
)
"""Toutes les erreurs du domaine : l'équivalent de la hiérarchie scellée de CatalogException."""

DOMAIN_ERRORS = (
    InvalidIdentifierError,
    InvalidSearchQueryError,
    ProductNotFoundError,
    StoreNotFoundError,
    DepartmentNotFoundError,
)
