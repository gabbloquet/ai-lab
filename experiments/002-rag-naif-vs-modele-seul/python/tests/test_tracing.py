"""Les traces Langfuse d'une campagne, avec un faux client : ni serveur ni réseau."""

from contextlib import contextmanager
from pathlib import Path
from typing import Any

import pytest
from pydantic_ai.messages import ModelMessage, ModelResponse, ToolCallPart
from pydantic_ai.models.function import AgentInfo, FunctionModel

from exp002_rag.answering import CLOSED_BOOK, NAIVE_RAG
from exp002_rag.campaign import run_campaign
from exp002_rag.corpus import Passage
from exp002_rag.tracing import LangfuseTracing

pytestmark = pytest.mark.anyio

GOLD = Passage("LEGIARTI000032226842", "L221-18", "Le consommateur dispose de quatorze jours.", 0)
ITEM = {
    "id": "rq-001",
    "split": "dev",
    "mode": "paraphrase",
    "answerable": True,
    "question": "Achat en ligne : combien de temps pour me rétracter ?",
    "expected": {
        "facts": [{"accepted": ["14 jours"]}],
        "articles": [{"id": GOLD.article_id, "num": "L221-18"}],
    },
    "evidence": [{"article": GOLD.article_id, "quote": "quatorze jours"}],
}


@pytest.fixture
def anyio_backend() -> str:
    return "asyncio"


class FakeSpan:
    def __init__(self) -> None:
        self.output: Any = None

    def update(self, *, output: Any) -> None:
        self.output = output


class FakeClient:
    def __init__(self) -> None:
        self.observations: list[dict[str, Any]] = []
        self.scores: list[dict[str, Any]] = []
        self.flushed = False

    @contextmanager
    def start_as_current_observation(self, *, name: str, as_type: str, input: Any):
        span = FakeSpan()
        self.observations.append({"name": name, "as_type": as_type, "input": input, "span": span})
        yield span

    def get_current_trace_id(self) -> str:
        return f"trace-{len(self.observations)}"

    def create_score(self, **kwargs: Any) -> None:
        self.scores.append(kwargs)

    def flush(self) -> None:
        self.flushed = True


class FakePropagation:
    def __init__(self) -> None:
        self.calls: list[dict[str, Any]] = []

    @contextmanager
    def __call__(self, **kwargs: Any):
        self.calls.append(kwargs)
        yield


def answers_right() -> FunctionModel:
    def respond(messages: list[ModelMessage], info: AgentInfo) -> ModelResponse:
        args = {"answer": "14 jours", "abstained": False, "cited": ["L221-18"]}
        return ModelResponse(parts=[ToolCallPart(info.output_tools[0].name, args)])

    return FunctionModel(respond, model_name="fake-model")


async def traced_campaign(tmp_path: Path, variants: list[str]):
    client, propagation = FakeClient(), FakePropagation()
    tracer = LangfuseTracing(
        client,
        run_id="2026-11-05-dev",
        split="dev",
        model="fake-model",
        propagate=propagation,
        instrument=False,
    )
    await run_campaign(
        [ITEM],
        variants=variants,
        model=answers_right(),
        repeats=1,
        retrieve=lambda q: [GOLD],
        out=tmp_path / "e.jsonl",
        tracer=tracer,
    )
    tracer.flush()
    return client, propagation


async def test_one_trace_per_execution_grouped_by_run(tmp_path: Path) -> None:
    client, propagation = await traced_campaign(tmp_path, [CLOSED_BOOK, NAIVE_RAG])

    assert [o["name"] for o in client.observations] == [
        "rq-001 closed_book #0",
        "rq-001 naive_rag #0",
    ]
    assert {o["input"] for o in client.observations} == {ITEM["question"]}
    assert {call["session_id"] for call in propagation.calls} == {"2026-11-05-dev"}
    assert propagation.calls[1]["tags"] == ["dev", "naive_rag", "paraphrase"]
    assert propagation.calls[1]["metadata"] == {
        "item_id": "rq-001",
        "variant": "naive_rag",
        "repeat": "0",
        "split": "dev",
        "model": "fake-model",
        "mode": "paraphrase",
        "answerable": "True",
    }
    assert client.flushed


async def test_the_trace_output_is_the_canonical_answer(tmp_path: Path) -> None:
    client, _ = await traced_campaign(tmp_path, [NAIVE_RAG])

    assert client.observations[0]["span"].output == {
        "answer": "14 jours",
        "abstained": False,
        "cited": ["L221-18"],
        "context": [GOLD.article_id],
        "error": None,
    }


async def test_the_scores_of_the_spec_are_attached_with_their_type(tmp_path: Path) -> None:
    client, _ = await traced_campaign(tmp_path, [NAIVE_RAG])

    scores = {s["name"]: (s["value"], s["data_type"]) for s in client.scores}
    assert scores["correct"] == (1.0, "BOOLEAN")
    assert scores["failure"] == ("correct", "CATEGORICAL")
    assert scores["evidence_recall@5"] == (1.0, "NUMERIC")
    assert scores["all_evidence@1"] == (1.0, "BOOLEAN")
    assert scores["citation_recall"] == (1.0, "NUMERIC")
    assert {s["trace_id"] for s in client.scores} == {"trace-1"}


async def test_null_metrics_are_not_sent(tmp_path: Path) -> None:
    client, _ = await traced_campaign(tmp_path, [CLOSED_BOOK])

    names = {s["name"] for s in client.scores}
    assert "correct" in names
    assert "failure" not in names  # pas de contexte : diagnostic nul
    assert not any(name.startswith("evidence_recall") for name in names)
    assert "hallucination" not in names  # item avec réponse
