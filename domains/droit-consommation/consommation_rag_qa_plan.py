"""Tire, de façon seedée, les articles qui serviront à rédiger le golden set rag-qa.

C'est le script qui choisit les articles, jamais le LLM rédacteur : laissé libre, il choisirait
les articles les plus connus. Les règles sont décrites dans golden/rag-qa/README.md (« Tirage »).

    uv run python domains/droit-consommation/consommation_rag_qa_plan.py \\
        --seed 7 --version pilot --quotas pilot
    uv run python domains/droit-consommation/consommation_rag_qa_plan.py --seed 42 --version v1 \\
        --exclude-plan domains/droit-consommation/golden/rag-qa/pilot/plan.jsonl
"""

from __future__ import annotations

import argparse
import json
import math
import random
import re
import sys
from collections import defaultdict
from collections.abc import Callable, Iterable
from pathlib import Path

DOMAIN_DIR = Path(__file__).parent

# Items gardés par mode : (dev, test). README du golden set, « Composition ».
V1_QUOTAS: dict[str, tuple[int, int]] = {
    "direct": (10, 30),
    "reference": (8, 22),
    "paraphrase": (10, 30),
    "multi_article": (8, 22),
    "lost_context": (7, 23),
    "unanswerable": (7, 23),
}
# v2 : la v1 publiée, plus des questions sans réponse dans le `dev` (expérience 006, consigne
# d'abstention) ; le `test` est celui de la v1. 31 tâches `dev` retenues en mode `unanswerable` :
# 30 items sans réponse, plus rq-133, transformé en item avec réponse à la relecture de la v1.
V2_QUOTAS: dict[str, tuple[int, int]] = {**V1_QUOTAS, "unanswerable": (31, 23)}
# Pilote : 20 brouillons jetés après la mise au point du prompt, sans surplus.
PILOT_QUOTAS: dict[str, tuple[int, int]] = {
    "direct": (4, 0),
    "reference": (3, 0),
    "paraphrase": (4, 0),
    "multi_article": (3, 0),
    "lost_context": (3, 0),
    "unanswerable": (3, 0),
}
# Réserve : deux fois le besoin. Au second pilote, 4 brouillons sur 20 ont été rejetés.
SURPLUS = 2.0

# Les modes au vivier le plus étroit tirent en premier : un article ne sert qu'une fois.
DRAW_ORDER = ("lost_context", "multi_article", "reference", "direct", "paraphrase", "unanswerable")

MIN_CHARS, MAX_CHARS = 200, 4000
LOST_CONTEXT = re.compile(
    r"\bprésente? (chapitre|titre|livre|section|sous-section)\b"
    r"|\b(ce|cette|ces) (délai|contrat|offre|professionnel|prêt|crédit)s?\b",
    re.IGNORECASE,
)
CITABLE_NUM = re.compile(r"^[LRD]\d")

Candidate = tuple[str, ...]  # les `id` d'articles d'une tâche : un seul, ou une paire A → B


# --- Viviers ------------------------------------------------------------------------------------


def eligible(article: dict) -> bool:
    text: str = article["text"]
    lines = text.split("\n")
    table_share = sum(" | " in line for line in lines) / len(lines)
    return (
        not article["num"].startswith("Annexe")
        and MIN_CHARS <= len(text) <= MAX_CHARS
        and article["valid_to"] is None
        and table_share < 0.5
    )


def lost_context_candidate(article: dict) -> bool:
    return bool(LOST_CONTEXT.search(article["text"]))


def reference_candidate(article: dict) -> bool:
    return bool(CITABLE_NUM.match(article["num"]))


def livre(article: dict) -> str:
    """Le livre du code, premier niveau sous la partie : « Livre II : … » devient « Livre II »."""
    level = article["path"][1] if len(article["path"]) > 1 else article["path"][0]
    return level.split(" :")[0].strip()


