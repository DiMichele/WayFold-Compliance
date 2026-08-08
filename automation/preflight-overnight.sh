#!/usr/bin/env bash
set -euo pipefail
ROOT="$(git rev-parse --show-toplevel)"
cd "$ROOT"
export PATH="${LOCALAPPDATA:+$LOCALAPPDATA/cursor-agent:}$HOME/.local/bin:$PATH"
exec python3 apps/wayfold-compliance/automation/wayfold_orchestrator.py preflight
