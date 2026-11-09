import json
from pathlib import Path

import pytest
from consommation_rag_qa_build import (
    MAX_QUESTION_WORDS,
    OVERLAP_THRESHOLD,
    Bm25,
    assign_ids,
    build,
    check,
    lexical_overlap,
    main,
    make_item,
    publish,
    question_words,
    quote_in_text,
    render_review_page,
)

A = {
    "id": "LEGIARTI000032226842",
    "num": "L221-18",
    "path": ["Partie législative nouvelle", "Livre II : CONTRATS", "Section 6 : Rétractation"],
    "text": "Le consommateur dispose d'un délai de quatorze jours pour exercer son droit de "
    "rétractation d'un contrat conclu à distance.",
}
B = {
    "id": "LEGIARTI000032221377",
    "num": "L221-23",
    "path": ["Partie législative nouvelle", "Livre II : CONTRATS", "Section 6 : Rétractation"],
    "text": "Le consommateur supporte les coûts directs de renvoi des biens.",
}
C = {
    "id": "LEGIARTI000032226000",
    "num": "L222-1",
    "path": ["Partie législative nouvelle", "Livre II : CONTRATS", "Section 7 : Services"],
    "text": "Les dispositions du présent chapitre s'appliquent aux contrats portant sur des "
    "services financiers, dans un délai de trente jours.",
}
BY_ID = {a["id"]: a for a in (A, B, C)}


def task(mode: str, articles=(A,), split="dev", rank=1) -> dict:
    return {
        "task": f"{mode}-{split}-{rank:03d}",
        "mode": mode,
        "split": split,
        "rank": rank,
        "articles": [a["id"] for a in articles],
        "livre": "Livre II",
    }


def fact(forms, quote, article="L221-18") -> dict:
    return {"accepted": list(forms), "quote": quote, "article": article}


def draft(t: dict, output: dict | None, stop_reason: str = "end_turn") -> dict:
    return {
        "task": t["task"],
        "mode": t["mode"],
        "model_requested": "claude-sonnet-5-5",
        "model": "claude-sonnet-5-5",
        "effort": "medium",
        "prompt_sha256": "0" * 64,
        "created_at": "2026-11-04T16:00:00+00:00",
        "stop_reason": stop_reason,
        "usage": {},
        "output": output,
        "raw_text": "",
    }


GOOD = {
    "question": "De combien de temps dispose-t-on pour se rétracter d'un achat en ligne ?",
    "usable": True,
    "facts": [fact(["quatorze jours", "14 jours"], "délai de quatorze jours")],
    "doubt": "",
}


def errors_of(t: dict, output: dict | None, **kwargs) -> list[str]:
    return check(t, draft(t, output), BY_ID, **kwargs).errors


# --- Contrôles bloquants ------------------------------------------------------------------------


def test_a_good_draft_passes_every_check() -> None:
    result = check(task("direct"), draft(task("direct"), GOOD), BY_ID)
    assert result.errors == []
    assert result.alerts == []


def test_a_missing_or_refused_draft_is_rejected() -> None:
    assert errors_of(task("direct"), None)
    assert check(task("direct"), None, BY_ID).errors


def test_an_article_the_writer_finds_unusable_is_rejected() -> None:
    assert any("inutilisable" in e for e in errors_of(task("direct"), {**GOOD, "usable": False}))


def test_a_draft_written_before_the_usable_flag_counts_as_usable() -> None:
    legacy = {k: v for k, v in GOOD.items() if k != "usable"}
    assert errors_of(task("direct"), legacy) == []


def test_paraphrase_uses_the_threshold_set_by_the_pilot_by_default() -> None:
    assert OVERLAP_THRESHOLD == 0.4
    close = {**GOOD, "question": "Quel délai pour exercer son droit de rétractation à distance ?"}
    assert errors_of(task("paraphrase"), close)


def test_a_form_longer_than_six_words_raises_an_alert() -> None:
    long_form = "le délai de quatorze jours prévu au contrat"
    output = {**GOOD, "facts": [fact(["quatorze jours", long_form], "délai de quatorze jours")]}
    result = check(task("direct"), draft(task("direct"), output), BY_ID)
    assert any("longue" in a for a in result.alerts)


def test_questions_are_limited_to_twenty_words_by_default() -> None:
    assert MAX_QUESTION_WORDS == 20


def test_a_question_longer_than_the_limit_is_rejected() -> None:
    long_question = (
        "Pour un achat fait en ligne la semaine dernière, "
        "combien de temps ai-je pour me rétracter ?"
    )
    assert question_words(long_question) == 16  # le « ? » isolé n'est pas un mot
    assert any(
        "mots" in e
        for e in errors_of(
            task("direct"), {**GOOD, "question": long_question}, max_question_words=15
        )
    )
    assert (
        errors_of(task("direct"), {**GOOD, "question": long_question}, max_question_words=None)
        == []
    )


def test_multi_article_questions_get_a_few_more_words() -> None:
    t = task("multi_article", (A, B))
    output = {
        **GOOD,
        "question": (
            "Achat en ligne : combien de temps pour me rétracter, "
            "et qui paie alors le retour du colis ?"
        ),
        "facts": [
            fact(["quatorze jours"], "délai de quatorze jours"),
            fact(["coûts directs de renvoi"], "coûts directs de renvoi", article="L221-23"),
        ],
    }
    assert question_words(output["question"]) == 17
    assert errors_of(t, output, max_question_words=15) == []


def test_an_empty_question_is_rejected() -> None:
    assert errors_of(task("direct"), {**GOOD, "question": "  "})


@pytest.mark.parametrize("n_facts", [0, 4])
def test_an_answerable_item_has_one_to_three_facts(n_facts: int) -> None:
    facts = [fact(["14 jours"], "délai de quatorze jours")] * n_facts
    assert errors_of(task("direct"), {**GOOD, "facts": facts})


