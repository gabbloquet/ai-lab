import json
from pathlib import Path
from typing import Any


def load_items(path: Path, split: str, *, final: bool = False) -> list[dict[str, Any]]:
    """Les items d'un split du golden set. Le split test n'est donné que pour le run final."""
    if split == "test" and not final:
        raise PermissionError("Le split test ne sert qu'au run final (final=True, après le gel).")
    lines = path.read_text(encoding="utf-8").splitlines()
    items = [json.loads(line) for line in lines if line.strip()]
    return [item for item in items if item["split"] == split]
