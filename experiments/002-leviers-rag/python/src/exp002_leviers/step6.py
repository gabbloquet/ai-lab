"""Étape 6 de la 002 : s'abstenir quand le meilleur score de reclassement Cohere de la question est
sous un seuil (README de l'expérience, « Étape 6 »).

A est le RAG à 20 passages du run consolidé, gelé : ses exécutions telles quelles. B en reprend
chaque réponse, sauf pour les questions dont le meilleur score est sous le seuil, où il s'abstient
sans appeler le générateur. B se calcule donc sans aucun appel : les notes Cohere sont lues dans le
cache, qu'un manque arrête au lieu de déclencher un appel.

    uv run python -m exp002_leviers.step6 --split dev
"""

from __future__ import annotations

import argparse
import json
import sys
from collections.abc import Callable, Collection, Mapping
from pathlib import Path
from typing import Any

from ailab_rag import cli
from ailab_rag.campaign import abstention_comparison, read_jsonl, summarize
from exp002_leviers.configurations import TOP_K_20
from exp002_leviers.paths import AUDIT, CACHE_DIR, EXPERIMENT_DIR, GOLDEN, ROOT
from exp006_rag.campaign import GUARD_MARGIN, excluded_items

BASELINE = TOP_K_20
VARIANT = "abstain_low_rerank"
# Fixé par la pré-étude du `dev` (README) : le seuil le plus haut qui n'écarte aucune question
# avec réponse. Il ne change plus.
THRESHOLD = 0.20
# Commit de gel du run consolidé, dont A reprend les exécutions `test`.
FROZEN_COMMIT = "f836315"
MODELS = (
    "mistral:mistral-small-2603",
    "mistral:ministral-14b-2512",
    "google:gemini-3.5-flash-lite",
)
RUN_DATE = "2026-11-09"


def apply_threshold(
    executions: list[dict], best_scores: Mapping[str, float], threshold: float = THRESHOLD
) -> list[dict]:
    """Les exécutions de B, une par exécution de A (`top_k_20`). Sous le seuil, une abstention
    sans appel : ni tokens, ni temps de génération, ni erreur. Le contexte reste celui de A, car la
    recherche a eu lieu. `threshold_abstention`, hors spec, est ignoré par le scorer."""
    variant = []
    for e in executions:
        if e["variant"] != BASELINE:
            continue
        if e["item_id"] not in best_scores:
            raise KeyError(f"{e['item_id']} : aucun score de reclassement")
        below = best_scores[e["item_id"]] < threshold
        b = {**e, "variant": VARIANT, "threshold_abstention": below}
        if below:
            b |= {
                "answer": "",
                "abstained": True,
                "cited": [],
                "usage": {"input_tokens": 0, "output_tokens": 0},
                "error": None,
                "latency": {"generation_s": 0.0},
            }
        variant.append(b)
    return variant


def judge(
    items: list[dict],
    baseline: list[dict],
    best_scores: Mapping[str, float],
    *,
    split: str,
    exclude: Collection[str] = frozenset(),
    threshold: float = THRESHOLD,
) -> dict[str, Any]:
    """Verdict à deux critères de l'étape 5, delta de `correct` (secondaire) et part des
    questions sous le seuil, sur les items valides du `split`."""
    a = [e for e in baseline if e["variant"] == BASELINE]
    executions = a + apply_threshold(a, best_scores, threshold)
    kept = [i for i in items if i["split"] == split and i["id"] not in exclude]
    secondary = summarize(
        items, executions, split=split, baseline=BASELINE, variant=VARIANT, exclude=exclude
    )

    def below(answerable: bool) -> list[int]:
        group = [i for i in kept if i["answerable"] == answerable]
        return [sum(best_scores[i["id"]] < threshold for i in group), len(group)]

    return {
        "split": split,
        "threshold": threshold,
        "abstention": abstention_comparison(
            items,
            executions,
            baseline=BASELINE,
            variant=VARIANT,
            guard_margin=GUARD_MARGIN,
            split=split,
            exclude=exclude,
        ),
        "correct": secondary["comparison"],
        "below_threshold": {"answerable": below(True), "unanswerable": below(False)},
        "configurations": secondary["variants"],
    }


