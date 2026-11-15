"""Les erreurs du domaine : le serveur les rend au modèle comme erreurs d'exécution (`isError`),
pour qu'il se corrige (référentiel MCP du dépôt, § 2)."""


class DomainError(Exception):
    """Une erreur que le modèle peut corriger lui-même."""


class InvalidArticleNumber(DomainError):
    def __init__(self, written: str) -> None:
        super().__init__(written)
        self.written = written


class InvalidQuery(DomainError):
    def __init__(self, reason: str) -> None:
        super().__init__(reason)
        self.reason = reason


class UnknownArticle(DomainError):
    def __init__(self, number: str) -> None:
        super().__init__(number)
        self.number = number


class CallBudgetExhausted(DomainError):
    def __init__(self, max_calls: int) -> None:
        super().__init__(max_calls)
        self.max_calls = max_calls


DOMAIN_ERRORS = (InvalidArticleNumber, InvalidQuery, UnknownArticle, CallBudgetExhausted)
