"""La campagne et son résumé, avec un faux modèle : ni coût ni hasard."""

import json
from pathlib import Path

import pytest
from pydantic_ai.exceptions import ModelHTTPError
from pydantic_ai.messages import ModelMessage, ModelRequest, ModelResponse, ToolCallPart
from pydantic_ai.models.function import AgentInfo, FunctionModel

from ailab_rag.answering import CLOSED_BOOK, NAIVE_RAG
from ailab_rag.campaign import abstention_comparison, run_campaign, summarize
from ailab_rag.corpus import Passage
from ailab_rag.prompting import GROUNDING

pytestmark = pytest.mark.anyio

GOLD = Passage("LEGIARTI000032226842", "L221-18", "Le consommateur dispose de quatorze jours.", 0)
OTHER = Passage("LEGIARTI000032221377", "L221-23", "Il supporte les coûts de renvoi.", 0)


def item(item_id: str, split: str = "test", mode: str = "direct", answerable: bool = True) -> dict:
    return {
        "id": item_id,
        "split": split,
        "mode": mode,
        "answerable": answerable,
        "question": f"Question {item_id} ?",
        "expected": {
            "facts": [{"accepted": ["14 jours"]}] if answerable else [],
            "articles": [{"id": GOLD.article_id, "num": "L221-18"}] if answerable else [],
        },
        "evidence": [{"article": GOLD.article_id, "quote": "quatorze jours"}] if answerable else [],
    }


ITEMS = [item("rq-001"), item("rq-002"), item("rq-003", split="dev")]


@pytest.fixture
def anyio_backend() -> str:
    return "asyncio"


def knows_only_with_context() -> FunctionModel:
    """Répond juste quand des extraits sont fournis, s'abstient sinon."""

    def respond(messages: list[ModelMessage], info: AgentInfo) -> ModelResponse:
        prompt = (
            str(messages[-1].parts[-1].content) if isinstance(messages[-1], ModelRequest) else ""
        )
        if "Extraits" in prompt:
            args = {"answer": "14 jours", "abstained": False, "cited": ["L221-18"]}
        else:
            args = {"answer": "", "abstained": True, "cited": []}
        return ModelResponse(parts=[ToolCallPart(info.output_tools[0].name, args)])

    return FunctionModel(respond, model_name="fake-model")


def retrieve(question: str) -> list[Passage]:
    return [GOLD, OTHER]


def read_lines(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text("utf-8").splitlines()]


# --- Campagne -----------------------------------------------------------------------------------


async def test_runs_every_item_k_times_per_variant_and_saves_each_execution(tmp_path: Path) -> None:
    out = tmp_path / "executions.jsonl"

    executions = await run_campaign(
        ITEMS[:2],
        variants=[CLOSED_BOOK, NAIVE_RAG],
        model=knows_only_with_context(),
        repeats=3,
        retrieve=retrieve,
        out=out,
    )

    assert len(executions) == 2 * 2 * 3
    assert sorted((e["item_id"], e["variant"], e["repeat"]) for e in read_lines(out)) == sorted(
        (e["item_id"], e["variant"], e["repeat"]) for e in executions
    )


async def test_resumes_without_redoing_saved_executions(tmp_path: Path) -> None:
    out = tmp_path / "executions.jsonl"
    await run_campaign(
        ITEMS[:1],
        variants=[CLOSED_BOOK],
        model=knows_only_with_context(),
        repeats=1,
        retrieve=retrieve,
        out=out,
    )
    calls = 0

    def counting(messages: list[ModelMessage], info: AgentInfo) -> ModelResponse:
        nonlocal calls
        calls += 1
        args = {"answer": "", "abstained": True, "cited": []}
        return ModelResponse(parts=[ToolCallPart(info.output_tools[0].name, args)])

    executions = await run_campaign(
        ITEMS[:1],
        variants=[CLOSED_BOOK],
        model=FunctionModel(counting),
        repeats=2,
        retrieve=retrieve,
        out=out,
    )

    assert calls == 1  # seule la répétition 1 manquait
    assert len(executions) == 2 and len(read_lines(out)) == 2


async def test_a_rate_limit_is_retried_instead_of_scored(tmp_path: Path) -> None:
    attempts = 0
    waits: list[float] = []

    def flaky(messages: list[ModelMessage], info: AgentInfo) -> ModelResponse:
        nonlocal attempts
        attempts += 1
        if attempts == 1:
            raise ModelHTTPError(429, "fake-model")
        args = {"answer": "", "abstained": True, "cited": []}
        return ModelResponse(parts=[ToolCallPart(info.output_tools[0].name, args)])

    async def no_wait(seconds: float) -> None:
        waits.append(seconds)

    executions = await run_campaign(
        ITEMS[:1],
        variants=[CLOSED_BOOK],
        model=FunctionModel(flaky),
        repeats=1,
        retrieve=retrieve,
        out=tmp_path / "e.jsonl",
        sleep=no_wait,
    )

    assert executions[0]["error"] is None
    assert len(waits) == 1


