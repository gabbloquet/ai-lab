"""La réponse d'un modèle à un item du golden set, sous la forme canonique de la spec rag-qa.

A (`closed_book`) pose la question seule ; B (`naive_rag`) la pose avec les passages récupérés.
Le modèle répond par l'outil de sortie de Pydantic AI, dont le schéma est `ModelAnswer`. Une sortie
invalide n'a pas de seconde chance : elle compte comme une erreur, donc comme une réponse fausse
(spec § 6), et son taux est publié.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from pydantic import BaseModel
from pydantic_ai import Agent, capture_run_messages
from pydantic_ai.messages import ModelMessage, ModelResponse
from pydantic_ai.models import Model
from pydantic_ai.settings import ModelSettings

from ailab_rag.corpus import Passage
from ailab_rag.prompting import SYSTEM_PROMPT, closed_book_message, rag_message

CLOSED_BOOK = "closed_book"
NAIVE_RAG = "naive_rag"
TOP_K = 5
TEMPERATURE = 0.0


class ModelAnswer(BaseModel):
    answer: str
    abstained: bool
    cited: list[str]


Retriever = Callable[[str], list[Passage]]


def _usage(messages: list[ModelMessage]) -> dict[str, int]:
    responses = [m for m in messages if isinstance(m, ModelResponse)]
    return {
        "input_tokens": sum(r.usage.input_tokens for r in responses),
        "output_tokens": sum(r.usage.output_tokens for r in responses),
    }


async def run_item(
    item: dict,
    *,
    variant: str,
    model: str | Model,
    repeat: int,
    retrieve: Retriever | None = None,
    reraise: Callable[[BaseException], bool] = lambda error: False,
) -> dict[str, Any]:
    """`reraise` laisse passer une erreur d'infrastructure (limite de débit) au lieu de la noter :
    la campagne relance alors l'exécution, au lieu de la compter comme une mauvaise réponse."""
    question = item["question"]
    context: list[str] | None = None
    if variant == NAIVE_RAG:
        if retrieve is None:
            raise ValueError("la variante naive_rag demande une fonction retrieve")
        passages = retrieve(question)
        prompt = rag_message(question, passages)
        context = list(dict.fromkeys(p.article_id for p in passages))
    elif variant == CLOSED_BOOK:
        prompt = closed_book_message(question)
    else:
        raise ValueError(f"variante inconnue : {variant}")

    agent = Agent(
        model,
        output_type=ModelAnswer,
        instructions=SYSTEM_PROMPT,
        retries=0,
        model_settings=ModelSettings(temperature=TEMPERATURE),
    )
    output: ModelAnswer | None = None
    error: str | None = None
    with capture_run_messages() as messages:
        try:
            output = (await agent.run(prompt)).output
        except Exception as exc:
            if reraise(exc):
                raise
            error = f"{type(exc).__name__}: {exc}"

    return {
        "item_id": item["id"],
        "variant": variant,
        "model": model if isinstance(model, str) else model.model_name,
        "repeat": repeat,
        "answer": output.answer if output else "",
        "abstained": output.abstained if output else False,
        "cited": list(output.cited) if output else [],
        "context": context,
        "usage": _usage(messages),
        "error": error,
    }
