"""La réponse d'un modèle à un item du golden set, sous la forme canonique de la spec rag-qa.

`closed_book` pose la question seule ; toute autre variante est un RAG, qui pose la question avec
les passages trouvés par sa propre fonction de recherche (`naive_rag`, ou un levier de la série).
Le modèle répond par l'outil de sortie de Pydantic AI, dont le schéma est `ModelAnswer`. Une sortie
invalide n'a pas de seconde chance : elle compte comme une erreur, donc comme une réponse fausse
(spec § 6), et son taux est publié.
"""

from __future__ import annotations

import time
from collections.abc import Callable
from typing import Any

from pydantic import BaseModel
from pydantic_ai import Agent, capture_run_messages
from pydantic_ai.messages import ModelMessage, ModelResponse
from pydantic_ai.models import Model
from pydantic_ai.settings import ModelSettings

from ailab_rag.corpus import Passage
from ailab_rag.prompting import GROUNDING, SYSTEM_PROMPT, closed_book_message, rag_message

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
    clock: Callable[[], float] = time.perf_counter,
    grounding: str = GROUNDING,
    canonical: str = "v1",
) -> dict[str, Any]:
    """`reraise` laisse passer une erreur d'infrastructure (limite de débit) au lieu de la noter :
    la campagne relance alors l'exécution, au lieu de la compter comme une mauvaise réponse.
    `canonical` choisit la forme de l'exécution : celle de la spec rag-qa v1, avec la durée de
    génération hors spec, ou celle de la v2 (§ 3.2), avec `latency_s` de bout en bout."""
    started = clock() if canonical == "v2" else None
    question = item["question"]
    context: list[str] | None = None
    if variant == CLOSED_BOOK:
        prompt = closed_book_message(question)
    else:
        # Toute autre variante est un RAG : naive_rag, ou un levier de la série (query_rewrite…).
        if retrieve is None:
            raise ValueError(f"la variante {variant} demande une fonction retrieve")
        passages = retrieve(question)
        prompt = rag_message(question, passages, grounding)
        context = list(dict.fromkeys(p.article_id for p in passages))

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
        start = clock()
        try:
            output = (await agent.run(prompt)).output
        except Exception as exc:
            if reraise(exc):
                raise
            error = f"{type(exc).__name__}: {exc}"
        generation_s = clock() - start

    execution: dict[str, Any] = {
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
    if started is None:
        # Hors spec rag-qa v1 (§ 3.2), ignoré par le scorer : durée de l'appel au générateur,
        # recherche exclue.
        execution["latency"] = {"generation_s": generation_s}
        return execution
    # Spec rag-qa v2 (§ 3.2) : durée de bout en bout, recherche comprise (caches compris : le
    # protocole dit ce que la mesure couvre). Le coût se calcule après coup, sur un barème daté.
    execution |= {
        "latency_s": start + generation_s - started,
        "cost_usd": None,
        "tool_calls": None,
        "extra": {"generation_s": generation_s},
    }
    return execution