async def test_a_lasting_rate_limit_stops_the_campaign(tmp_path: Path) -> None:
    def always_limited(messages: list[ModelMessage], info: AgentInfo) -> ModelResponse:
        raise ModelHTTPError(429, "fake-model")

    async def no_wait(seconds: float) -> None:
        return None

    with pytest.raises(ModelHTTPError):
        await run_campaign(
            ITEMS[:1],
            variants=[CLOSED_BOOK],
            model=FunctionModel(always_limited),
            repeats=1,
            retrieve=retrieve,
            out=tmp_path / "e.jsonl",
            sleep=no_wait,
            max_attempts=3,
        )
    assert not (tmp_path / "e.jsonl").exists() or read_lines(tmp_path / "e.jsonl") == []


# --- Résumé -------------------------------------------------------------------------------------


async def test_summary_reports_each_variant_and_the_verdict_on_test_items(tmp_path: Path) -> None:
    executions = await run_campaign(
        ITEMS,
        variants=[CLOSED_BOOK, NAIVE_RAG],
        model=knows_only_with_context(),
        repeats=2,
        retrieve=retrieve,
        out=tmp_path / "e.jsonl",
    )

    summary = summarize(ITEMS, executions, split="test")

    assert summary["split"] == "test"
    assert summary["n_items"] == 2
    assert summary["variants"][CLOSED_BOOK]["correct"] == 0.0
    assert summary["variants"][NAIVE_RAG]["correct"] == 1.0
    assert summary["variants"][CLOSED_BOOK]["false_abstention"] == 1.0
    assert summary["variants"][NAIVE_RAG]["failure"] == {
        "correct": 1.0,
        "retrieval_miss": 0.0,
        "generation_miss": 0.0,
        "error": 0.0,
    }
    assert summary["variants"][CLOSED_BOOK]["failure"] is None
    assert summary["variants"][NAIVE_RAG]["evidence_recall@1"] == 1.0
    assert summary["variants"][NAIVE_RAG]["by_mode"] == {"direct": 1.0}
    assert summary["comparison"]["n"] == 2
    assert summary["comparison"]["delta"] == 1.0
    assert summary["comparison"]["verdict"] == "b_better"


async def test_summary_on_dev_uses_dev_items_only(tmp_path: Path) -> None:
    executions = await run_campaign(
        ITEMS,
        variants=[CLOSED_BOOK, NAIVE_RAG],
        model=knows_only_with_context(),
        repeats=1,
        retrieve=retrieve,
        out=tmp_path / "e.jsonl",
    )

    summary = summarize(ITEMS, executions, split="dev")

    assert summary["n_items"] == 1
    assert summary["comparison"] is None  # moins de deux items : pas d'intervalle


async def test_each_variant_searches_with_its_own_retriever(tmp_path: Path) -> None:
    seen: dict[str, list[str]] = {"naive_rag": [], "query_rewrite": []}

    def recording(name: str):
        def retrieve(question: str) -> list[Passage]:
            seen[name].append(question)
            return [GOLD]

        return retrieve

    await run_campaign(
        ITEMS[:1],
        variants=[CLOSED_BOOK, NAIVE_RAG, "query_rewrite"],
        model=knows_only_with_context(),
        repeats=1,
        retrievers={NAIVE_RAG: recording("naive_rag"), "query_rewrite": recording("query_rewrite")},
        out=tmp_path / "e.jsonl",
    )

    assert seen == {"naive_rag": ["Question rq-001 ?"], "query_rewrite": ["Question rq-001 ?"]}


async def test_summary_reports_the_generation_time_of_each_variant(tmp_path: Path) -> None:
    executions = await run_campaign(
        ITEMS,
        variants=[CLOSED_BOOK, NAIVE_RAG],
        model=knows_only_with_context(),
        repeats=2,
        retrieve=retrieve,
        out=tmp_path / "e.jsonl",
    )
    rag = [e for e in executions if e["variant"] == NAIVE_RAG and e["item_id"] != "rq-003"]
    for execution, seconds in zip(rag, [1.0, 2.0, 3.0, 10.0], strict=True):
        execution["latency"] = {"generation_s": seconds}

    summary = summarize(ITEMS, executions, split="test")

    assert summary["variants"][NAIVE_RAG]["generation_s"] == {
        "mean": 4.0,
        "median": 2.5,
        "p90": 10.0,
    }


