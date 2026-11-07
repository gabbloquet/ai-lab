from ailab_rag.corpus import Passage, passages


def article(article_id: str, num: str, text: str) -> dict:
    return {
        "id": article_id,
        "num": num,
        "part": "legislative",
        "path": ["Partie législative nouvelle", "Livre II : CONTRATS"],
        "section_id": "LEGISCTA000000000001",
        "text": text,
        "nota": "Note de la DILA.",
        "valid_from": "2016-07-01",
        "valid_to": None,
        "cites": [],
    }


SHORT = article("LEGIARTI000032226842", "L221-18", "Le consommateur dispose de quatorze jours.")


def test_a_short_article_gives_one_passage_with_its_text_intact() -> None:
    assert passages([SHORT]) == [
        Passage(
            article_id="LEGIARTI000032226842",
            num="L221-18",
            text="Le consommateur dispose de quatorze jours.",
            part=0,
        )
    ]


def test_the_indexed_text_carries_neither_number_nor_plan_nor_nota() -> None:
    (passage,) = passages([SHORT])

    assert "L221-18" not in passage.text
    assert "Livre II" not in passage.text
    assert "Note de la DILA" not in passage.text


def test_a_long_article_is_cut_into_pieces_that_keep_its_id() -> None:
    text = "x" * 25
    pieces = passages([article("LEGIARTI000000000001", "R1", text)], max_chars=10)

    assert [len(p.text) for p in pieces] == [10, 10, 5]
    assert [p.part for p in pieces] == [0, 1, 2]
    assert {p.article_id for p in pieces} == {"LEGIARTI000000000001"}
    assert "".join(p.text for p in pieces) == text


def test_a_cut_falls_on_a_line_break_when_there_is_one() -> None:
    text = "alinéa un\nalinéa deux\nalinéa trois"
    pieces = passages([article("LEGIARTI000000000001", "R1", text)], max_chars=15)

    assert [p.text for p in pieces] == ["alinéa un\n", "alinéa deux\n", "alinéa trois"]
    assert all(len(p.text) <= 15 for p in pieces)


def test_an_article_exactly_at_the_limit_stays_whole() -> None:
    pieces = passages([article("LEGIARTI000000000001", "R1", "x" * 10)], max_chars=10)

    assert [p.text for p in pieces] == ["x" * 10]


def test_passages_follow_the_order_of_the_articles() -> None:
    other = article("LEGIARTI000032221377", "L221-23", "Les coûts directs de renvoi.")

    assert [p.num for p in passages([other, SHORT])] == ["L221-23", "L221-18"]


# --- En-tête contextuel (levier de la série) -----------------------------------------------------


def test_without_header_the_indexed_text_is_the_text() -> None:
    (passage,) = passages([SHORT])

    assert passage.header == ""
    assert passage.indexed_text == passage.text


def test_the_header_puts_the_number_and_the_plan_before_the_indexed_text() -> None:
    (passage,) = passages([SHORT], header=True)

    assert passage.header == "Article L221-18\nPartie législative nouvelle > Livre II : CONTRATS"
    assert passage.indexed_text == f"{passage.header}\n\n{passage.text}"


def test_the_header_leaves_the_text_shown_to_the_model_unchanged() -> None:
    (plain,) = passages([SHORT])
    (headed,) = passages([SHORT], header=True)

    assert headed.text == plain.text == "Le consommateur dispose de quatorze jours."


def test_every_piece_of_a_long_article_carries_the_header() -> None:
    pieces = passages([article("LEGIARTI000000000001", "R1", "x" * 25)], max_chars=10, header=True)

    assert {p.header for p in pieces} == {
        "Article R1\nPartie législative nouvelle > Livre II : CONTRATS"
    }
    assert "".join(p.text for p in pieces) == "x" * 25
