"""Writable runtime paths for WayFold Compliance engine stores."""

from __future__ import annotations

import os
from pathlib import Path

# Repo-local default (dev/tests). Production sets WAYFOLD_DATA_DIR to a writable volume.
_DEFAULT_DATA = Path(__file__).resolve().parent / "data"


def data_root() -> Path:
    raw = os.environ.get("WAYFOLD_DATA_DIR", "").strip()
    root = Path(raw) if raw else _DEFAULT_DATA
    root.mkdir(parents=True, exist_ok=True)
    return root


def seed_demo_enabled() -> bool:
    """Local/tests default ON; production sets WAYFOLD_SEED_DEMO=0."""
    raw = os.environ.get("WAYFOLD_SEED_DEMO")
    if raw is None or not str(raw).strip():
        return True
    return str(raw).strip().lower() in {"1", "true", "yes", "on"}


def portfolio_registry_path(default_fixtures: Path) -> Path:
    """Dev/tests: fixture registry. Production (SEED_DEMO=0): empty writable registry."""
    override = os.environ.get("WAYFOLD_PORTFOLIO_REGISTRY", "").strip()
    if override:
        return Path(override)
    if seed_demo_enabled():
        return default_fixtures
    path = data_root() / "portfolio_registry.json"
    if not path.is_file():
        path.write_text('{"programs": []}\n', encoding="utf-8")
    return path
