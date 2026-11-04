import json
import math
from collections import Counter
from pathlib import Path

import pytest
from consommation_rag_qa_plan import (
    PILOT_QUOTAS,
    SURPLUS,
    V1_QUOTAS,
    allocate,
    eligible,
    lost_context_candidate,
    main,
    make_plan,
    reference_candidate,
)

LIVRES = ("Livre Ier", "Livre II", "Livre III")


def article(
    i: int,
    *,
    livre: str = "Livre II",
    num: str | None = None,
    text: str | None = None,
    valid_to: str | None = None,
    cites: tuple[str, ...] = (),
) -> dict:
    return {
        "id": f"LEGIARTI{i:012d}",
        "num": num or f"L{100 + i}-1",
        "part": "legislative",
        "path": ["Partie législative nouvelle", f"{livre} : TITRE", "Chapitre Ier"],
        "section_id": "LEGISCTA000000000001",
        "text": text if text is not None else f"Texte de l'article {i}. " * 20,
        "nota": "",
        "valid_from": "2016-07-01",
        "valid_to": valid_to,
        "cites": list(cites),
    }


def corpus(n_per_livre: dict[str, int], start: int = 1) -> list[dict]:
    """Un corpus où chaque article cite le suivant du même livre, et où un sur trois renvoie
    à son contexte."""
    rows: list[dict] = []
    i = start
    for livre, n in n_per_livre.items():
        ids = [f"LEGIARTI{j:012d}" for j in range(i, i + n)]
        for k in range(n):
            text = f"Article {i}. " * 30
            if k % 3 == 0:
                text += "Les dispositions du présent chapitre s'appliquent."
            cites = (ids[k + 1],) if k + 1 < n else ()
            rows.append(article(i, livre=livre, text=text, cites=cites))
            i += 1
    return rows


# --- Éligibilité --------------------------------------------------------------------------------


def test_an_ordinary_article_is_eligible() -> None:
    assert eligible(article(1))


@pytest.mark.parametrize(
    ("case", "row"),
    [
        ("annexe", article(1, num="Annexe à l'article R313-4")),
        ("trop court", article(1, text="x" * 199)),
        ("trop long", article(1, text="x" * 4001)),
        ("abrogation différée", article(1, valid_to="2026-01-01")),
        ("tableau", article(1, text="Tableau :\n" + "\n".join(["a | b"] * 30 + ["x" * 100] * 5))),
    ],
)
def test_ineligible_articles(case: str, row: dict) -> None:
    assert not eligible(row), case


def test_length_bounds_are_inclusive() -> None:
    assert eligible(article(1, text="x" * 200))
    assert eligible(article(1, text="x" * 4000))


@pytest.mark.parametrize(
    "text",
    [
        "Les dispositions du présent chapitre s'appliquent.",
        "La présente section est applicable.",
        "Ce délai court à compter de la livraison.",
        "Ces contrats sont conclus par écrit.",
    ],
)
def test_lost_context_candidates_refer_to_their_context(text: str) -> None:
    assert lost_context_candidate(article(1, text=("Texte. " * 40) + text))


def test_an_article_without_such_a_reference_is_not_a_lost_context_candidate() -> None:
    assert not lost_context_candidate(article(1, text="Le vendeur informe le consommateur. " * 9))


@pytest.mark.parametrize(("num", "ok"), [("L221-18", True), ("R312-9", True), ("D111-8", True)])
def test_reference_candidates_have_a_citable_number(num: str, ok: bool) -> None:
    assert reference_candidate(article(1, num=num)) is ok


def test_a_preliminary_article_is_not_a_reference_candidate() -> None:
    assert not reference_candidate(article(1, num="liminaire"))


# --- Répartition --------------------------------------------------------------------------------


def test_allocate_is_proportional_by_largest_remainder() -> None:
    assert allocate({"a": 50, "b": 30, "c": 20}, 10) == {"a": 5, "b": 3, "c": 2}
    assert allocate({"a": 1, "b": 1, "c": 1}, 2) == {"a": 1, "b": 1, "c": 0}
    assert sum(allocate({"a": 7, "b": 5, "c": 3}, 11).values()) == 11


def test_allocate_never_asks_more_than_available() -> None:
    assert allocate({"a": 1, "b": 1}, 5) == {"a": 1, "b": 1}
    assert allocate({"a": 1, "b": 100}, 50) == {
        "a": 0,
        "b": 50,
    }  # 0,495 contre 49,5 : plus forts restes


# --- Plan ---------------------------------------------------------------------------------------


@pytest.fixture(scope="module")
def big_corpus() -> list[dict]:
    return corpus({"Livre Ier": 300, "Livre II": 600, "Livre III": 300})


@pytest.fixture(scope="module")
def plan(big_corpus: list[dict]) -> list[dict]:
    return make_plan(big_corpus, seed=42, quotas=V1_QUOTAS)


