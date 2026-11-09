"""Les chemins du run consolidé, relatifs à la racine du dépôt."""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[5]
EXPERIMENT_DIR = ROOT / "experiments" / "002-leviers-rag"
GOLDEN = ROOT / "domains/droit-consommation/golden/rag-qa/v4/items.jsonl"
AUDIT = ROOT / "domains/droit-consommation/golden/rag-qa/audit/v1-unanswerable.jsonl"
ARTICLES = ROOT / "domains/droit-consommation/data/v1/articles.jsonl"
# Le cache partagé des étapes 2 à 5 : embeddings, reformulations, notes de reclassement.
CACHE_DIR = ROOT / ".cache" / "ailab_rag"
