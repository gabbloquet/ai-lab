"""Noter de nouveau un run déjà fait sur une autre version du golden set, sans rien rejouer.

Les appels émis sont dans records.jsonl : seule la notation change. Le résultat va dans
rescored-<version>.jsonl, à côté du run, et le résumé s'affiche comme à la fin d'un run.

Usage :
    uv run python experiments/001-mcp-outils-par-intention/python/agent/scripts/rescore_run.py \\
        experiments/001-mcp-outils-par-intention/runs/cycle1-dev --golden v2
"""

import argparse
import hashlib
import json
from dataclasses import asdict
from pathlib import Path

from run_campaign import GOLDENS, read_records, report

from ailab_evals.tool_selection import score_execution


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("run_dir", type=Path)
    parser.add_argument("--golden", required=True)
    args = parser.parse_args()

    meta = json.loads((args.run_dir / "run.json").read_text(encoding="utf-8"))
    golden = GOLDENS / args.golden
    manifest = json.loads((golden / "MANIFEST.json").read_text(encoding="utf-8"))
    items_path = golden / "items.jsonl"
    if hashlib.sha256(items_path.read_bytes()).hexdigest() != manifest["files"]["items.jsonl"]:
        raise SystemExit("Le golden set ne correspond plus à son MANIFEST.")
    items = {i["id"]: i for i in map(json.loads, items_path.read_text().splitlines())}

    lines = read_records(args.run_dir / "records.jsonl")
    for line in lines:
        spec = line["execution"]
        item = items[spec["item_id"]]
        if item["split"] != meta["split"]:
            raise SystemExit(f"{item['id']} n'est plus dans le split {meta['split']}.")
        expectation = item["expected"][spec["variant"]]
        line["score"] = asdict(score_execution(expectation, spec["calls"], spec["error"]))
        line["golden"] = args.golden

    out = args.run_dir / f"rescored-{args.golden}.jsonl"
    out.write_text("".join(json.dumps(line, ensure_ascii=False) + "\n" for line in lines))
    print(f"run {args.run_dir.name}, noté sur le golden set {args.golden}")
    report(meta["split"], lines)


if __name__ == "__main__":
    main()
