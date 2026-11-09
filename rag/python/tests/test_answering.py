"""La réponse d'un modèle à un item, avec un faux modèle : ni coût ni hasard."""

import pytest
from pydantic_ai.messages import (
    ModelMessage,
    ModelRequest,
    ModelResponse,
    ToolCallPart,
    UserPromptPart,
)
from pydantic_ai.models.function import AgentInfo, FunctionModel

from ailab_evals.rag_qa import score_execution
from ailab_rag.answering import CLOSED_BOOK, NAIVE_RAG, run_item
from ailab_rag.corpus import Passage
from ailab_rag.prompting import SYSTEM_PROMPT, closed_book_message, rag_message

pytestmark = pytest.mark.anyio

ITEM = {
    "id": "rq-001",
    "split": "dev",
    "mode": "direct",
    "answerable": True,
    "question": "Achat en ligne : j'ai combien de temps pour me rétracter ?",
    "expected": {
        "facts": [{"accepted": ["quatorze jours", "14 jours"]}],
        "articles": [{"id": "LEGIARTI000032226842", "num": "L221-18"}],
    },
    "evidence": [{"article": "LEGIARTI000032226842", "quote": "quatorze jours"}],
}
P1 = Passage("LEGIARTI000032226842", "L221-18", "Le consommateur dispose de quatorze jours.", 0)
P2 = Passage("LEGIARTI000032221377", "L221-23", "Il supporte les coûts directs de renvoi.", 0)
ANNEX_PART_2 = Passage("LEGIARTI000032221377", "L221-23", "Suite de l'article.", 1)

GOOD = {"answer": "Vous avez 14 jours.", "abstained": False, "cited": ["L. 221-18"]}


@pytest.fixture
def anyio_backend() -> str:
    return "asyncio"


class Recorder:
    """Un faux modèle qui répond par l'outil de sortie et garde ce qu'il a reçu."""

    def __init__(self, args: dict | str = GOOD) -> None:
        self.args = args
        self.prompts: list[str] = []
        self.instructions: list[str | None] = []
        self.calls = 0

    def model(self) -> FunctionModel:
        def respond(messages: list[ModelMessage], info: AgentInfo) -> ModelResponse:
            self.calls += 1
            self.instructions.append(info.instructions)
            self.prompts.extend(
                part.content
                for message in messages
                if isinstance(message, ModelRequest)
                for part in message.parts
                if isinstance(part, UserPromptPart) and isinstance(part.content, str)
            )
            return ModelResponse(parts=[ToolCallPart(info.output_tools[0].name, self.args)])

        return FunctionModel(respond, model_name="fake-model")


async def test_closed_book_sends_the_question_alone_and_reports_no_context() -> None:
    recorder = Recorder()

    execution = await run_item(ITEM, variant=CLOSED_BOOK, model=recorder.model(), repeat=0)

    assert recorder.prompts == [closed_book_message(ITEM["question"])]
    assert recorder.instructions == [SYSTEM_PROMPT]
    assert execution["context"] is None


async def test_naive_rag_sends_the_passages_and_reports_their_articles() -> None:
    recorder = Recorder()
    found = [P2, P1, ANNEX_PART_2]

    execution = await run_item(
        ITEM, variant=NAIVE_RAG, model=recorder.model(), repeat=2, retrieve=lambda q: found
    )

    assert recorder.prompts == [rag_message(ITEM["question"], found)]
    assert recorder.instructions == [SYSTEM_PROMPT]
    # La spec ne garde que la première occurrence d'un article (§ 3.2).
    assert execution["context"] == ["LEGIARTI000032221377", "LEGIARTI000032226842"]


async def test_any_other_variant_is_a_rag_with_its_own_retriever() -> None:
    recorder = Recorder()

    execution = await run_item(
        ITEM, variant="query_rewrite", model=recorder.model(), repeat=0, retrieve=lambda q: [P1]
    )

    assert recorder.prompts == [rag_message(ITEM["question"], [P1])]
    assert execution["variant"] == "query_rewrite"
    assert execution["context"] == [P1.article_id]


async def test_naive_rag_needs_a_retriever() -> None:
    with pytest.raises(ValueError, match="retrieve"):
        await run_item(ITEM, variant=NAIVE_RAG, model=Recorder().model(), repeat=0)


async def test_a_valid_answer_fills_the_canonical_execution() -> None:
    execution = await run_item(ITEM, variant=CLOSED_BOOK, model=Recorder().model(), repeat=1)

    assert execution["item_id"] == "rq-001"
    assert execution["variant"] == CLOSED_BOOK
    assert execution["model"] == "fake-model"
    assert execution["repeat"] == 1
    assert (execution["answer"], execution["abstained"], execution["cited"]) == (
        "Vous avez 14 jours.",
        False,
        ["L. 221-18"],
    )
    assert execution["error"] is None
    assert set(execution["usage"]) == {"input_tokens", "output_tokens"}
    assert all(isinstance(v, int) for v in execution["usage"].values())


async def test_an_invalid_output_is_an_error_without_a_second_attempt() -> None:
    recorder = Recorder(args={"answer": "14 jours"})  # abstained et cited manquent

    execution = await run_item(ITEM, variant=CLOSED_BOOK, model=recorder.model(), repeat=0)

    assert recorder.calls == 1
    assert execution["error"]
    assert (execution["answer"], execution["abstained"], execution["cited"]) == ("", False, [])


async def test_an_infrastructure_error_can_be_reraised() -> None:
    def failing(messages: list[ModelMessage], info: AgentInfo) -> ModelResponse:
        raise ConnectionError("réseau coupé")

    with pytest.raises(ConnectionError):
        await run_item(
            ITEM,
            variant=CLOSED_BOOK,
            model=FunctionModel(failing),
            repeat=0,
            reraise=lambda error: isinstance(error, ConnectionError),
        )


@pytest.mark.parametrize("args", [GOOD, {"answer": "14 jours"}])
async def test_the_execution_goes_through_the_scorer_of_the_spec(args: dict) -> None:
    execution = await run_item(
        ITEM, variant=NAIVE_RAG, model=Recorder(args).model(), repeat=0, retrieve=lambda q: [P1]
    )

    score = score_execution(ITEM, execution)

    assert score.correct is (args is GOOD)


async def test_the_execution_records_how_long_the_generator_took() -> None:
    """Hors spec : le scorer l'ignore, le résumé le publie comme métrique secondaire."""
    ticks = iter([10.0, 12.5])

    execution = await run_item(
        ITEM, variant=CLOSED_BOOK, model=Recorder().model(), repeat=1, clock=lambda: next(ticks)
    )

    assert execution["latency"] == {"generation_s": 2.5}
    assert score_execution(ITEM, execution).as_dict()["correct"] is True


async def test_a_rag_variant_can_send_its_own_grounding() -> None:
    recorder = Recorder()

    await run_item(
        ITEM,
        variant="abstain_strict",
        model=recorder.model(),
        repeat=0,
        retrieve=lambda q: [P1],
        grounding="Consigne plus exigeante.",
    )

    assert recorder.prompts == [
        rag_message(ITEM["question"], [P1], grounding="Consigne plus exigeante.")
    ]