def test_a_quote_must_be_copied_from_its_article() -> None:
    bad = {**GOOD, "facts": [fact(["14 jours"], "délai de 14 jours")]}
    assert any("extrait" in e for e in errors_of(task("direct"), bad))


def test_a_quote_may_differ_only_by_spacing() -> None:
    spaced = {**GOOD, "facts": [fact(["quatorze jours"], "délai  de\nquatorze jours")]}
    assert errors_of(task("direct"), spaced) == []
    assert quote_in_text("délai de quatorze", A["text"])


def test_a_fact_must_point_to_an_article_of_the_task() -> None:
    bad = {**GOOD, "facts": [fact(["14 jours"], "délai de quatorze jours", article="L999-1")]}
    assert errors_of(task("direct"), bad)


def test_one_accepted_form_at_least_must_appear_in_the_quote() -> None:
    bad = {**GOOD, "facts": [fact(["deux semaines"], "délai de quatorze jours")]}
    assert any("forme" in e for e in errors_of(task("direct"), bad))


def test_a_form_that_is_empty_once_normalized_is_rejected() -> None:
    bad = {**GOOD, "facts": [fact(["quatorze jours", " ́ "], "délai de quatorze jours")]}
    assert errors_of(task("direct"), bad)


def test_the_question_must_not_contain_the_answer() -> None:
    leak = {**GOOD, "question": "Le délai de 14 jours vaut-il pour un achat en ligne ?"}
    assert any("réponse" in e for e in errors_of(task("direct"), leak))


def test_multi_article_needs_a_fact_from_each_article() -> None:
    t = task("multi_article", (A, B))
    one_sided = {**GOOD, "question": "Combien de temps pour se rétracter, et qui paie le retour ?"}
    assert errors_of(t, one_sided)
    both = {
        **one_sided,
        "facts": [
            fact(["quatorze jours"], "délai de quatorze jours"),
            fact(["coûts directs de renvoi"], "coûts directs de renvoi", article="L221-23"),
        ],
    }
    assert errors_of(t, both) == []


@pytest.mark.parametrize(
    "cited", ["l'article L. 221-18", "l'article L221-18", "l'article l.221-18"]
)
def test_reference_questions_cite_their_article(cited: str) -> None:
    t = task("reference")
    question = f"Que prévoit {cited} sur la rétractation d'un achat à distance ?"
    assert errors_of(t, {**GOOD, "question": question}) == []


def test_a_reference_question_without_its_number_is_rejected() -> None:
    assert errors_of(task("reference"), GOOD)


def test_a_reference_question_citing_a_longer_number_is_rejected() -> None:
    question = "Que prévoit l'article L. 221-180 sur la rétractation ?"
    assert errors_of(task("reference"), {**GOOD, "question": question})


def test_other_modes_must_not_cite_an_article_number() -> None:
    question = "Selon l'article L. 221-18, combien de temps pour se rétracter ?"
    assert any("numéro" in e for e in errors_of(task("direct"), {**GOOD, "question": question}))


def test_paraphrase_above_the_overlap_threshold_is_rejected() -> None:
    close = {**GOOD, "question": "Quel délai pour exercer son droit de rétractation à distance ?"}
    assert errors_of(task("paraphrase"), close, overlap_threshold=0.3)
    assert errors_of(task("paraphrase"), close, overlap_threshold=None) == []


def test_unanswerable_items_need_a_reason_and_no_fact() -> None:
    t = task("unanswerable")
    output = {"question": "Quel prix pour un timbre fiscal ?", "why_unanswerable": "", "doubt": ""}
    assert errors_of(t, output)
    assert errors_of(t, {**output, "why_unanswerable": "Le code ne fixe aucun prix."}) == []


# --- Alertes ------------------------------------------------------------------------------------


def test_a_doubt_raises_an_alert() -> None:
    result = check(task("direct"), draft(task("direct"), {**GOOD, "doubt": "Formulation ?"}), BY_ID)
    assert result.errors == [] and result.alerts


def test_lost_context_and_unanswerable_are_always_reviewed() -> None:
    t = task("lost_context", (C,))
    output = {
        **GOOD,
        "question": "Pour un service financier, quel délai prévoit le code ?",
        "facts": [fact(["trente jours", "30 jours"], "délai de trente jours", article="L222-1")],
    }
    assert check(t, draft(t, output), BY_ID).alerts


def test_a_form_absent_from_the_article_raises_an_alert() -> None:
    output = {
        **GOOD,
        "facts": [fact(["quatorze jours", "quatorze jour"], "délai de quatorze jours")],
    }
    result = check(task("direct"), draft(task("direct"), output), BY_ID)
    assert result.errors == []
    assert any("quatorze jour" in a for a in result.alerts)


# --- Mesures ------------------------------------------------------------------------------------


def test_lexical_overlap_counts_content_words_of_the_question_found_in_the_article() -> None:
    assert lexical_overlap("Quel délai pour exercer la rétractation ?", A["text"]) == 1.0
    assert lexical_overlap("Combien de temps pour changer d'avis ?", A["text"]) == 0.0
    assert lexical_overlap("Le délai pour changer d'avis ?", A["text"]) == pytest.approx(1 / 3)


def test_bm25_ranks_the_article_sharing_rare_terms_first() -> None:
    index = Bm25([A, B, C])
    assert index.top("services financiers", 2)[0] == C["id"]
    assert index.top("renvoi des biens", 1) == [B["id"]]


# --- Sélection ----------------------------------------------------------------------------------


QUOTAS = {"direct": (1, 1)}


def plan_and_drafts(outputs: dict[tuple[str, int], dict | None]):
    plan, drafts = [], {}
    for (split, rank), output in outputs.items():
        t = task("direct", split=split, rank=rank)
        plan.append(t)
        drafts[t["task"]] = draft(t, output)
    return plan, drafts