def frozen_baseline(run_dir: Path, *, split: str) -> list[dict]:
    """Les exécutions de A. Sur le `test`, elles doivent venir du run final du run consolidé."""
    run = json.loads((run_dir / "summary.json").read_text(encoding="utf-8"))["run"]
    if split == "test":
        if not run["commit"].startswith(FROZEN_COMMIT):
            sys.exit(f"{run_dir.name} : pas le commit de gel du run consolidé ({FROZEN_COMMIT})")
        if not run["final"]:
            sys.exit(f"{run_dir.name} : pas le run final du run consolidé")
    return read_jsonl(run_dir / "executions.jsonl")


def _best_scores(questions: Mapping[str, str]) -> dict[str, float]:
    from ailab_rag.corpus import passages
    from ailab_rag.embeddings import MODEL, CachedEmbedder
    from ailab_rag.reranking import RerankingRetriever
    from ailab_rag.retrieval import build_index
    from exp002_leviers.paths import ARTICLES
    from exp002_leviers.reproduction import CacheOnlyEmbedder, CacheOnlyReranker
    from exp005_rag.campaign import RERANKER

    embedder = CachedEmbedder(CacheOnlyEmbedder(MODEL), CACHE_DIR / "embeddings")
    index = build_index(passages(read_jsonl(ARTICLES)), embedder)
    reranker = RerankingRetriever(
        index, embedder, CacheOnlyReranker(f"cohere:{RERANKER}"), cache_dir=CACHE_DIR / "rerank"
    )
    return {item_id: reranker.best_score(q) for item_id, q in questions.items()}


def main(
    argv: list[str] | None = None,
    git_is_clean: Callable[[], bool] = lambda: cli.git_is_clean(ROOT),
) -> None:
    parser = argparse.ArgumentParser(description="Étape 6 de la 002")
    parser.add_argument("--split", choices=["dev", "test"], required=True)
    parser.add_argument("--final", action="store_true", help="le calcul unique sur le test")
    args = parser.parse_args(argv)

    if args.split == "test" and not args.final:
        sys.exit("le split test ne se calcule qu'une fois, pour le verdict : ajoutez --final")
    if args.final and not git_is_clean():
        sys.exit(
            "calcul final refusé : l'arbre git n'est pas propre, faites d'abord le commit de gel"
        )

    excluded = excluded_items(AUDIT)
    items = read_jsonl(GOLDEN)
    questions = {
        i["id"]: i["question"]
        for i in items
        if i["split"] == args.split and i["id"] not in excluded
    }
    best = _best_scores(questions)
    commit = cli.current_commit(ROOT)

    for model in MODELS:
        slug = model.replace(":", "-").replace("/", "-")
        source = EXPERIMENT_DIR / "runs" / f"{RUN_DATE}-{slug}-{args.split}"
        baseline = frozen_baseline(source, split=args.split)
        result = judge(items, baseline, best, split=args.split, exclude=excluded)
        result["run"] = {
            "model": model,
            "baseline_run": cli.display_path(source, ROOT),
            "golden": cli.display_path(GOLDEN, ROOT),
            "audit": cli.display_path(AUDIT, ROOT),
            "commit": commit,
            "final": args.final,
        }
        out = EXPERIMENT_DIR / "runs" / f"step6-{slug}-{args.split}"
        out.mkdir(parents=True, exist_ok=True)
        (out / "executions.jsonl").write_text(
            "".join(
                json.dumps(e, ensure_ascii=False) + "\n" for e in apply_threshold(baseline, best)
            ),
            encoding="utf-8",
        )
        (out / "summary.json").write_text(
            json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
        )
        a = result["abstention"]
        print(
            f"{model} : hallucination {a['hallucination']['delta']:+.3f} "
            f"[{a['hallucination']['ci_low']:+.3f} ; {a['hallucination']['ci_high']:+.3f}], "
            f"false_abstention {a['false_abstention']['delta']:+.3f} "
            f"[{a['false_abstention']['ci_low']:+.3f} ; {a['false_abstention']['ci_high']:+.3f}] "
            f"→ {a['verdict']}",
            flush=True,
        )


if __name__ == "__main__":
    main()
