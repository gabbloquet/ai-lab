"""Lanceur de runs de la 001 : chaque item, k fois, sur chaque variante, noté par la spec."""

from collections.abc import Callable, Iterable
from dataclasses import dataclass
from typing import Any

import anyio
from pydantic_ai.exceptions import ModelHTTPError
from pydantic_ai.models import Model

from ailab_evals.tool_selection import ExecutionScore, score_execution
from exp001_agent.loop import Execution, run_item

MAX_ATTEMPTS = 4
TRANSIENT_STATUSES = {429, 500, 502, 503, 504}


@dataclass(frozen=True)
class Record:
    execution: Execution
    score: ExecutionScore
    attempts: int
    """Tentatives faites : une limite de débit du fournisseur relance l'exécution."""


async def run_campaign(
    *,
    items: list[dict[str, Any]],
    servers: dict[str, str],
    model: str | Model,
    repeats: int,
    system_prompt: str,
    done: Iterable[tuple[str, str, int]] = (),
    concurrency: int = 1,
    backoff_seconds: float = 5.0,
    on_record: Callable[[Record], None] = lambda record: None,
) -> list[Record]:
    """Joue item × variante × répétition, sauf ce qui est déjà dans `done` (reprise d'un run)."""
    already = set(done)
    todo = [
        (item, variant, url, repeat)
        for item in items
        for variant, url in servers.items()
        for repeat in range(repeats)
        if (item["id"], variant, repeat) not in already
    ]
    records: list[Record | None] = [None] * len(todo)
    limiter = anyio.CapacityLimiter(concurrency)

    async def play(index: int, item: dict[str, Any], variant: str, url: str, repeat: int) -> None:
        async with limiter:
            execution, attempts = await _with_retries(
                item, variant, url, repeat, model, system_prompt, backoff_seconds
            )
        score = score_execution(item["expected"][variant], execution.calls, execution.error)
        record = Record(execution=execution, score=score, attempts=attempts)
        records[index] = record
        on_record(record)

    async with anyio.create_task_group() as group:
        for index, (item, variant, url, repeat) in enumerate(todo):
            group.start_soon(play, index, item, variant, url, repeat)
    return [record for record in records if record is not None]


async def _with_retries(
    item: dict[str, Any],
    variant: str,
    url: str,
    repeat: int,
    model: str | Model,
    system_prompt: str,
    backoff_seconds: float,
) -> tuple[Execution, int]:
    for attempt in range(1, MAX_ATTEMPTS + 1):
        try:
            execution = await run_item(
                item_id=item["id"],
                question=item["question"],
                store_id=item["context"]["storeId"],
                variant=variant,
                url=url,
                model=model,
                system_prompt=system_prompt,
                repeat=repeat,
                reraise=_is_transient,
            )
            return execution, attempt
        except ModelHTTPError as error:
            if attempt == MAX_ATTEMPTS:
                # Toujours limité après plusieurs essais : l'exécution est notée en erreur.
                return _failed(item, variant, model, repeat, error), attempt
            await anyio.sleep(error.retry_after or backoff_seconds * attempt)
    raise AssertionError("unreachable")


def _is_transient(error: BaseException) -> bool:
    return isinstance(error, ModelHTTPError) and error.status_code in TRANSIENT_STATUSES


def _failed(
    item: dict[str, Any], variant: str, model: str | Model, repeat: int, error: Exception
) -> Execution:
    return Execution(
        item_id=item["id"],
        variant=variant,
        model=model if isinstance(model, str) else model.model_name,
        repeat=repeat,
        calls=[],
        usage={"input_tokens": 0, "output_tokens": 0},
        error=f"{type(error).__name__}: {error}",
        answer=None,
    )