def test_selection_keeps_the_first_passing_draft_of_each_split() -> None:
    plan, drafts = plan_and_drafts(
        {("dev", 1): None, ("dev", 2): GOOD, ("dev", 3): GOOD, ("test", 1): GOOD}
    )
    result = build(plan, drafts, BY_ID, QUOTAS, seed=1)

    assert [s.task["task"] for s in result.selected] == ["direct-dev-002", "direct-test-001"]
    assert result.shortages == {}
    assert "direct-dev-001" in result.rejected


def test_a_split_without_enough_passing_drafts_is_reported_short() -> None:
    plan, drafts = plan_and_drafts({("dev", 1): GOOD, ("test", 1): None})
    result = build(plan, drafts, BY_ID, QUOTAS, seed=1)

    assert result.shortages == {("direct", "test"): 1}


def test_a_rejected_review_is_replaced_by_the_next_draft() -> None:
    plan, drafts = plan_and_drafts({("dev", 1): GOOD, ("dev", 2): GOOD, ("test", 1): GOOD})
    review = {"direct-dev-001": {"task": "direct-dev-001", "verdict": "rejete", "note": "flou"}}
    result = build(plan, drafts, BY_ID, QUOTAS, seed=1, review=review)

    assert [s.task["task"] for s in result.selected][0] == "direct-dev-002"


def test_a_correction_replaces_the_question_and_the_facts() -> None:
    plan, drafts = plan_and_drafts({("dev", 1): GOOD, ("test", 1): GOOD})
    correction = {
        "question": "Combien de jours pour se rétracter ?",
        "facts": [{"accepted": ["quatorze jours", "14 jours", "14 j"]}],
    }
    review = {
        "direct-dev-001": {"task": "direct-dev-001", "verdict": "corrige", "correction": correction}
    }
    result = build(plan, drafts, BY_ID, QUOTAS, seed=1, review=review)

    item = result.selected[0].item
    assert item["question"] == "Combien de jours pour se rétracter ?"
    assert item["expected"]["facts"] == [{"accepted": ["quatorze jours", "14 jours", "14 j"]}]


def test_every_selected_item_needs_review() -> None:
    outputs = {("dev", r): {**GOOD, "doubt": "?" if r == 1 else ""} for r in range(1, 6)}
    outputs |= {("test", r): GOOD for r in range(1, 6)}
    plan, drafts = plan_and_drafts(outputs)
    result = build(plan, drafts, BY_ID, {"direct": (5, 5)}, seed=1)

    assert all(s.needs_review for s in result.selected)
    assert set(result.pending_review) == {s.task["task"] for s in result.selected}


def test_reviewed_items_are_no_longer_pending() -> None:
    plan, drafts = plan_and_drafts({("dev", 1): {**GOOD, "doubt": "?"}, ("test", 1): GOOD})
    review = {"direct-dev-001": {"task": "direct-dev-001", "verdict": "ok"}}
    result = build(plan, drafts, BY_ID, QUOTAS, seed=1, review=review)

    assert "direct-dev-001" not in result.pending_review


def test_items_carry_their_articles_and_evidence() -> None:
    plan, drafts = plan_and_drafts({("dev", 1): GOOD, ("test", 1): GOOD})
    item = build(plan, drafts, BY_ID, QUOTAS, seed=1).selected[0].item

    assert item["expected"]["articles"] == [{"id": A["id"], "num": "L221-18"}]
    assert item["evidence"] == [{"article": A["id"], "quote": "délai de quatorze jours"}]
    assert item["answerable"] is True


def test_duplicate_forms_after_normalization_are_merged() -> None:
    output = {
        **GOOD,
        "facts": [fact(["14 jours", "14 Jours", "quatorze jours"], "délai de quatorze jours")],
    }
    plan, drafts = plan_and_drafts({("dev", 1): output, ("test", 1): GOOD})
    item = build(plan, drafts, BY_ID, QUOTAS, seed=1).selected[0].item

    assert item["expected"]["facts"][0]["accepted"] == ["14 jours", "quatorze jours"]


# --- Publication --------------------------------------------------------------------------------


def schema_validator():
    from jsonschema import Draft202012Validator

    path = Path(__file__).resolve().parents[3] / "evals/spec/rag-qa/v1/golden.schema.json"
    return Draft202012Validator(json.loads(path.read_text("utf-8")))


def test_publish_writes_valid_items_with_shuffled_ids(tmp_path: Path) -> None:
    outputs = {(s, r): GOOD for s in ("dev", "test") for r in range(1, 4)}
    plan, drafts = plan_and_drafts(outputs)
    result = build(
        plan,
        drafts,
        BY_ID,
        {"direct": (3, 3)},
        seed=1,
        review={t["task"]: {"task": t["task"], "verdict": "ok"} for t in plan},
    )

    items = publish(result, tmp_path, seed=1)

    validator = schema_validator()
    assert all(list(validator.iter_errors(item)) == [] for item in items)
    assert [i["id"] for i in items] == [f"rq-{n:03d}" for n in range(1, 7)]
    lines = (tmp_path / "items.jsonl").read_text("utf-8").splitlines()
    assert [json.loads(line) for line in lines] == items
    assert [i["split"] for i in items] != ["dev"] * 3 + ["test"] * 3  # mélangés
    assert publish(result, tmp_path / "again", seed=1) == items


def test_publish_refuses_pending_reviews_or_shortages(tmp_path: Path) -> None:
    plan, drafts = plan_and_drafts({("dev", 1): {**GOOD, "doubt": "?"}, ("test", 1): None})
    result = build(plan, drafts, BY_ID, QUOTAS, seed=1)

    with pytest.raises(ValueError, match="relecture|manque"):
        publish(result, tmp_path, seed=1)


