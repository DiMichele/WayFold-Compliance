#!/usr/bin/env bash
set -euo pipefail
ROOT="$(git rev-parse --show-toplevel)"
cd "$ROOT"
export PATH="${LOCALAPPDATA:+$LOCALAPPDATA/cursor-agent:}$HOME/.local/bin:$PATH"
PYTHON_BIN="${PYTHON_BIN:-python3}"
ORCH="apps/wayfold-compliance/automation/wayfold_orchestrator.py"

"$PYTHON_BIN" "$ORCH" doctor
echo
"$PYTHON_BIN" "$ORCH" status
echo
echo "Percorso normale (unattended):"
echo "  ./apps/wayfold-compliance/automation/overnight.sh"
echo "oppure su Windows:"
echo "  .\\apps\\wayfold-compliance\\automation\\overnight.ps1"
