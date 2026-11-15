"""Ce que le serveur sert : un article entier, ou un passage trouvé par la recherche."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Article:
    article_id: str
    num: str
    path: tuple[str, ...]
    text: str


@dataclass(frozen=True)
class FoundPassage:
    """Un passage rendu par la recherche ; `article_id` sert à reconstruire le contexte noté."""

    article_id: str
    num: str
    path: tuple[str, ...]
    text: str