# --- Page de relecture --------------------------------------------------------------------------


def test_review_page_shows_the_question_and_highlights_the_quote() -> None:
    plan, drafts = plan_and_drafts(
        {("dev", 1): {**GOOD, "doubt": "Formulation ?"}, ("test", 1): GOOD}
    )
    result = build(plan, drafts, BY_ID, QUOTAS, seed=1)

    html = render_review_page(result, BY_ID, version="pilot", include_all=True)

    assert "De combien de temps dispose-t-on" in html
    assert "<mark>délai de quatorze jours</mark>" in html
    assert "Formulation ?" in html
    assert "direct-dev-001" in html


def test_review_page_lists_dev_items_before_test_items() -> None:
    plan = [task("direct", split="test", rank=1), task("reference", split="dev", rank=1)]
    reference = {**GOOD, "question": "Que prévoit l'article L. 221-18 sur la rétractation ?"}
    drafts = {plan[0]["task"]: draft(plan[0], GOOD), plan[1]["task"]: draft(plan[1], reference)}
    result = build(plan, drafts, BY_ID, {"direct": (0, 1), "reference": (1, 0)}, seed=1)

    html = render_review_page(result, BY_ID, version="v1")

    assert html.index("reference-dev-001") < html.index("direct-test-001")
    assert html.index("Split dev") < html.index("Split test")


def test_review_page_escapes_html() -> None:
    output = {**GOOD, "question": "Quel délai <script>alert(1)</script> pour se rétracter ?"}
    plan, drafts = plan_and_drafts({("dev", 1): output, ("test", 1): GOOD})
    html = render_review_page(
        build(plan, drafts, BY_ID, QUOTAS, seed=1), BY_ID, version="v1", include_all=True
    )

    assert "<script>alert(1)</script>" not in html


# --- Ligne de commande --------------------------------------------------------------------------


def test_cli_writes_a_report_and_a_review_page(tmp_path: Path) -> None:
    golden = tmp_path / "golden"
    (golden / "pilot").mkdir(parents=True)
    (golden / "drafts" / "pilot").mkdir(parents=True)
    plan, drafts = plan_and_drafts({("dev", 1): GOOD})
    (golden / "pilot" / "plan.jsonl").write_text(json.dumps(plan[0]) + "\n", "utf-8")
    (golden / "drafts" / "pilot" / "direct-dev-001.json").write_text(
        json.dumps(drafts["direct-dev-001"]), "utf-8"
    )
    articles = tmp_path / "articles.jsonl"
    articles.write_text("".join(json.dumps(a) + "\n" for a in (A, B, C)), "utf-8")

    main(
        [
            "--version",
            "pilot",
            "--quotas",
            "pilot",
            "--seed",
            "7",
            "--articles",
            str(articles),
            "--golden-dir",
            str(golden),
            "--page",
            str(tmp_path / "review.html"),
        ]
    )

    report = json.loads((golden / "pilot" / "build_report.json").read_text("utf-8"))
    assert report["selected"] == 1
    assert (tmp_path / "review.html").exists()


# --- Publication d'un split ---------------------------------------------------------------------


def all_reviewed(plan: list[dict], split: str) -> dict[str, dict]:
    return {t["task"]: {"task": t["task"], "verdict": "ok"} for t in plan if t["split"] == split}


def test_a_split_can_be_published_once_its_own_items_are_reviewed(tmp_path: Path) -> None:
    outputs = {(s, r): GOOD for s in ("dev", "test") for r in range(1, 4)}
    plan, drafts = plan_and_drafts(outputs)
    result = build(
        plan, drafts, BY_ID, {"direct": (3, 3)}, seed=1, review=all_reviewed(plan, "dev")
    )

    dev_items = publish(result, tmp_path, seed=1, split="dev")

    assert {i["split"] for i in dev_items} == {"dev"} and len(dev_items) == 3
    lines = (tmp_path / "items-dev.jsonl").read_text("utf-8").splitlines()
    assert [json.loads(line) for line in lines] == dev_items
    assert not (tmp_path / "items.jsonl").exists()


def test_dev_ids_do_not_change_when_the_whole_set_is_published(tmp_path: Path) -> None:
    outputs = {(s, r): GOOD for s in ("dev", "test") for r in range(1, 5)}
    plan, drafts = plan_and_drafts(outputs)
    dev_only = build(
        plan, drafts, BY_ID, {"direct": (3, 3)}, seed=1, review=all_reviewed(plan, "dev")
    )
    # Un item test rejeté à la relecture est remplacé par la réserve : les ids dev ne bougent pas.
    full_review = all_reviewed(plan, "dev") | all_reviewed(plan, "test")
    full_review["direct-test-001"] = {"task": "direct-test-001", "verdict": "rejete"}
    full = build(plan, drafts, BY_ID, {"direct": (3, 3)}, seed=1, review=full_review)

    dev_items = publish(dev_only, tmp_path / "dev", seed=1, split="dev")
    all_items = publish(full, tmp_path / "all", seed=1)

    assert dev_items == [i for i in all_items if i["split"] == "dev"]


def test_a_split_with_pending_reviews_is_not_published(tmp_path: Path) -> None:
    plan, drafts = plan_and_drafts({("dev", 1): GOOD, ("test", 1): GOOD})
    result = build(plan, drafts, BY_ID, QUOTAS, seed=1, review=all_reviewed(plan, "test"))

    with pytest.raises(ValueError, match="relecture"):
        publish(result, tmp_path, seed=1, split="dev")


# --- Correction qui change le statut d'un item ---------------------------------------------------


UNANSWERABLE = {
    "question": "Combien de temps pour se rétracter ?",
    "why_unanswerable": "x",
    "doubt": "",
}


