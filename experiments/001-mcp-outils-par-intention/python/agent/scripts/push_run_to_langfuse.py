"""Envoyer dans Langfuse un run déjà fait, depuis son records.jsonl (sans les spans du modèle).

Sert aux runs lancés sans --langfuse, comme le run 0 de la 001 : la trace porte la question,
les appels, la réponse et les scores de la spec, mais pas le détail des requêtes au modèle.

Usage :
    uv run --env-file .env python \\
        experiments/001-mcp-outils-par-intention/python/agent/scripts/push_run_to_langfuse.py \\
        experiments/001-mcp-outils-par-intention/runs/cycle1-dev
"""

import argparse
import json
from pathlib import Path

from langfuse import Langfuse

from ailab_evals.langfuse_setup import check_reachable, credentials
from ailab_evals.tool_selection import ExecutionScore
from exp001_agent.campaign import Record
from exp001_agent.loop import Execution
from exp001_agent.tracing import LangfuseTracing

ROOT = Path(__file__).resolve().parents[5]
GOLDENS = ROOT / "domains/magasin/golden/tool-selection"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("run_dir", type=Path)
    args = parser.parse_args()

    meta = json.loads((args.run_dir / "run.json").read_text(encoding="utf-8"))
    if meta.get("langfuse"):
        raise SystemExit("Ce run a déjà été tracé dans Langfuse pendant son exécution.")
    items = {
        item["id"]: item
        for item in map(
            json.loads,
            (GOLDENS / meta["golden"]["version"] / "items.jsonl").read_text().splitlines(),
        )
    }
    lines = [json.loads(line) for line in (args.run_dir / "records.jsonl").read_text().splitlines()]

    base_url, public_key, secret_key = credentials(ROOT / "infra/langfuse/.env")
    check_reachable(base_url)
    client = Langfuse(public_key=public_key, secret_key=secret_key, base_url=base_url)
    tracer = LangfuseTracing(
        client, run_id=args.run_dir.name, split=meta["split"], model=meta["model"]
    )
    for line in lines:
        spec = line["execution"]
        record = Record(
            execution=Execution(**spec, answer=line["answer"]),
            score=ExecutionScore(**line["score"]),
            attempts=line["attempts"],
        )
        item = items[spec["item_id"]]
        with tracer.execution(item=item, variant=spec["variant"], repeat=spec["repeat"]) as observe:
            observe(record)
    tracer.flush()
    print(f"{len(lines)} exécutions envoyées, session {args.run_dir.name}")


if __name__ == "__main__":
    main()