def test_plan_draws_twice_each_quota(plan: list[dict]) -> None:
    counts = Counter((task["mode"], task["split"]) for task in plan)
    for mode, (dev, test) in V1_QUOTAS.items():
        assert counts[(mode, "dev")] == math.ceil(SURPLUS * dev) == 2 * dev, mode
        assert counts[(mode, "test")] == math.ceil(SURPLUS * test) == 2 * test, mode


def test_an_article_serves_only_once_in_the_whole_plan(plan: list[dict]) -> None:
    ids = [a for task in plan for a in task["articles"]]
    assert len(ids) == len(set(ids))


def test_modes_draw_from_their_own_pools(plan: list[dict], big_corpus: list[dict]) -> None:
    by_id = {a["id"]: a for a in big_corpus}
    for task in plan:
        articles = [by_id[i] for i in task["articles"]]
        assert all(eligible(a) for a in articles)
        if task["mode"] == "multi_article":
            first, second = articles
            assert second["id"] in first["cites"]
        else:
            assert len(articles) == 1
        if task["mode"] == "lost_context":
            assert lost_context_candidate(articles[0])
        if task["mode"] == "reference":
            assert reference_candidate(articles[0])


def test_ranks_order_the_tasks_of_each_mode_and_split(plan: list[dict]) -> None:
    groups: dict[tuple[str, str], list[int]] = {}
    for task in plan:
        groups.setdefault((task["mode"], task["split"]), []).append(task["rank"])
    for ranks in groups.values():
        assert ranks == list(range(1, len(ranks) + 1))


def test_task_ids_are_unique_and_readable(plan: list[dict]) -> None:
    ids = [task["task"] for task in plan]
    assert len(ids) == len(set(ids))
    assert plan[0]["task"] == f"{plan[0]['mode']}-{plan[0]['split']}-001"


def test_books_are_represented_in_proportion(plan: list[dict]) -> None:
    direct = Counter(t["livre"] for t in plan if t["mode"] == "direct")
    total = sum(direct.values())
    assert set(direct) == set(LIVRES)
    assert direct["Livre II"] / total == pytest.approx(0.5, abs=0.05)


def test_the_same_seed_gives_the_same_plan(big_corpus: list[dict], plan: list[dict]) -> None:
    assert make_plan(big_corpus, seed=42, quotas=V1_QUOTAS) == plan
    assert make_plan(big_corpus, seed=7, quotas=V1_QUOTAS) != plan


def test_excluded_articles_are_never_drawn(big_corpus: list[dict], plan: list[dict]) -> None:
    excluded = {a for task in plan[:50] for a in task["articles"]}
    other = make_plan(big_corpus, seed=42, quotas=PILOT_QUOTAS, exclude=excluded)
    assert not excluded & {a for task in other for a in task["articles"]}


def test_the_pilot_draws_exactly_twenty_tasks_without_surplus(big_corpus: list[dict]) -> None:
    pilot = make_plan(big_corpus, seed=7, quotas=PILOT_QUOTAS, surplus=1.0)
    assert len(pilot) == sum(dev + test for dev, test in PILOT_QUOTAS.values()) == 20
    assert set(PILOT_QUOTAS) == set(V1_QUOTAS)


def test_a_corpus_too_small_for_the_quotas_is_rejected() -> None:
    with pytest.raises(ValueError, match="lost_context"):
        make_plan(corpus({"Livre II": 40}), seed=42, quotas=V1_QUOTAS)


# --- Ligne de commande --------------------------------------------------------------------------


def write_corpus(directory: Path, rows: list[dict]) -> Path:
    path = directory / "articles.jsonl"
    path.write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in rows), "utf-8")
    return path


def test_cli_writes_the_plan_and_refuses_to_overwrite_it(
    tmp_path: Path, big_corpus: list[dict]
) -> None:
    articles = write_corpus(tmp_path, big_corpus)
    args = ["--articles", str(articles), "--seed", "42", "--version", "v1"]
    args += ["--golden-dir", str(tmp_path / "golden")]
    main(args)

    plan_file = tmp_path / "golden" / "v1" / "plan.jsonl"
    rows = [json.loads(line) for line in plan_file.read_text("utf-8").splitlines()]
    assert rows == make_plan(big_corpus, seed=42, quotas=V1_QUOTAS)

    with pytest.raises(SystemExit):
        main(args)


def test_cli_excludes_the_articles_of_another_plan(tmp_path: Path, big_corpus: list[dict]) -> None:
    articles = write_corpus(tmp_path, big_corpus)
    golden = tmp_path / "golden"
    main(
        [
            "--articles",
            str(articles),
            "--seed",
            "7",
            "--version",
            "pilot",
            "--quotas",
            "pilot",
            "--golden-dir",
            str(golden),
        ]
    )
    main(
        [
            "--articles",
            str(articles),
            "--seed",
            "42",
            "--version",
            "v1",
            "--golden-dir",
            str(golden),
            "--exclude-plan",
            str(golden / "pilot" / "plan.jsonl"),
        ]
    )

    def used(version: str) -> set[str]:
        lines = (golden / version / "plan.jsonl").read_text("utf-8").splitlines()
        return {a for line in lines for a in json.loads(line)["articles"]}

    assert not used("pilot") & used("v1")