async def test_summary_has_no_generation_time_for_executions_recorded_without_it(
    tmp_path: Path,
) -> None:
    """Les exécutions des 002 à 004 n'ont pas de champ `latency`."""
    executions = await run_campaign(
        ITEMS,
        variants=[CLOSED_BOOK, NAIVE_RAG],
        model=knows_only_with_context(),
        repeats=1,
        retrieve=retrieve,
        out=tmp_path / "e.jsonl",
    )
    for execution in executions:
        execution.pop("latency", None)

    summary = summarize(ITEMS, executions, split="test")

    assert summary["variants"][NAIVE_RAG]["generation_s"] is None


async def test_each_variant_can_have_its_own_grounding(tmp_path: Path) -> None:
    prompts: list[str] = []

    def respond(messages: list[ModelMessage], info: AgentInfo) -> ModelResponse:
        prompts.append(str(messages[-1].parts[-1].content))
        args = {"answer": "14 jours", "abstained": False, "cited": ["L221-18"]}
        return ModelResponse(parts=[ToolCallPart(info.output_tools[0].name, args)])

    await run_campaign(
        ITEMS[:1],
        variants=[NAIVE_RAG, "abstain_strict"],
        model=FunctionModel(respond, model_name="fake-model"),
        repeats=1,
        retrieve=retrieve,
        groundings={"abstain_strict": "Consigne plus exigeante."},
        out=tmp_path / "e.jsonl",
        concurrency=1,
    )

    assert sum("Consigne plus exigeante." in p for p in prompts) == 1
    assert sum(GROUNDING in p for p in prompts) == 1


# --- Verdict à deux critères (006) --------------------------------------------------------------


def execution(item_id: str, variant: str, repeat: int, *, abstained: bool) -> dict:
    return {
        "item_id": item_id,
        "variant": variant,
        "model": "fake-model",
        "repeat": repeat,
        "answer": "" if abstained else "14 jours",
        "abstained": abstained,
        "cited": [] if abstained else ["L221-18"],
        "context": [GOLD.article_id],
        "usage": {},
        "error": None,
    }


ABSTENTION_ITEMS = [
    item("rq-101"),
    item("rq-102"),
    item("rq-103", mode="unanswerable", answerable=False),
    item("rq-104", mode="unanswerable", answerable=False),
    item("rq-105", mode="unanswerable", answerable=False),
]


def test_abstention_comparison_judges_inventions_and_wrong_abstentions() -> None:
    """A invente sur les items sans réponse ; B s'y abstient et répond toujours aux autres."""
    executions = [
        execution(i["id"], v, r, abstained=(v == "strict" and not i["answerable"]))
        for i in ABSTENTION_ITEMS
        for v in ("base", "strict")
        for r in range(2)
    ]

    result = abstention_comparison(
        ABSTENTION_ITEMS, executions, baseline="base", variant="strict", guard_margin=0.03
    )

    assert result["hallucination"]["n"] == 3 and result["hallucination"]["delta"] == -1.0
    assert result["false_abstention"]["n"] == 2 and result["false_abstention"]["delta"] == 0.0
    assert result["verdict"] == "b_better"


def test_abstention_comparison_leaves_out_the_excluded_items() -> None:
    executions = [
        execution(i["id"], v, r, abstained=(v == "strict" and not i["answerable"]))
        for i in ABSTENTION_ITEMS
        for v in ("base", "strict")
        for r in range(2)
    ]

    result = abstention_comparison(
        ABSTENTION_ITEMS,
        executions,
        baseline="base",
        variant="strict",
        guard_margin=0.03,
        exclude={"rq-105"},
    )

    assert result["hallucination"]["n"] == 2
    assert result["excluded"] == ["rq-105"]


async def test_summary_can_leave_out_excluded_items(tmp_path: Path) -> None:
    executions = await run_campaign(
        ITEMS,
        variants=[CLOSED_BOOK, NAIVE_RAG],
        model=knows_only_with_context(),
        repeats=1,
        retrieve=retrieve,
        out=tmp_path / "e.jsonl",
    )

    summary = summarize(ITEMS, executions, split="test", exclude={"rq-002"})

    assert summary["n_items"] == 1
    assert summary["excluded"] == ["rq-002"]


def test_abstention_comparison_ignores_failed_executions() -> None:
    """La spec ne note pas une exécution en erreur : elle ne compte ni pour ni contre."""
    executions = [
        execution(i["id"], v, r, abstained=(v == "strict" and not i["answerable"]))
        for i in ABSTENTION_ITEMS
        for v in ("base", "strict")
        for r in range(2)
    ]
    executions.append({**execution("rq-103", "strict", 2, abstained=False), "error": "Timeout"})

    result = abstention_comparison(
        ABSTENTION_ITEMS, executions, baseline="base", variant="strict", guard_margin=0.03
    )

    assert result["hallucination"]["delta"] == -1.0
