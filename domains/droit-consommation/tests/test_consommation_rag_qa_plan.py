import json
import math
from collections import Counter
from pathlib import Path

import pytest
from consommation_rag_qa_plan import (
    DRAW_ORDER,
    PILOT_QUOTAS,
    SURPLUS,
    V1_QUOTAS,
    V3_QUOTAS,
    V4_PILOT2_QUOTAS,
    V4_PILOT_QUOTAS,
    V4_QUOTAS,
    allocate,
    bridge_candidates,
    canonical_value,
    comparison_candidates,
    eligible,
    enumeration,
    excluded_articles,
    extend_plan,
    false_premise_candidate,
    lost_context_candidate,
    main,
    make_plan,
    reference_candidate,
    reusable_articles,
    set_candidate,
    value_classes,
    writes_number,
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


# --- Extension d'un plan ------------------------------------------------------------------------


def test_extend_appends_tasks_after_the_last_rank(big_corpus: list[dict], plan: list[dict]) -> None:
    extended = extend_plan(big_corpus, plan, mode="paraphrase", split="dev", n=5, seed=42)

    assert extended[: len(plan)] == plan
    added = extended[len(plan) :]
    last = max(t["rank"] for t in plan if t["mode"] == "paraphrase" and t["split"] == "dev")
    assert [t["rank"] for t in added] == list(range(last + 1, last + 6))
    assert all(t["mode"] == "paraphrase" and t["split"] == "dev" and t["extension"] for t in added)
    assert added[0]["task"] == f"paraphrase-dev-{last + 1:03d}"


def test_extend_never_reuses_an_article(big_corpus: list[dict], plan: list[dict]) -> None:
    in_plan = {a for task in plan for a in task["articles"]}
    excluded = {a["id"] for a in big_corpus if a["id"] not in in_plan}
    excluded = set(sorted(excluded)[:100])
    extended = extend_plan(
        big_corpus, plan, mode="paraphrase", split="test", n=20, seed=42, exclude=excluded
    )
    ids = [a for task in extended for a in task["articles"]]
    assert len(ids) == len(set(ids))
    assert not excluded & {a for task in extended[len(plan) :] for a in task["articles"]}


def test_extend_is_deterministic_and_chains(big_corpus: list[dict], plan: list[dict]) -> None:
    once = extend_plan(big_corpus, plan, mode="paraphrase", split="dev", n=3, seed=42)
    assert extend_plan(big_corpus, plan, mode="paraphrase", split="dev", n=3, seed=42) == once
    twice = extend_plan(big_corpus, once, mode="paraphrase", split="dev", n=3, seed=42)
    assert twice[: len(once)] == once and len(twice) == len(once) + 3


def test_cli_extends_an_existing_plan(tmp_path: Path, big_corpus: list[dict]) -> None:
    articles = write_corpus(tmp_path, big_corpus)
    golden = tmp_path / "golden"
    base = [
        "--articles",
        str(articles),
        "--seed",
        "42",
        "--version",
        "v1",
        "--golden-dir",
        str(golden),
    ]
    main(base)
    before = (golden / "v1" / "plan.jsonl").read_text("utf-8").splitlines()

    main([*base, "--extend", "paraphrase:test:4"])

    after = (golden / "v1" / "plan.jsonl").read_text("utf-8").splitlines()
    assert after[: len(before)] == before and len(after) == len(before) + 4


# --- Modes de la v4 -----------------------------------------------------------------------------

PAD = " Texte de remplissage." * 12  # au-dessus des 200 caractères d'un article éligible


def v4_article(
    i: int,
    text: str,
    *,
    titre: str = "Titre II",
    chapitre: str = "Chapitre Ier",
    cites: tuple[str, ...] = (),
    num: str | None = None,
) -> dict:
    row = article(i, text=text + PAD, cites=cites, num=num)
    row["path"] = ["Partie législative nouvelle", "Livre II : X", f"{titre} : Y", chapitre]
    return row


def test_writes_number_accepts_the_usual_spellings() -> None:
    assert writes_number("Le délai mentionné à l'article L. 312-25.", "L312-25")
    assert writes_number("Le délai mentionné à l'article L312-25.", "L312-25")
    assert not writes_number("Le délai mentionné à l'article L. 312-25-1.", "L312-25")
    assert not writes_number("Le délai mentionné à l'article R. 312-25.", "L312-25")


def test_value_classes_reads_durations_amounts_and_rates() -> None:
    assert value_classes("quatorze jours ou 30 jours ; 15 000 euros ; 3 % du prix") == {
        "durée": {"quatorze jours", "30 jours"},
        "montant": {"15 000 euros"},
        "taux": {"3 %"},
    }


@pytest.mark.parametrize(
    ("a", "b"),
    [
        ("3 000 €", "3 000 euros"),
        ("quatorze jours", "14 jours"),
        ("un an", "1 an"),
        ("15\u00a0000 euros", "15 000 euro"),
        ("vingt-quatre heures", "24 heures"),
    ],
)
def test_canonical_value_merges_the_spellings_of_a_value(a: str, b: str) -> None:
    assert canonical_value(a) == canonical_value(b)


def test_canonical_value_keeps_different_values_apart() -> None:
    assert canonical_value("3 000 euros") != canonical_value("15 000 euros")
    assert canonical_value("14 jours") != canonical_value("14 mois")


def test_comparison_sees_the_same_ceiling_written_two_ways() -> None:
    a = v4_article(1, "Une amende de 3 000 € pour une personne physique.")
    b = v4_article(2, "Une amende de 3 000 euros pour une personne physique.")
    assert comparison_candidates([a, b]) == []


# bridge, sens aller : A renvoie à B, qui porte la valeur.
B_VALUE = v4_article(2, "Un délai de sept jours.", num="L312-25")
A_LINK = v4_article(1, "Dans le délai mentionné à l'article L. 312-25.", cites=(B_VALUE["id"],))


def test_bridge_forward_pair_when_a_writes_b_number_and_b_holds_the_value() -> None:
    silent = v4_article(3, "Les dispositions de la présente section.", cites=(B_VALUE["id"],))
    assert bridge_candidates([A_LINK, B_VALUE, silent]) == [(A_LINK["id"], B_VALUE["id"])]


def test_bridge_forward_drops_pairs_where_b_has_no_value_of_its_own() -> None:
    no_value = v4_article(2, "Le professionnel informe le consommateur.", num="L312-25")
    assert bridge_candidates([A_LINK, no_value]) == []
    a_with_value = {**A_LINK, "text": A_LINK["text"] + " Ce délai est de sept jours."}
    assert bridge_candidates([a_with_value, B_VALUE]) == []


def test_bridge_forward_drops_links_lost_in_a_list_of_articles() -> None:
    others = [v4_article(10 + k, "Autre article.", num=f"L312-{30 + k}") for k in range(2)]
    crowded = {**A_LINK, "cites": [B_VALUE["id"], *(o["id"] for o in others)]}
    assert bridge_candidates([crowded, B_VALUE, *others]) == []


def test_bridge_reverse_pair_starts_from_the_obligation_and_ends_at_its_sanction() -> None:
    obligation = v4_article(4, "Le professionnel affiche le mode de calcul du prix.", num="L112-3")
    sanction = v4_article(
        5,
        "Tout manquement à l'article L. 112-3 est passible d'une amende de 3 000 euros.",
        cites=(obligation["id"],),
        num="L131-6",
    )
    assert bridge_candidates([obligation, sanction]) == [(obligation["id"], sanction["id"])]


def test_comparison_pairs_same_chapter_with_no_shared_value() -> None:
    a = v4_article(1, "Un délai de quatorze jours.")
    b = v4_article(2, "Un délai de sept jours.")
    shared = v4_article(3, "Un délai de quatorze jours, ou de trente jours.")
    fine = v4_article(4, "Une amende de 15 000 euros.")
    far = v4_article(5, "Un délai de trois jours.", chapitre="Chapitre II")
    expected = [(a["id"], b["id"]), (b["id"], shared["id"])]
    assert comparison_candidates([a, b, shared, fine, far]) == expected


def test_enumeration_keeps_sub_items_in_their_parent() -> None:
    text = "Contrat :\n1° Le nom ;\n2° Le prix, qui comprend :\na) Les taxes ;\n3° La durée."
    items = enumeration(text)
    assert len(items) == 3 and "Les taxes" in items[1]


def numbered(n: int, preamble: str = "Sont exclus :", item: str = "Élément {k} ;") -> str:
    return preamble + "\n" + "\n".join(f"{k}° " + item.format(k=k) for k in range(1, n + 1))


@pytest.mark.parametrize(
    ("text", "ok"),
    [
        (numbered(3), True),
        (numbered(6), True),
        (numbered(2), False),
        (numbered(7), False),
        (numbered(3, preamble="Sont notamment exclus :"), False),
        (numbered(3, preamble="Pour l'application à Mayotte, sont remplacés :"), False),
        (numbered(3, item="Les dispositions de l'article L. 1{k}-1 ;"), False),
    ],
)
def test_set_candidates_are_closed_lists_of_three_to_six(text: str, ok: bool) -> None:
    assert set_candidate(v4_article(1, text)) is ok


def test_a_set_may_refer_to_an_article_in_a_third_of_its_items() -> None:
    text = numbered(3) + "\n" + "4° Les contrats de l'article L. 221-2 ;"
    assert set_candidate(v4_article(1, text.replace("Sont exclus", "Sont aussi exclus")))


def test_false_premise_candidates_carry_a_value() -> None:
    assert false_premise_candidate(v4_article(1, "Un délai de quatorze jours."))
    assert not false_premise_candidate(v4_article(1, "Le professionnel informe le consommateur."))


def v4_corpus() -> list[dict]:
    """Assez d'articles pour chaque nouveau vivier : listes, valeurs voisines, renvois."""
    rows: list[dict] = []
    for k in range(60):
        rows.append(v4_article(1000 + k, numbered(3)))
    for k in range(80):
        rows.append(v4_article(2000 + k, f"Un délai de {k + 1} jours.", titre=f"Titre {k // 4}"))
    for k in range(60):
        b = v4_article(
            3000 + 2 * k + 1,
            f"Une amende de {k + 1} 000 euros.",
            num=f"L{500 + k}-2",
            titre=f"Titre B{k}",
        )
        rows.append(
            v4_article(
                3000 + 2 * k,
                f"L'amende prévue à l'article L. {500 + k}-2.",
                cites=(b["id"],),
                titre=f"Titre A{k}",
            )
        )
        rows.append(b)
    return rows


@pytest.mark.parametrize("quotas", [V4_PILOT_QUOTAS, V4_PILOT2_QUOTAS])
def test_v4_pilots_draw_each_mode_once_without_surplus(quotas: dict) -> None:
    pilot = make_plan(v4_corpus(), seed=10, quotas=quotas, surplus=1.0)
    counts = Counter(t["mode"] for t in pilot)
    assert counts == {mode: dev for mode, (dev, _) in quotas.items()}
    ids = [a for t in pilot for a in t["articles"]]
    assert len(ids) == len(set(ids))


def test_modes_absent_from_the_quotas_are_not_drawn(plan: list[dict]) -> None:
    assert {t["mode"] for t in plan} == set(V1_QUOTAS)


def test_v4_quotas_extend_v3() -> None:
    assert {m: V4_QUOTAS[m] for m in V3_QUOTAS} == V3_QUOTAS
    assert {m: n for m, n in V4_QUOTAS.items() if m not in V3_QUOTAS} == {
        "comparison": (4, 14),
        "set": (5, 12),
        "false_premise": (10, 30),
    }
    assert DRAW_ORDER[-4:] == ("bridge", "comparison", "set", "false_premise")
    assert "bridge" not in V4_QUOTAS  # retiré après le second pilote (README, « v4 »)
    assert V4_PILOT2_QUOTAS == {"bridge": (10, 0), "comparison": (6, 0), "set": (6, 0)}


def test_extend_draws_a_new_mode_from_its_pool() -> None:
    rows = v4_corpus()
    extended = extend_plan(rows, [], mode="bridge", split="test", n=5, seed=42)
    by_id = {a["id"]: a for a in rows}
    for task in extended:
        a, b = (by_id[i] for i in task["articles"])
        assert writes_number(a["text"], b["num"])


# --- Réutiliser les articles des tâches rejetées ------------------------------------------------


def test_reusable_articles_come_from_rejected_tasks_and_never_from_items() -> None:
    plan = [
        {"task": "direct-dev-001", "articles": ["a1"]},
        {"task": "direct-dev-002", "articles": ["a2"]},
        {"task": "multi_article-dev-001", "articles": ["a3", "a4"]},
        {"task": "direct-dev-003", "articles": ["a5"]},
    ]
    rejected = {"direct-dev-002": ["…"], "multi_article-dev-001": ["…"], "direct-dev-003": ["…"]}
    # a5 : tâche rejetée, mais une correction de relecture en a fait l'article d'un item.
    items = [
        {"expected": {"articles": [{"id": "a1"}]}},
        {"expected": {"articles": [{"id": "a5"}]}},
        {"expected": {"articles": []}, "source_article": "a4"},
    ]
    assert reusable_articles(plan, rejected, items) == {"a2", "a3"}


def test_extend_may_draw_again_the_reusable_articles(big_corpus: list[dict]) -> None:
    base = make_plan(big_corpus, seed=42, quotas=PILOT_QUOTAS, surplus=1.0)
    in_base = {a for t in base for a in t["articles"]}
    free = len([a for a in big_corpus if eligible(a)]) - len(in_base)
    with pytest.raises(ValueError):
        extend_plan(big_corpus, base, mode="direct", split="test", n=free + 1, seed=42)
    freed = frozenset(t["task"] for t in base)
    extended = extend_plan(
        big_corpus, base, mode="direct", split="test", n=free + 1, seed=42, freed_tasks=freed
    )
    assert len(extended) == len(base) + free + 1
    # Un article réutilisé une fois ne se réutilise plus : sa nouvelle tâche n'est pas libérée.
    with pytest.raises(ValueError):
        extend_plan(
            big_corpus,
            extended,
            mode="direct",
            split="test",
            n=len(in_base),
            seed=42,
            freed_tasks=freed,
        )


def test_reused_articles_are_no_longer_excluded(tmp_path: Path) -> None:
    base = tmp_path / "v1"
    base.mkdir()
    tasks = [
        {"task": "direct-dev-001", "articles": ["kept"]},
        {"task": "direct-dev-002", "articles": ["rejected"]},
    ]
    (base / "plan.jsonl").write_text("".join(json.dumps(t) + "\n" for t in tasks), "utf-8")
    (base / "build_report.json").write_text(json.dumps({"rejected": {"direct-dev-002": ["x"]}}))
    (base / "items.jsonl").write_text(json.dumps({"expected": {"articles": [{"id": "kept"}]}}))
    plans = [base / "plan.jsonl"]
    assert excluded_articles(plans, [], tmp_path) == {"kept", "rejected"}
    assert excluded_articles(plans, ["v1"], tmp_path) == {"kept"}


def test_an_article_reused_by_another_plan_stays_excluded(tmp_path: Path) -> None:
    base = tmp_path / "v1"
    base.mkdir()
    task = {"task": "direct-dev-002", "articles": ["rejected"]}
    (base / "plan.jsonl").write_text(json.dumps(task) + "\n", "utf-8")
    (base / "build_report.json").write_text(json.dumps({"rejected": {"direct-dev-002": ["x"]}}))
    (base / "items.jsonl").write_text("", "utf-8")
    pilot = tmp_path / "pilot.jsonl"  # un pilote qui a déjà réutilisé l'article
    pilot.write_text(json.dumps({"task": "set-dev-001", "articles": ["rejected"]}) + "\n")
    assert excluded_articles([base / "plan.jsonl", pilot], ["v1"], tmp_path) == {"rejected"}
