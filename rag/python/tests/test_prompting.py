from ailab_rag.corpus import Passage
from ailab_rag.prompting import (
    GROUNDING,
    SYSTEM_PROMPT,
    closed_book_message,
    question_line,
    rag_message,
)

QUESTION = "Achat en ligne : j'ai combien de temps pour me rétracter ?"
P1 = Passage("LEGIARTI000032226842", "L221-18", "Le consommateur dispose de quatorze jours.", 0)
P2 = Passage("LEGIARTI000032221377", "L221-23", "Il supporte les coûts directs de renvoi.", 0)


def test_the_system_prompt_asks_for_a_value_citations_and_abstention() -> None:
    assert "Code de la consommation" in SYSTEM_PROMPT
    assert "`cited`" in SYSTEM_PROMPT
    assert "`abstained`" in SYSTEM_PROMPT


def test_closed_book_message_is_the_question_alone() -> None:
    assert closed_book_message(QUESTION) == f"Question : {QUESTION}"


def test_rag_message_shows_each_passage_under_its_article_number_in_order() -> None:
    message = rag_message(QUESTION, [P2, P1])

    assert "Article L221-23\nIl supporte les coûts directs de renvoi." in message
    assert "Article L221-18\nLe consommateur dispose de quatorze jours." in message
    assert message.index("L221-23") < message.index("L221-18")


def test_rag_message_only_adds_the_grounding_and_the_extracts_to_the_question() -> None:
    message = rag_message(QUESTION, [P1])

    assert message.startswith(GROUNDING)
    assert message.endswith(closed_book_message(QUESTION))
    assert message.endswith(question_line(QUESTION))
    assert "abstained" in GROUNDING


def test_saying_the_code_is_silent_means_abstaining() -> None:
    """Cycle 1 : « le code ne prévoit rien » doit aller avec `abstained` à vrai."""
    assert "ne prévoit rien" in SYSTEM_PROMPT
    assert "ne fixe pas la valeur demandée" in SYSTEM_PROMPT


def test_the_grounding_asks_to_answer_when_an_extract_holds_the_value() -> None:
    """Cycle 2 : une formulation différente de la question n'est pas une raison de s'abstenir."""
    assert "même si sa formulation diffère" in GROUNDING


def test_rag_message_can_use_another_grounding() -> None:
    """Un levier de génération (006) remplace la phrase d'ancrage, et rien d'autre."""
    other = "Consigne d'ancrage plus exigeante."

    message = rag_message(QUESTION, [P1], grounding=other)

    assert message == rag_message(QUESTION, [P1]).replace(GROUNDING, other)
