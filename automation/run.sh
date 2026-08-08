#!/usr/bin/env bash
# Compatibility wrapper — prefer overnight.sh
set -euo pipefail
ROOT="$(git rev-parse --show-toplevel)"
cd "$ROOT"
exec ./apps/wayfold-compliance/automation/overnight.sh
