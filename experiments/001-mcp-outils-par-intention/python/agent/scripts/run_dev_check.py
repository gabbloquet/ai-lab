"""Vérifier la boucle d'agent de la 001 sur quelques items du split dev, avec un vrai modèle.

Ce n'est pas un cycle d'itération : il sert à voir la boucle tourner de bout en bout. Le script
refuse tout item du split test, qui ne sert qu'au run final.

Usage, avec le serveur de la variante lancé à part et la clé dans .env :
    PYDANTIC_AI_NO_BANNER=1 uv run --env-file .env python \\
        experiments/001-mcp-outils-par-intention/python/agent/scripts/run_dev_check.py \\
        --variant intent --url http://127.0.0.1:8082/mcp
"""

import argparse
import json
from pathlib import Path
from typing import Any

import anyio
from ailab_evals.tool_selection import score_execution

from exp001_agent.loop import run_item

ROOT = Path(__file__).resolve().parents[5]
GOLDEN = ROOT / "domains/magasin/golden/tool-selection/v1/items.jsonl"
SYSTEM_PROMPT = ROOT / "experiments/001-mcp-outils-par-intention/python/prompts/system.md"
DEFAULT_MODEL = "mistral:mistral-small-2603"


def dev_items(intents: list[str]) -> list[dict[str, Any]]:
    """Le premier item dev de chaque intention demandée, dans l'ordre du golden set."""
    items = [json.loads(line) for line in GOLDEN.read_text(encoding="utf-8").splitlines() if line]
    chosen = []
    for intent in intents:
        item = next(i for i in items if i["split"] == "dev" and i["tags"][0] == intent)
        chosen.append(item)
    if any(item["split"] != "dev" for item in chosen):
        raise SystemExit("Refusé : le split test ne sert qu'au run final.")
    return chosen


async def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--variant", choices=["intent", "rest"], required=True)
    parser.add_argument("--url", required=True)
    parser.add_argument("--model", default=DEFAULT_MODEL)
    parser.add_argument("--intents", default="availability,alternative,stores_with_stock")
    args = parser.parse_args()

    system_prompt = SYSTEM_PROMPT.read_text(encoding="utf-8")
    for item in dev_items(args.intents.split(",")):
        execution = await run_item(
            item_id=item["id"],
            question=item["question"],
            store_id=item["context"]["storeId"],
            variant=args.variant,
            url=args.url,
            model=args.model,
            system_prompt=system_prompt,
        )
        score = score_execution(item["expected"][args.variant], execution.calls, execution.error)
        print(f"\n=== {item['id']} ({item['tags'][0]}, magasin {item['context']['storeId']})")
        print(f"question : {item['question']}")
        for call in execution.calls:
            print(f"  appel    : {call['tool']} {json.dumps(call['args'], ensure_ascii=False)}")
        print(f"réponse  : {execution.answer}")
        print(f"erreur   : {execution.error}")
        print(
            f"score    : success={score.success} strict={score.strict_success}"
            f" tool_recall={score.tool_recall} args_recall={score.args_recall}"
            f" n_calls={score.n_calls} extra={score.extra_calls}"
        )
        print(f"tokens   : {execution.usage}")


if __name__ == "__main__":
    anyio.run(main)
