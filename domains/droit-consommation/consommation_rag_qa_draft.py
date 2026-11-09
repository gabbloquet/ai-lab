"""Fait rédiger par un LLM un brouillon de question pour chaque tâche d'un plan rag-qa.

Chaque brouillon est enregistré tel quel dans `drafts/<version>/<tâche>.json`, avec le modèle
qui l'a écrit et l'empreinte du prompt : le golden set se reconstruit ensuite sans rappeler l'API.
Une tâche déjà rédigée n'est jamais redemandée. Les contrôles se font plus tard, au build.

    uv run --env-file .env python domains/droit-consommation/consommation_rag_qa_draft.py \\
        --version pilot
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from collections.abc import Sequence
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Protocol

DOMAIN_DIR = Path(__file__).parent
GOLDEN_DIR = DOMAIN_DIR / "golden" / "rag-qa"
PROMPTS_DIR = GOLDEN_DIR / "prompts"

# Le rédacteur : un fournisseur différent du modèle évalué dans la 002 (Mistral Small).
WRITER_MODEL = "claude-sonnet-5-5"
WRITER_EFFORT = "medium"
MAX_TOKENS = 16000
MODES = ("direct", "reference", "paraphrase", "multi_article", "lost_context", "unanswerable")

ANSWERABLE_SCHEMA: dict = {
    "type": "object",
    "properties": {
        "question": {"type": "string"},
        "usable": {"type": "boolean"},
        "facts": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "accepted": {"type": "array", "items": {"type": "string"}},
                    "quote": {"type": "string"},
                    "article": {"type": "string"},
                },
                "required": ["accepted", "quote", "article"],
                "additionalProperties": False,
            },
        },
        "doubt": {"type": "string"},
    },
    "required": ["question", "usable", "facts", "doubt"],
    "additionalProperties": False,
}
UNANSWERABLE_SCHEMA: dict = {
    "type": "object",
    "properties": {
        "question": {"type": "string"},
        "why_unanswerable": {"type": "string"},
        "doubt": {"type": "string"},
    },
    "required": ["question", "why_unanswerable", "doubt"],
    "additionalProperties": False,
}

_NUM = re.compile(r"^([LRD])(\d.*)$")


@dataclass(frozen=True)
class WriterResult:
    model: str
    stop_reason: str | None
    text: str
    usage: dict


class Writer(Protocol):
    def write(self, system: str, user: str, schema: dict) -> WriterResult: ...


class AnthropicWriter:
    """Le rédacteur réel : Claude, en sortie structurée (JSON Schema).

    Pas de modèle de repli en cas de refus : un brouillon écrit par un autre modèle changerait la
    provenance du golden set. Un refus est enregistré et la tâche est remplacée par le surplus.
    """

    def __init__(self) -> None:
        import anthropic  # importé ici : les tests n'en ont pas besoin

        self._client = anthropic.Anthropic()

    def write(self, system: str, user: str, schema: dict) -> WriterResult:
        response = self._client.messages.create(
            model=WRITER_MODEL,
            max_tokens=MAX_TOKENS,
            system=system,
            messages=[{"role": "user", "content": user}],
            output_config={
                "effort": WRITER_EFFORT,
                "format": {"type": "json_schema", "schema": schema},
            },
        )
        text = next((block.text for block in response.content if block.type == "text"), "")
        return WriterResult(
            model=response.model,
            stop_reason=response.stop_reason,
            text=text,
            usage={
                "input_tokens": response.usage.input_tokens,
                "output_tokens": response.usage.output_tokens,
            },
        )


# --- Requête ------------------------------------------------------------------------------------


def load_prompts(directory: Path = PROMPTS_DIR) -> dict[str, str]:
    return {
        name: (directory / f"{name}.md").read_text(encoding="utf-8").strip()
        for name in ("system", *MODES)
    }


def citation_form(num: str) -> str:
    """« L221-18 » s'écrit « L. 221-18 » dans le texte du code."""
    match = _NUM.match(num)
    return f"{match.group(1)}. {match.group(2)}" if match else num


def _article_block(article: dict, label: str) -> str:
    return f"{label}{article['num']}\nPlan : {' > '.join(article['path'])}\n\n{article['text']}"


def render_request(
    task: dict, by_id: dict[str, dict], prompts: dict[str, str]
) -> tuple[str, str, dict]:
    """(prompt système, message utilisateur, schéma de sortie) d'une tâche."""
    mode = task["mode"]
    articles = [by_id[i] for i in task["articles"]]
    instruction = prompts[mode].replace("{citation}", citation_form(articles[0]["num"]))
    if mode == "multi_article":
        blocks = [
            _article_block(articles[0], "Article A : "),
            _article_block(articles[1], "Article B : "),
        ]
    else:
        blocks = [_article_block(articles[0], "Article ")]
    user = "\n\n---\n\n".join([instruction, *blocks])
    schema = UNANSWERABLE_SCHEMA if mode == "unanswerable" else ANSWERABLE_SCHEMA
    return prompts["system"], user, schema