def _pools(articles: list[dict]) -> dict[str, list[Candidate]]:
    pool = [a for a in articles if eligible(a)]
    ids = {a["id"] for a in pool}

    def singles(keep: Callable[[dict], bool]) -> list[Candidate]:
        return [(a["id"],) for a in pool if keep(a)]

    pairs = [(a["id"], b) for a in pool for b in a["cites"] if b in ids and b != a["id"]]
    everything = singles(lambda a: True)
    return {
        "direct": everything,
        "reference": singles(reference_candidate),
        "paraphrase": everything,
        "multi_article": pairs,
        "lost_context": singles(lost_context_candidate),
        "unanswerable": everything,
    }


# --- Répartition --------------------------------------------------------------------------------


def allocate(available: dict[str, int], n: int) -> dict[str, int]:
    """Répartit n tirages entre les livres au prorata de leur vivier (plus forts restes),
    sans jamais demander plus que ce qu'un livre contient."""
    targets = {key: 0 for key in available}
    remaining = n
    open_keys = {key for key, count in available.items() if count > 0}
    while remaining > 0 and open_keys:
        total = sum(available[key] - targets[key] for key in open_keys)
        shares = {key: remaining * (available[key] - targets[key]) / total for key in open_keys}
        floors = {
            key: min(math.floor(share), available[key] - targets[key])
            for key, share in shares.items()
        }
        leftover = remaining - sum(floors.values())
        by_remainder = sorted(open_keys, key=lambda key: (-(shares[key] - floors[key]), key))
        for key in by_remainder:
            if leftover == 0:
                break
            if floors[key] < available[key] - targets[key]:
                floors[key] += 1
                leftover -= 1
        for key, extra in floors.items():
            targets[key] += extra
            remaining -= extra
        open_keys = {key for key in open_keys if targets[key] < available[key]}
    return targets


# --- Tirage -------------------------------------------------------------------------------------


def _draw(
    candidates: list[Candidate],
    n: int,
    used: set[str],
    livre_of: dict[str, str],
    rng: random.Random,
) -> list[Candidate]:
    free = [c for c in candidates if not used & set(c)]
    rng.shuffle(free)
    by_livre: dict[str, list[Candidate]] = defaultdict(list)
    for candidate in free:
        by_livre[livre_of[candidate[0]]].append(candidate)
    targets = allocate({key: len(group) for key, group in sorted(by_livre.items())}, n)

    drawn: list[Candidate] = []

    def take(group: Iterable[Candidate], limit: int) -> None:
        for candidate in group:
            if limit == 0:
                return
            if used & set(candidate):
                continue
            drawn.append(candidate)
            used.update(candidate)
            limit -= 1

    for key in sorted(by_livre):
        take(by_livre[key], targets[key])
    # Une paire peut entrer en conflit avec une paire déjà tirée : on complète dans l'ordre mélangé.
    take(free, n - len(drawn))
    return drawn


def make_plan(
    articles: list[dict],
    *,
    seed: int,
    quotas: dict[str, tuple[int, int]],
    surplus: float = SURPLUS,
    exclude: set[str] | frozenset[str] = frozenset(),
) -> list[dict]:
    pools = _pools(articles)
    livre_of = {a["id"]: livre(a) for a in articles}
    used = set(exclude)
    plan: list[dict] = []
    drawn_by_mode: dict[str, list[dict]] = {}
    for mode in DRAW_ORDER:
        dev, test = quotas[mode]
        n_dev, n_test = math.ceil(surplus * dev), math.ceil(surplus * test)
        rng = random.Random(f"{seed}-{mode}")
        drawn = _draw(pools[mode], n_dev + n_test, used, livre_of, rng)
        if len(drawn) < n_dev + n_test:
            raise ValueError(
                f"{mode} : {len(drawn)} candidats disponibles pour {n_dev + n_test} tirages"
            )
        rng.shuffle(drawn)
        tasks = []
        for split, chunk in (("dev", drawn[:n_dev]), ("test", drawn[n_dev:])):
            for rank, candidate in enumerate(chunk, start=1):
                tasks.append(
                    {
                        "task": f"{mode}-{split}-{rank:03d}",
                        "mode": mode,
                        "split": split,
                        "rank": rank,
                        "articles": list(candidate),
                        "livre": livre_of[candidate[0]],
                    }
                )
        drawn_by_mode[mode] = tasks
    for mode in quotas:  # ordre de sortie : celui des quotas, lisible
        plan.extend(drawn_by_mode[mode])
    return plan


