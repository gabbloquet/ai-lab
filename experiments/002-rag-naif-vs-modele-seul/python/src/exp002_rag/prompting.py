"""Les prompts des deux variantes, validés le 2026-11-05 ; consigne d'abstention du cycle 1 et
phrase d'ancrage du cycle 2 de B validées le 2026-11-07.

Le prompt système est le même pour A et B. Le message de B ajoute seulement, avant la question,
la phrase d'ancrage (cycle 2 de B) et les extraits récupérés : c'est la seule différence
d'instruction entre les variantes (README de la 002, « Protocole »).
"""

from __future__ import annotations

from ailab_rag.corpus import Passage

SYSTEM_PROMPT = (
    "Tu réponds à des questions sur le Code de la consommation français. Réponds en français, "
    "en une ou deux phrases, en donnant la valeur demandée (durée, montant, organisme…). "
    "Dans `cited`, indique le numéro de chaque article sur lequel tu t'appuies, un par élément "
    "(par exemple « L. 221-18 »). Si le Code de la consommation ne fixe pas la valeur demandée, "
    "ou si tu ne la connais pas avec certitude, mets `abstained` à vrai. Dès que ta réponse "
    "revient à dire que le code ne prévoit rien ou ne précise pas cette valeur, `abstained` doit "
    "être vrai."
)

GROUNDING = (
    "Réponds à partir des extraits ci-dessous. Si un extrait contient la valeur demandée, "
    "réponds, même si sa formulation diffère de celle de la question. S'ils ne permettent pas "
    "de répondre, mets `abstained` à vrai."
)


def question_line(question: str) -> str:
    return f"Question : {question}"


def closed_book_message(question: str) -> str:
    """A pose la question seule. Le cycle 2 de A (une phrase sur ses connaissances) n'a rien
    apporté sur le dev (0,41 → 0,39) : A garde la configuration de son cycle 1."""
    return question_line(question)


def rag_message(question: str, passages: list[Passage]) -> str:
    extracts = "\n\n---\n\n".join(f"Article {p.num}\n{p.text}" for p in passages)
    return (
        f"{GROUNDING}\n\nExtraits du Code de la consommation :\n\n{extracts}\n\n---\n\n"
        f"{question_line(question)}"
    )
