"""Tableaux du rapport de la 001 : toutes les métriques de la spec, par modèle, delta apparié B − A.

Le verdict ne porte que sur success ; les autres métriques suivent le même calcul (spec § 7).

Usage :
    uv run python experiments/001-mcp-outils-par-intention/python/agent/scripts/report_metrics.py \\
        experiments/001-mcp-outils-par-intention/runs/final-test-*
"""

import argparse
import json
import math
import statistics
from collections import defaultdict
from pathlib import Path

from scipy import stats

METRICS = ["success", "strict_success", "tool_recall", "args_recall", "n_calls", "extra_calls"]
TOKENS = ["input_tokens", "output_tokens"]


def paired(by_item: dict[str, dict[str, list[float]]]) -> tuple[float, float, float]:
    differences = [
        statistics.fmean(v["intent"]) - statistics.fmean(v["rest"]) for v in by_item.values()
    ]
    n = len(differences)
    delta = statistics.fmean(differences)
    half = float(stats.t.ppf(0.975, n - 1)) * statistics.stdev(differences) / math.sqrt(n)
    return delta, delta - half, delta + half


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("run_dirs", nargs="+", type=Path)
    args = parser.parse_args()
    for run_dir in args.run_dirs:
        meta = json.loads((run_dir / "run.json").read_text(encoding="utf-8"))
        lines = [json.loads(line) for line in (run_dir / "records.jsonl").read_text().splitlines()]
        values: dict[str, dict[str, dict[str, list[float]]]] = defaultdict(
            lambda: defaultdict(lambda: defaultdict(list))
        )
        for line in lines:
            execution, score = line["execution"], line["score"]
            for metric in METRICS:
                values[metric][execution["item_id"]][execution["variant"]].append(
                    float(score[metric])
                )
            for token in TOKENS:
                values[token][execution["item_id"]][execution["variant"]].append(
                    float(execution["usage"][token])
                )
        errors = defaultdict(int)
        for line in lines:
            if line["execution"]["error"]:
                errors[line["execution"]["variant"]] += 1
        print(f"\n### {meta['model']} — {run_dir.name} (commit {meta['git_commit'][:7]})")
        print("| Métrique | A (rest) | B (intent) | Delta B − A | IC 95 % |")
        print("|---|---|---|---|---|")
        for metric in METRICS + TOKENS:
            by_item = values[metric]
            mean = {
                v: statistics.fmean(x for item in by_item.values() for x in item[v])
                for v in ("rest", "intent")
            }
            delta, low, high = paired(by_item)
            print(
                f"| `{metric}` | {mean['rest']:.3f} | {mean['intent']:.3f} | {delta:+.3f} |"
                f" [{low:+.3f} ; {high:+.3f}] |"
            )
        print(f"Exécutions en erreur : A {errors['rest']}, B {errors['intent']}")


if __name__ == "__main__":
    main()
