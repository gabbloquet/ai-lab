"""Le banc de mesure de la récupération : il note les contextes avec les règles de la spec
rag-qa v1 (§ 6), sans faire répondre de modèle."""

import pytest

from ailab_evals.rag_qa import score_execution
from ailab_rag.bench import retrieval_report
from ailab_rag.corpus import Passage


def passage(i: int) -> Passage:
    return Passage(f"LEGIARTI{i:012d}", f"L{i}-1", f"texte {i}", 0)


def item(item_id: str, mode: str, gold: list[int], answerable: bool = True) -> dict:
    return {
        "id": item_id,
        "split": "dev",
        "mode": mode,
        "answerable": answerable,
        "question": item_id,
        "expected": {
            "facts": [{"accepted": ["x"]}] if answerable else [],
            "articles": [{"id": passage(g).article_id, "num": passage(g).num} for g in gold],
        },
        "evidence": [{"article": passage(g).article_id, "quote": "x"} for g in gold],
    }


ITEMS = [
    item("q-rank1", "direct", [1]),
    item("q-rank4", "direct", [4]),
    item("q-pair", "multi_article", [1, 9]),
    item("q-none", "unanswerable", [], answerable=False),
]
RANKING = [passage(i) for i in (1, 2, 3, 4, 5, 6, 7, 8, 9, 10)]


def retrieve(question: str) -> list[Passage]:
    return RANKING


@pytest.fixture
def report() -> dict:
    return retrieval_report(ITEMS, retrieve)


def test_only_answerable_items_are_measured(report: dict) -> None:
    assert report["n"] == 3
    assert "unanswerable" not in report["by_mode"]


def test_an_article_at_rank_four_is_in_the_top_five_but_not_the_top_three(report: dict) -> None:
    direct = report["by_mode"]["direct"]

    assert direct["n"] == 2
    assert direct["evidence_recall@1"] == 0.5
    assert direct["evidence_recall@3"] == 0.5
    assert direct["evidence_recall@5"] == 1.0


def test_two_expected_articles_count_half_each_and_all_needs_both(report: dict) -> None:
    pair = report["by_mode"]["multi_article"]

    assert pair["evidence_recall@5"] == 0.5
    assert pair["all_evidence@5"] == 0.0
    assert pair["all_evidence@10"] == 1.0


def test_overall_figures_average_every_measured_item(report: dict) -> None:
    assert report["overall"]["evidence_recall@5"] == pytest.approx((1 + 1 + 0.5) / 3)


def test_figures_match_the_scorer_of_the_spec(report: dict) -> None:
    item_ = ITEMS[2]
    execution = {
        "item_id": item_["id"],
        "variant": "bench",
        "model": "none",
        "repeat": 0,
        "answer": "",
        "abstained": False,
        "cited": [],
        "context": [p.article_id for p in RANKING],
        "usage": {},
        "error": None,
    }
    spec = score_execution(item_, execution).as_dict()

    assert report["items"]["q-pair"]["evidence_recall@3"] == spec["evidence_recall@3"]
    assert report["items"]["q-pair"]["all_evidence@10"] == spec["all_evidence@10"]