def turned_answerable() -> dict:
    return {
        "answerable": True,
        "mode": "direct",
        "facts": [{"accepted": ["quatorze jours", "14 jours"]}],
        "articles": ["L221-18"],
        "evidence": [{"article": "L221-18", "quote": "délai de quatorze jours"}],
    }


def test_a_correction_can_turn_an_unanswerable_item_into_an_answerable_one() -> None:
    t = task("unanswerable", (B,))
    review = {
        t["task"]: {"task": t["task"], "verdict": "corrige", "correction": turned_answerable()}
    }
    result = build(
        [t],
        {t["task"]: draft(t, UNANSWERABLE)},
        BY_ID,
        {"unanswerable": (1, 0)},
        seed=1,
        review=review,
    )

    item = result.selected[0].item
    assert item["answerable"] is True
    assert item["mode"] == "direct"
    assert item["expected"]["articles"] == [{"id": A["id"], "num": "L221-18"}]
    assert item["evidence"] == [{"article": A["id"], "quote": "délai de quatorze jours"}]
    assert "source_article" not in item
    assert list(schema_validator().iter_errors({**item, "id": "rq-001"})) == []


def test_a_correction_quote_must_be_copied_from_its_article() -> None:
    t = task("unanswerable", (B,))
    correction = turned_answerable()
    correction["evidence"] = [{"article": "L221-18", "quote": "délai de 14 jours"}]
    review = {t["task"]: {"task": t["task"], "verdict": "corrige", "correction": correction}}

    with pytest.raises(ValueError, match="extrait"):
        build(
            [t],
            {t["task"]: draft(t, UNANSWERABLE)},
            BY_ID,
            {"unanswerable": (1, 0)},
            seed=1,
            review=review,
        )


# --- Version qui étend une version publiée ------------------------------------------------------


def extended_result(n_base: int, n_new: int):
    """Une base de `n_base` items dev et test, puis `n_new` items dev de plus."""
    outputs = {(s, r): GOOD for s in ("dev", "test") for r in range(1, n_base + 1)}
    outputs |= {("dev", r): GOOD for r in range(n_base + 1, n_base + n_new + 1)}
    plan, drafts = plan_and_drafts(outputs)
    review = {t["task"]: {"task": t["task"], "verdict": "ok"} for t in plan}
    base = build(
        [t for t in plan if t["rank"] <= n_base],
        drafts,
        BY_ID,
        {"direct": (n_base, n_base)},
        seed=1,
        review=review,
    )
    extended = build(
        plan, drafts, BY_ID, {"direct": (n_base + n_new, n_base)}, seed=1, review=review
    )
    return base, extended


def test_an_extension_keeps_the_ids_and_items_of_its_base(tmp_path: Path) -> None:
    base, extended = extended_result(n_base=3, n_new=2)
    base_items = publish(base, tmp_path / "v1", seed=1)

    items = publish(
        extended, tmp_path / "v2", seed=1, base_ids=assign_ids(base, seed=1), base_items=base_items
    )

    assert [i for i in items if i["id"] in {b["id"] for b in base_items}] == base_items
    new = [i for i in items if i["id"] not in {b["id"] for b in base_items}]
    assert sorted(i["id"] for i in new) == ["rq-007", "rq-008"]
    assert {i["split"] for i in new} == {"dev"}


def test_an_extension_refuses_a_base_item_that_changed(tmp_path: Path) -> None:
    base, extended = extended_result(n_base=2, n_new=1)
    base_items = publish(base, tmp_path / "v1", seed=1)
    base_items[0] = {**base_items[0], "question": "Une autre question ?"}

    with pytest.raises(ValueError, match="diffère"):
        publish(
            extended,
            tmp_path / "v2",
            seed=1,
            base_ids=assign_ids(base, seed=1),
            base_items=base_items,
        )


def test_assign_ids_gives_the_ids_publish_writes(tmp_path: Path) -> None:
    base, _ = extended_result(n_base=3, n_new=0)
    items = publish(base, tmp_path, seed=1)
    ids = assign_ids(base, seed=1)

    assert sorted(ids.values()) == [i["id"] for i in items]
    by_task = {s.task["task"]: s.item for s in base.selected}
    assert all({**by_task[task], "id": rq} in items for task, rq in ids.items())