def prompt_sha256(mode: str, prompts: dict[str, str]) -> str:
    return hashlib.sha256(f"{prompts['system']}\n\n{prompts[mode]}".encode()).hexdigest()


# --- Brouillons ---------------------------------------------------------------------------------


def draft_task(task: dict, by_id: dict[str, dict], writer: Writer, prompts: dict[str, str]) -> dict:
    system, user, schema = render_request(task, by_id, prompts)
    result = writer.write(system, user, schema)
    output = None
    if result.stop_reason != "refusal":
        try:
            output = json.loads(result.text)
        except json.JSONDecodeError:
            output = None
    return {
        "task": task["task"],
        "mode": task["mode"],
        "model_requested": WRITER_MODEL,
        "model": result.model,
        "effort": WRITER_EFFORT,
        "prompt_sha256": prompt_sha256(task["mode"], prompts),
        "created_at": datetime.now(UTC).isoformat(timespec="seconds"),
        "stop_reason": result.stop_reason,
        "usage": result.usage,
        "output": output,
        "raw_text": result.text,
    }


def _write_atomically(path: Path, content: str) -> None:
    tmp = path.with_suffix(".tmp")
    tmp.write_text(content, encoding="utf-8")
    tmp.replace(path)


def run_drafts(
    plan: Sequence[dict],
    by_id: dict[str, dict],
    writer: Writer,
    drafts_dir: Path,
    prompts: dict[str, str],
    *,
    workers: int = 4,
    limit: int | None = None,
    base_dirs: Sequence[Path] = (),
) -> list[str]:
    """Rédige les tâches qui n'ont pas encore de brouillon ; renvoie celles écrites, dans l'ordre
    du plan. Une tâche dont l'appel échoue n'est pas écrite : elle sera retentée au prochain run.
    Une tâche qui a déjà un brouillon dans une version de base (`base_dirs`) n'est pas récrite :
    une version qui en étend une autre réutilise ses brouillons."""
    drafts_dir.mkdir(parents=True, exist_ok=True)
    pending = [
        t
        for t in plan
        if not any((d / f"{t['task']}.json").exists() for d in (drafts_dir, *base_dirs))
    ]
    if limit is not None:
        pending = pending[:limit]

    def one(task: dict) -> str | None:
        try:
            draft = draft_task(task, by_id, writer, prompts)
        except Exception as error:  # noqa: BLE001 - une tâche ratée ne doit pas arrêter les autres
            print(f"{task['task']} : échec de l'appel ({error})", file=sys.stderr)
            return None
        path = drafts_dir / f"{task['task']}.json"
        _write_atomically(path, json.dumps(draft, ensure_ascii=False, indent=2) + "\n")
        return task["task"]

    with ThreadPoolExecutor(max_workers=workers) as pool:
        results = list(pool.map(one, pending))
    return [name for name in results if name is not None]


# --- Ligne de commande --------------------------------------------------------------------------


def _read_jsonl(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line]


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description=(__doc__ or "").splitlines()[0])
    parser.add_argument("--version", required=True, help="ex. pilot, v1")
    parser.add_argument("--articles", type=Path, default=DOMAIN_DIR / "data/v1/articles.jsonl")
    parser.add_argument("--golden-dir", type=Path, default=GOLDEN_DIR)
    parser.add_argument("--workers", type=int, default=4)
    parser.add_argument("--limit", type=int, default=None, help="au plus N nouvelles tâches")
    parser.add_argument(
        "--base-version",
        action="append",
        default=[],
        help="version étendue, dont les brouillons sont repris (répétable : v1, puis v2…)",
    )
    args = parser.parse_args(argv)

    plan = _read_jsonl(args.golden_dir / args.version / "plan.jsonl")
    by_id = {a["id"]: a for a in _read_jsonl(args.articles)}
    drafts_dir = args.golden_dir / "drafts" / args.version
    base_dirs = [args.golden_dir / "drafts" / base for base in args.base_version]
    written = run_drafts(
        plan,
        by_id,
        AnthropicWriter(),
        drafts_dir,
        load_prompts(args.golden_dir / "prompts"),
        workers=args.workers,
        limit=args.limit,
        base_dirs=base_dirs,
    )
    missing = sum(
        not any((d / f"{t['task']}.json").exists() for d in (drafts_dir, *base_dirs)) for t in plan
    )
    print(f"{len(written)} brouillons écrits dans {drafts_dir} ; {missing} tâches sans brouillon")


if __name__ == "__main__":
    main()
