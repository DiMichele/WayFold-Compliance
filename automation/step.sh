#!/usr/bin/env bash
set -euo pipefail
ROOT="$(git rev-parse --show-toplevel)"
cd "$ROOT"
exec python3 apps/wayfold-compliance/automation/wayfold_orchestrator.py step
