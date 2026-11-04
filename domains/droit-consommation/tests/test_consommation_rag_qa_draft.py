import json
from pathlib import Path

import pytest
from consommation_rag_qa_draft import (
    ANSWERABLE_SCHEMA,
    UNANSWERABLE_SCHEMA,
    WRITER_MODEL,
    WriterResult,
    citation_form,
    draft_task,
    load_prompts,
    render_request,
    run_drafts,
)

PROMPTS = Path(__file__).resolve().parents[1] / "golden" / "rag-qa" / "prompts"

A = {
    "id": "LEGIARTI000032226842",
    "num": "L221-18",
    "path": ["Partie législative nouvelle", "Livre II : CONTRATS", "Section 6 : Rétractation"],
    "text": "Le consommateur dispose d'un délai de quatorze jours.",
}
B = {
    "id": "LEGIARTI000032221377",
    "num": "L221-23",
    "path": ["Partie législative nouvelle", "Livre II : CONTRATS", "Section 6 : Rétractation"],
    "text": "Le consommateur supporte les coûts directs de renvoi des biens.",
}
BY_ID = {A["id"]: A, B["id"]: B}


def task(mode: str, articles: tuple[dict, ...] = (A,), name: str = "t-1") -> dict:
    return {
        "task": name,
        "mode": mode,
        "split": "dev",
        "rank": 1,
        "articles": [a["id"] for a in articles],
        "livre": "Livre II",
    }


GOOD_OUTPUT = {
    "question": "De combien de temps dispose-t-on pour se rétracter ?",
    "facts": [
        {
            "accepted": ["quatorze jours", "14 jours"],
            "quote": "délai de quatorze jours",
            "article": "L221-18",
        }
    ],
    "doubt": "",
}


class FakeWriter:
    """Un rédacteur qui rejoue une réponse fixée et garde les requêtes reçues."""

    def __init__(self, result: WriterResult) -> None:
        self.result = result
        self.requests: list[tuple[str, str, dict]] = []

    def write(self, system: str, user: str, schema: dict) -> WriterResult:
        self.requests.append((system, user, schema))
        return self.result


def ok(output: dict = GOOD_OUTPUT) -> WriterResult:
    return WriterResult(
        model=WRITER_MODEL,
        stop_reason="end_turn",
        text=json.dumps(output, ensure_ascii=False),
        usage={"input_tokens": 900, "output_tokens": 120},
    )


@pytest.fixture(scope="module")
def prompts() -> dict[str, str]:
    return load_prompts(PROMPTS)


def test_prompts_exist_for_every_mode(prompts: dict[str, str]) -> None:
    assert set(prompts) == {
        "system",
        "direct",
        "reference",
        "paraphrase",
        "multi_article",
        "lost_context",
        "unanswerable",
    }


@pytest.mark.parametrize(
    ("num", "citation"),
    [("L221-18", "L. 221-18"), ("R312-9", "R. 312-9"), ("liminaire", "liminaire")],
)
def test_citation_form_writes_numbers_as_the_code_does(num: str, citation: str) -> None:
    assert citation_form(num) == citation


def test_request_shows_each_article_with_its_place_in_the_plan(prompts: dict[str, str]) -> None:
    system, user, schema = render_request(task("direct"), BY_ID, prompts)

    assert system == prompts["system"]
    assert "Article L221-18" in user
    assert "Livre II : CONTRATS > Section 6 : Rétractation" in user
    assert A["text"] in user
    assert prompts["direct"] in user
    assert schema == ANSWERABLE_SCHEMA


def test_reference_mode_gives_the_number_in_its_citation_form(prompts: dict[str, str]) -> None:
    _, user, _ = render_request(task("reference"), BY_ID, prompts)

    assert "l'article L. 221-18" in user
    assert "{citation}" not in user


def test_multi_article_mode_shows_both_articles_in_order(prompts: dict[str, str]) -> None:
    _, user, _ = render_request(task("multi_article", (A, B)), BY_ID, prompts)

    assert user.index("Article A : L221-18") < user.index("Article B : L221-23")


def test_unanswerable_mode_asks_for_no_fact(prompts: dict[str, str]) -> None:
    _, _, schema = render_request(task("unanswerable"), BY_ID, prompts)

    assert schema == UNANSWERABLE_SCHEMA
    assert "facts" not in schema["properties"]


def test_schemas_are_strict_objects() -> None:
    for schema in (ANSWERABLE_SCHEMA, UNANSWERABLE_SCHEMA):
        assert schema["additionalProperties"] is False
        assert set(schema["required"]) == set(schema["properties"])


def test_a_draft_records_the_output_and_its_provenance(prompts: dict[str, str]) -> None:
    draft = draft_task(task("direct"), BY_ID, FakeWriter(ok()), prompts)

    assert draft["task"] == "t-1"
    assert draft["model_requested"] == WRITER_MODEL
    assert draft["model"] == WRITER_MODEL
    assert draft["output"] == GOOD_OUTPUT
    assert draft["stop_reason"] == "end_turn"
    assert draft["usage"] == {"input_tokens": 900, "output_tokens": 120}
    assert len(draft["prompt_sha256"]) == 64
    assert draft["created_at"]


def test_the_prompt_hash_changes_with_the_mode_template(prompts: dict[str, str]) -> None:
    direct = draft_task(task("direct"), BY_ID, FakeWriter(ok()), prompts)
    paraphrase = draft_task(task("paraphrase"), BY_ID, FakeWriter(ok()), prompts)
    again = draft_task(task("direct", name="t-2"), BY_ID, FakeWriter(ok()), prompts)

    assert direct["prompt_sha256"] != paraphrase["prompt_sha256"]
    assert direct["prompt_sha256"] == again["prompt_sha256"]


def test_a_refusal_is_recorded_without_output(prompts: dict[str, str]) -> None:
    refused = WriterResult(model=WRITER_MODEL, stop_reason="refusal", text="", usage={})

    draft = draft_task(task("direct"), BY_ID, FakeWriter(refused), prompts)

    assert draft["output"] is None
    assert draft["stop_reason"] == "refusal"


def test_an_unreadable_output_is_kept_as_raw_text(prompts: dict[str, str]) -> None:
    broken = WriterResult(model=WRITER_MODEL, stop_reason="max_tokens", text='{"quest', usage={})

    draft = draft_task(task("direct"), BY_ID, FakeWriter(broken), prompts)

    assert draft["output"] is None
    assert draft["raw_text"] == '{"quest'


def test_run_drafts_writes_one_file_per_task_and_skips_existing_ones(
    tmp_path: Path, prompts: dict[str, str]
) -> None:
    plan = [task("direct", name="t-1"), task("paraphrase", name="t-2")]
    writer = FakeWriter(ok())

    written = run_drafts(plan, BY_ID, writer, tmp_path, prompts, workers=2)
    assert sorted(written) == ["t-1", "t-2"]
    assert json.loads((tmp_path / "t-1.json").read_text("utf-8"))["output"] == GOOD_OUTPUT

    again = run_drafts(plan, BY_ID, writer, tmp_path, prompts, workers=2)
    assert again == []
    assert len(writer.requests) == 2


def test_run_drafts_can_be_limited_to_some_tasks(tmp_path: Path, prompts: dict[str, str]) -> None:
    plan = [task("direct", name="t-1"), task("paraphrase", name="t-2")]

    written = run_drafts(plan, BY_ID, FakeWriter(ok()), tmp_path, prompts, workers=1, limit=1)

    assert written == ["t-1"]
