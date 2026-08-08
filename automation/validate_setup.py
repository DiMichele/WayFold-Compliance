#!/usr/bin/env python3
"""Validate WayFold Compliance automation contract (no product mutations)."""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
BASE = ROOT / "apps/wayfold-compliance"
sys.path.insert(0, str(BASE / "automation"))

from state_machine import TRANSITIONS, validate_state  # noqa: E402


def main() -> int:
    errors: list[str] = []
    config_path = BASE / ".wayfold/config.json"
    state_path = BASE / ".wayfold/state.json"
    if not config_path.exists():
        errors.append("missing config.json")
    if not state_path.exists():
        errors.append("missing state.json")
    if errors:
        print("\n".join(f"ERROR: {e}" for e in errors))
        return 1

    config = json.loads(config_path.read_text(encoding="utf-8"))
    state = json.loads(state_path.read_text(encoding="utf-8"))
    try:
        validate_state(state)
    except ValueError as exc:
        errors.append(f"invalid state: {exc}")

    for key in (
        "maxAutomaticFixAttempts",
        "maxPhase",
        "autoCommit",
        "autoPush",
        "autoTag",
        "autoMergeMain",
    ):
        if key not in config:
            errors.append(f"config missing {key}")
    if config.get("autoDeploy"):
        errors.append("autoDeploy must not be enabled")

    for name, meta in TRANSITIONS.items():
        p = ROOT / meta["prompt"]
        if not p.exists():
            errors.append(f"missing transition prompt {name}: {meta['prompt']}")

    for phase in config.get("phases", []):
        for key in ("developPrompt", "verifyPrompt", "fixPrompt"):
            p = ROOT / phase[key]
            if not p.exists():
                errors.append(f"missing {p.relative_to(ROOT).as_posix()}")

    required = [
        BASE / "automation/wayfold_orchestrator.py",
        BASE / "automation/state_machine.py",
        BASE / "automation/overnight.sh",
        BASE / "automation/preflight-overnight.sh",
        BASE / "prompts/common.md",
        BASE / "docs/PROGRESS.md",
        BASE / "docs/DECISIONS.md",
    ]
    for p in required:
        if not p.exists():
            errors.append(f"missing {p.relative_to(ROOT).as_posix()}")

    if errors:
        print("\n".join(f"ERROR: {e}" for e in errors))
        return 1
    print(
        f"WayFold automation setup valid: {len(TRANSITIONS)} transitions, "
        f"{len(config.get('phases', []))} phases, next={state.get('nextTransition')}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