def extend_plan(
    articles: list[dict],
    plan: list[dict],
    *,
    mode: str,
    split: str,
    n: int,
    seed: int,
    exclude: set[str] | frozenset[str] = frozenset(),
) -> list[dict]:
    """Ajoute n tâches à un mode et un split d'un plan existant, sans toucher aux tâches déjà
    tirées : c'est la seule modification permise d'un plan, quand la réserve ne suffit pas."""
    used = set(exclude) | {a for task in plan for a in task["articles"]}
    group = [t for t in plan if t["mode"] == mode and t["split"] == split]
    last = max((t["rank"] for t in group), default=0)
    rng = random.Random(f"{seed}-{mode}-{split}-extension-{last}")
    livre_of = {a["id"]: livre(a) for a in articles}
    drawn = _draw(_pools(articles)[mode], n, used, livre_of, rng)
    if len(drawn) < n:
        raise ValueError(f"{mode} : {len(drawn)} candidats disponibles pour {n} tirages")
    rng.shuffle(drawn)
    added = [
        {
            "task": f"{mode}-{split}-{rank:03d}",
            "mode": mode,
            "split": split,
            "rank": rank,
            "articles": list(candidate),
            "livre": livre_of[candidate[0]],
            "extension": True,
        }
        for rank, candidate in enumerate(drawn, start=last + 1)
    ]
    return [*plan, *added]


# --- Ligne de commande --------------------------------------------------------------------------


def _read_jsonl(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line]


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description=(__doc__ or "").splitlines()[0])
    parser.add_argument("--articles", type=Path, default=DOMAIN_DIR / "data/v1/articles.jsonl")
    parser.add_argument("--seed", type=int, required=True)
    parser.add_argument("--version", required=True, help="ex. pilot, v1")
    parser.add_argument("--quotas", choices=["v1", "pilot"], default="v1")
    parser.add_argument("--golden-dir", type=Path, default=DOMAIN_DIR / "golden/rag-qa")
    parser.add_argument("--exclude-plan", type=Path, action="append", default=[])
    parser.add_argument("--extend", help="mode:split:n, ajoute n tâches à un plan existant")
    args = parser.parse_args(argv)

    out = args.golden_dir / args.version / "plan.jsonl"
    exclude = {
        a for path in args.exclude_plan for task in _read_jsonl(path) for a in task["articles"]
    }
    if args.extend:
        mode, split, n = args.extend.split(":")
        extended = extend_plan(
            _read_jsonl(args.articles),
            _read_jsonl(out),
            mode=mode,
            split=split,
            n=int(n),
            seed=args.seed,
            exclude=exclude,
        )
        out.write_text("".join(json.dumps(t, ensure_ascii=False) + "\n" for t in extended), "utf-8")
        print(f"{n} tâches {mode}/{split} ajoutées à {out}")
        return
    if out.exists():
        sys.exit(f"{out} existe déjà : un plan ne se retire pas.")
    quotas, surplus = (PILOT_QUOTAS, 1.0) if args.quotas == "pilot" else (V1_QUOTAS, SURPLUS)
    plan = make_plan(
        _read_jsonl(args.articles), seed=args.seed, quotas=quotas, surplus=surplus, exclude=exclude
    )
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text("".join(json.dumps(t, ensure_ascii=False) + "\n" for t in plan), "utf-8")
    print(f"{len(plan)} tâches écrites dans {out}")


if __name__ == "__main__":
    main()