def test_cli_publishes_an_extension_that_keeps_its_base(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """v2 = la v1 publiée, plus des items dev : brouillons, relecture et identifiants repris."""
    import consommation_rag_qa_build as build_module

    monkeypatch.setitem(build_module.QUOTAS, "v1", {"direct": (1, 1)})
    monkeypatch.setitem(build_module.QUOTAS, "v2", {"direct": (2, 1)})
    golden, articles = tmp_path / "golden", tmp_path / "articles.jsonl"
    articles.write_text("".join(json.dumps(a) + "\n" for a in (A, B, C)), "utf-8")
    plan, drafts = plan_and_drafts({("dev", 1): GOOD, ("test", 1): GOOD, ("dev", 2): GOOD})
    for version, tasks in (("v1", plan[:2]), ("v2", plan[2:])):
        (golden / version).mkdir(parents=True, exist_ok=True)
        (golden / "drafts" / version).mkdir(parents=True)
        for t in tasks:
            (golden / "drafts" / version / f"{t['task']}.json").write_text(
                json.dumps(drafts[t["task"]]), "utf-8"
            )
        (golden / "review").mkdir(exist_ok=True)
        (golden / "review" / f"{version}.jsonl").write_text(
            "".join(json.dumps({"task": t["task"], "verdict": "ok"}) + "\n" for t in tasks),
            "utf-8",
        )
    (golden / "v1" / "plan.jsonl").write_text("".join(json.dumps(t) + "\n" for t in plan[:2]))
    (golden / "v2" / "plan.jsonl").write_text("".join(json.dumps(t) + "\n" for t in plan))
    common = ["--seed", "1", "--articles", str(articles), "--golden-dir", str(golden)]
    main(["--version", "v1", "--quotas", "v1", "--publish", *common])

    main(["--version", "v2", "--quotas", "v2", "--base-version", "v1", "--publish", *common])

    v1 = [json.loads(line) for line in (golden / "v1" / "items.jsonl").read_text().splitlines()]
    v2 = [json.loads(line) for line in (golden / "v2" / "items.jsonl").read_text().splitlines()]
    assert [i for i in v2 if i["id"] in {x["id"] for x in v1}] == v1
    assert [i["id"] for i in v2 if i["id"] not in {x["id"] for x in v1}] == ["rq-003"]
    manifest = json.loads((golden / "v2" / "MANIFEST.json").read_text("utf-8"))
    assert manifest["base_version"] == "v1"
    assert manifest["counts"] == {"direct/dev": 2, "direct/test": 1}


def test_cli_chains_extensions_and_keeps_every_published_id(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """v3 étend v2, qui étend v1 : les identifiants de v2 (y compris ses ajouts) sont repris."""
    import consommation_rag_qa_build as build_module

    monkeypatch.setitem(build_module.QUOTAS, "v1", {"direct": (1, 1)})
    monkeypatch.setitem(build_module.QUOTAS, "v2", {"direct": (2, 1)})
    monkeypatch.setitem(build_module.QUOTAS, "v3", {"direct": (2, 2)})
    golden, articles = tmp_path / "golden", tmp_path / "articles.jsonl"
    articles.write_text("".join(json.dumps(a) + "\n" for a in (A, B, C)), "utf-8")
    plan, drafts = plan_and_drafts(
        {("dev", 1): GOOD, ("test", 1): GOOD, ("dev", 2): GOOD, ("test", 2): GOOD}
    )
    tasks = {"v1": plan[:2], "v2": plan[2:3], "v3": plan[3:]}
    for version, own in tasks.items():
        (golden / version).mkdir(parents=True, exist_ok=True)
        (golden / "drafts" / version).mkdir(parents=True)
        for t in own:
            (golden / "drafts" / version / f"{t['task']}.json").write_text(
                json.dumps(drafts[t["task"]]), "utf-8"
            )
        (golden / "review").mkdir(exist_ok=True)
        (golden / "review" / f"{version}.jsonl").write_text(
            "".join(json.dumps({"task": t["task"], "verdict": "ok"}) + "\n" for t in own), "utf-8"
        )
    cumulative = {"v1": plan[:2], "v2": plan[:3], "v3": plan}
    for version, rows in cumulative.items():
        (golden / version / "plan.jsonl").write_text("".join(json.dumps(t) + "\n" for t in rows))
    common = ["--seed", "1", "--articles", str(articles), "--golden-dir", str(golden), "--publish"]
    main(["--version", "v1", "--quotas", "v1", *common])
    main(["--version", "v2", "--quotas", "v2", "--base-version", "v1", *common])

    main(["--version", "v3", "--quotas", "v3", "--base-version", "v2", *common])

    def read(version: str) -> list[dict]:
        return [
            json.loads(line) for line in (golden / version / "items.jsonl").read_text().splitlines()
        ]

    v2, v3 = read("v2"), read("v3")
    assert [i for i in v3 if i["id"] in {x["id"] for x in v2}] == v2
    assert [i["id"] for i in v3 if i["id"] not in {x["id"] for x in v2}] == ["rq-004"]


# --- Modes de la v4 -----------------------------------------------------------------------------


def v4(id_: str, num: str, text: str) -> dict:
    return {
        "id": id_,
        "num": num,
        "path": ["Partie législative nouvelle", "Livre III : CRÉDIT"],
        "text": text,
    }


BR_A = v4(
    "LEGIARTI000000000101",
    "L312-30",
    "L'emprunteur peut se rétracter dans le délai mentionné à l'article L. 312-25. "
    "Le prêteur informe l'emprunteur de cette faculté.",
)
BR_B = v4(
    "LEGIARTI000000000102",
    "L312-25",
    "Pendant un délai de sept jours à compter de l'acceptation de l'offre de crédit "
    "affecté, aucun paiement ne peut être fait.",
)
CMP_A = v4(
    "LEGIARTI000000000103", "L221-24", "Le professionnel rembourse dans un délai de quatorze jours."
)
CMP_B = v4(
    "LEGIARTI000000000104",
    "L221-30",
    "Pour un contrat conclu hors établissement, le délai est de sept jours.",
)
SET = v4(
    "LEGIARTI000000000105",
    "L221-28",
    "Le droit de rétractation ne peut être exercé pour les contrats :\n"
    "1° De fourniture de biens confectionnés selon les spécifications du consommateur ;\n"
    "2° De fourniture de journaux, de périodiques ou de magazines ;\n"
    "3° De fourniture de boissons alcoolisées dont la livraison est différée.",
)
FP = v4(
    "LEGIARTI000000000106",
    "L221-18",
    "Le consommateur dispose d'un délai de quatorze jours pour exercer son droit de rétractation.",
)
FP_ELSEWHERE = v4("LEGIARTI000000000107", "L312-19", "Le délai est de 30 jours pour le crédit.")
V4_BY_ID = {a["id"]: a for a in (BR_A, BR_B, CMP_A, CMP_B, SET, FP, FP_ELSEWHERE)}


def v4_check(mode: str, articles: tuple[dict, ...], output: dict, by_id=V4_BY_ID):
    t = task(mode, articles)
    return check(t, draft(t, {"usable": True, "doubt": "", **output}), by_id)


BRIDGE_OK = {
    "question": "Crédit : combien de temps pour me rétracter après avoir signé ?",
    "link_quote": "dans le délai mentionné à l'article L. 312-25",
    "facts": [fact(["sept jours", "7 jours"], "Pendant un délai de sept jours", "L312-25")],
}


def bridge_errors(**changes) -> list[str]:
    return v4_check("bridge", (BR_A, BR_B), {**BRIDGE_OK, **changes}).errors


def test_a_valid_bridge_passes() -> None:
    result = v4_check("bridge", (BR_A, BR_B), BRIDGE_OK)
    assert (result.errors, result.alerts) == ([], [])


def test_bridge_takes_exactly_one_fact_from_b() -> None:
    assert "2 faits au lieu d'un seul en mode bridge" in bridge_errors(facts=BRIDGE_OK["facts"] * 2)
    from_a = fact(["faculté"], "cette faculté", "L312-30")
    assert "le fait vient de L312-30 au lieu de B (L312-25)" in bridge_errors(facts=[from_a])


def test_bridge_link_quote_is_copied_from_a_and_cites_b() -> None:
    assert "renvoi introuvable dans A (L312-30)" in bridge_errors(
        link_quote="dans le délai prévu à l'article L. 312-25"
    )
    assert "le renvoi ne cite pas B (L312-25)" in bridge_errors(
        link_quote="Le prêteur informe l'emprunteur"
    )


def test_bridge_fact_must_not_be_in_a() -> None:
    a_with_value = {**BR_A, "text": BR_A["text"] + " Ce délai est de sept jours."}
    by_id = {**V4_BY_ID, BR_A["id"]: a_with_value}
    errors = v4_check("bridge", (a_with_value, BR_B), BRIDGE_OK, by_id=by_id).errors
    assert "le fait « sept jours » figure déjà dans A" in errors


def test_bridge_question_close_to_b_is_rejected_and_flagged() -> None:
    close = "Crédit affecté : délai après acceptation de l'offre avant tout paiement ?"
    result = v4_check("bridge", (BR_A, BR_B), {**BRIDGE_OK, "question": close})
    assert any(e.startswith("recouvrement question/B 1.00 > 0.40") for e in result.errors)
    assert "la question est plus proche de B que de A" in result.alerts
    assert result.overlap == 1.0  # en bridge, le recouvrement mesuré est celui avec B


def test_bridge_item_expects_both_articles_and_quotes_the_link_first() -> None:
    t = task("bridge", (BR_A, BR_B))
    item = make_item(t, BRIDGE_OK, V4_BY_ID)
    assert [a["num"] for a in item["expected"]["articles"]] == ["L312-30", "L312-25"]
    assert item["evidence"] == [
        {"article": BR_A["id"], "quote": BRIDGE_OK["link_quote"]},
        {"article": BR_B["id"], "quote": "Pendant un délai de sept jours"},
    ]


# bridge inversé : la question part de l'obligation O ; la sanction S la cite et porte la valeur.
OBLIGATION = v4(
    "LEGIARTI000000000108",
    "L112-3",
    "Lorsque le prix ne peut être calculé à l'avance, le professionnel fournit le mode de calcul "
    "du prix.",
)
SANCTION = v4(
    "LEGIARTI000000000109",
    "L131-6",
    "Tout manquement aux dispositions de l'article L. 112-3 est passible d'une amende "
    "administrative dont le montant ne peut excéder 3 000 euros pour une personne physique.",
)
V4_BY_ID |= {OBLIGATION["id"]: OBLIGATION, SANCTION["id"]: SANCTION}
REVERSE_OK = {
    "question": "Un artisan ne m'a pas dit comment il calculait son devis : il risque quoi ?",
    "link_quote": "Tout manquement aux dispositions de l'article L. 112-3",
    "facts": [fact(["3 000 euros", "3 000 €"], "ne peut excéder 3 000 euros", "L131-6")],
}


def test_a_valid_reverse_bridge_passes() -> None:
    result = v4_check("bridge", (OBLIGATION, SANCTION), REVERSE_OK)
    assert result.errors == []


def test_reverse_bridge_link_quote_is_copied_from_the_sanction() -> None:
    errors = v4_check(
        "bridge", (OBLIGATION, SANCTION), {**REVERSE_OK, "link_quote": "le mode de calcul"}
    ).errors
    assert "renvoi introuvable dans B (L131-6)" in errors


def test_reverse_bridge_item_quotes_the_link_then_the_value() -> None:
    item = make_item(task("bridge", (OBLIGATION, SANCTION)), REVERSE_OK, V4_BY_ID)
    assert [a["num"] for a in item["expected"]["articles"]] == ["L112-3", "L131-6"]
    assert [e["article"] for e in item["evidence"]] == [SANCTION["id"], SANCTION["id"]]


COMPARISON_OK = {
    "question": "Remboursement en ligne et démarchage à domicile : quels délais dans chaque cas ?",
    "facts": [
        fact(["quatorze jours", "14 jours"], "délai de quatorze jours", "L221-24"),
        fact(["sept jours", "7 jours"], "le délai est de sept jours", "L221-30"),
    ],
}


def comparison_errors(**changes) -> list[str]:
    return v4_check("comparison", (CMP_A, CMP_B), {**COMPARISON_OK, **changes}).errors


def test_a_valid_comparison_passes() -> None:
    result = v4_check("comparison", (CMP_A, CMP_B), COMPARISON_OK)
    assert (result.errors, result.alerts) == ([], [])


def test_comparison_takes_one_fact_from_each_article() -> None:
    one = COMPARISON_OK["facts"][:1]
    assert "1 faits au lieu de 2 en mode comparison" in comparison_errors(facts=one)
    both_a = [COMPARISON_OK["facts"][0]] * 2
    assert "aucun fait tiré de L221-30" in comparison_errors(facts=both_a)


def test_comparison_values_differ_and_stay_in_their_article() -> None:
    same = [COMPARISON_OK["facts"][0], {**COMPARISON_OK["facts"][0], "article": "L221-30"}]
    assert "les deux faits ont la même valeur" in comparison_errors(facts=same)
    b_with_a_value = {**CMP_B, "text": CMP_B["text"] + " Sinon, quatorze jours."}
    by_id = {**V4_BY_ID, CMP_B["id"]: b_with_a_value}
    errors = v4_check("comparison", (CMP_A, b_with_a_value), COMPARISON_OK, by_id=by_id).errors
    assert "le fait de L221-24 figure aussi dans L221-30" in errors


def test_comparison_alerts_when_the_values_are_of_different_kinds() -> None:
    fine = fact(["15 000 euros"], "le délai est de sept jours", "L221-30")
    output = {**COMPARISON_OK, "facts": [COMPARISON_OK["facts"][0], fine]}
    alerts = v4_check("comparison", (CMP_A, CMP_B), output).alerts
    assert "les deux faits ne sont pas du même type de valeur" in alerts


def test_comparison_questions_get_a_few_more_words() -> None:
    long = (
        "Remboursement après une commande en ligne et après un démarchage à domicile : "
        "quels sont les délais dans chacun des deux cas ?"
    )
    assert 20 < question_words(long) <= 25
    assert not any("mots" in e for e in comparison_errors(question=long))


SET_OK = {
    "question": "Quels achats ne peut-on pas annuler après coup ?",
    "facts": [
        fact(
            ["biens confectionnés selon les spécifications"],
            "biens confectionnés selon les spécifications du consommateur",
            "L221-28",
        ),
        fact(
            ["journaux", "périodiques", "magazines"],
            "journaux, de périodiques ou de magazines",
            "L221-28",
        ),
        fact(
            ["boissons alcoolisées"],
            "boissons alcoolisées dont la livraison est différée",
            "L221-28",
        ),
    ],
}


def set_errors(facts) -> list[str]:
    return v4_check("set", (SET,), {**SET_OK, "facts": facts}).errors


def test_a_complete_list_passes() -> None:
    assert set_errors(SET_OK["facts"]) == []


def test_a_set_needs_one_fact_per_item() -> None:
    assert "2 faits pour une liste de 3 éléments" in set_errors(SET_OK["facts"][:2])
    twice = [
        *SET_OK["facts"][:2],
        fact(["périodiques"], "de périodiques ou de magazines", "L221-28"),
    ]
    assert "deux faits dans l'élément 2" in set_errors(twice)


def test_a_set_quote_lies_in_the_list() -> None:
    outside = [*SET_OK["facts"][:2], fact(["rétractation"], "Le droit de rétractation", "L221-28")]
    assert "fait 3 : extrait hors de la liste" in set_errors(outside)


def test_a_set_form_must_be_specific_to_its_item() -> None:
    vague = [
        SET_OK["facts"][0],
        fact(["fourniture"], "De fourniture de journaux", "L221-28"),
        SET_OK["facts"][2],
    ]
    assert "fait 2 : la forme « fourniture » figure dans un autre élément" in set_errors(vague)


FALSE_PREMISE_OK = {
    "question": "Achat en ligne : j'ai bien 30 jours pour me rétracter ?",
    "false_value": "30 jours",
    "facts": [fact(["quatorze jours", "14 jours"], "délai de quatorze jours", "L221-18")],
}


def false_premise_errors(**changes) -> list[str]:
    by_id = {FP["id"]: FP}
    return v4_check("false_premise", (FP,), {**FALSE_PREMISE_OK, **changes}, by_id=by_id).errors


def test_a_valid_false_premise_passes() -> None:
    assert false_premise_errors() == []


def test_the_false_value_is_in_the_question_but_not_in_the_article() -> None:
    assert "valeur fausse manquante" in false_premise_errors(false_value="")
    assert "la valeur fausse « 7 jours » ne figure pas dans la question" in false_premise_errors(
        false_value="7 jours"
    )
    q = "Achat en ligne : j'ai bien quatorze jours, ou 14 jours ?"
    assert "la valeur fausse est une forme acceptée" in false_premise_errors(
        question=q, false_value="14 jours"
    )


def test_the_false_value_is_of_the_same_kind_as_the_fact() -> None:
    q = "Achat en ligne : 30 euros pour me rétracter ?"
    assert "la valeur fausse n'est pas du même type que le fait" in false_premise_errors(
        question=q, false_value="30 euros"
    )


def test_a_false_value_found_elsewhere_in_the_code_raises_an_alert() -> None:
    alerts = v4_check("false_premise", (FP,), FALSE_PREMISE_OK).alerts
    assert "la valeur fausse figure dans d'autres articles : L312-19" in alerts


def test_mode_order_knows_every_mode_and_keeps_the_v1_order() -> None:
    from consommation_rag_qa_build import MODE_ORDER
    from consommation_rag_qa_plan import DRAW_ORDER, V1_QUOTAS

    assert set(MODE_ORDER) == set(DRAW_ORDER)
    assert MODE_ORDER[: len(V1_QUOTAS)] == list(V1_QUOTAS)


def test_a_set_form_must_not_appear_in_an_alinea_outside_its_item() -> None:
    text = SET["text"].replace(
        "3° De fourniture de boissons alcoolisées dont la livraison est différée.",
        "3° De fourniture de boissons alcoolisées dont la livraison est différée.\n"
        "Il en va de même pour les magazines vendus au numéro.",
    )
    with_alinea = {**SET, "text": text}
    by_id = {**V4_BY_ID, SET["id"]: with_alinea}
    errors = v4_check("set", (with_alinea,), SET_OK, by_id=by_id).errors
    assert "fait 2 : la forme « magazines » figure ailleurs dans l'article" in errors
