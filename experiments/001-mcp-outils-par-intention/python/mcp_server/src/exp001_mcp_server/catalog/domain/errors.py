class CatalogError(Exception):
    """Exception de base pour toutes les erreurs du domaine Catalogue."""


class InvalidIdentifierError(CatalogError):
    """Levée lorsqu'un identifiant (comme un SkuCode) a un format ou une valeur invalide."""
