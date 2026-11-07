"""Les passages indexés par le RAG naïf : un par article du corpus.

Seul le texte de l'article est indexé, sans son numéro, son plan ni son `nota` (README de la 002,
« Le RAG naïf »). Un article trop long pour le modèle d'embedding est coupé en morceaux qui gardent
l'`id` de l'article : la spec rag-qa ramène chaque passage à son article (§ 3.2).
"""

from __future__ import annotations

from dataclasses import dataclass

# Au-dessus, mistral-embed (8 192 tokens) risquerait de refuser le texte, même à 3 caractères par
# token. Seules quelques annexes du corpus dépassent ce seuil.
MAX_CHARS = 12_000


@dataclass(frozen=True)
class Passage:
    """`text` est ce que lit le modèle ; `indexed_text` est ce qui est transformé en vecteur.
    Sans en-tête, les deux sont identiques : c'est la baseline naïve."""

    article_id: str
    num: str
    text: str
    part: int
    header: str = ""

    @property
    def indexed_text(self) -> str:
        return f"{self.header}\n\n{self.text}" if self.header else self.text


def contextual_header(article: dict) -> str:
    """Levier « en-tête contextuel » : le numéro de l'article et son plan, tirés des données,
    sans appel à un LLM. Seul le texte indexé change ; le prompt reste le même."""
    return f"Article {article['num']}\n{' > '.join(article['path'])}"


def _cut(text: str, max_chars: int) -> list[str]:
    """Coupe en morceaux de `max_chars` caractères au plus, sur le dernier saut de ligne de chaque
    fenêtre s'il y en a un. La concaténation des morceaux redonne le texte."""
    pieces = []
    start = 0
    while len(text) - start > max_chars:
        window = text[start : start + max_chars]
        newline = window.rfind("\n")
        end = start + newline + 1 if newline >= 0 else start + max_chars
        pieces.append(text[start:end])
        start = end
    pieces.append(text[start:])
    return pieces


def passages(
    articles: list[dict], max_chars: int = MAX_CHARS, header: bool = False
) -> list[Passage]:
    return [
        Passage(
            article_id=a["id"],
            num=a["num"],
            text=piece,
            part=part,
            header=contextual_header(a) if header else "",
        )
        for a in articles
        for part, piece in enumerate(_cut(a["text"], max_chars))
    ]
