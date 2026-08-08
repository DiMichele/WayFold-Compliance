#!/usr/bin/env bash
set -euo pipefail

ROOT="$(git rev-parse --show-toplevel)"
cd "$ROOT"

PYTHON_BIN="${PYTHON_BIN:-python3}"
ORCH="apps/wayfold-compliance/automation/wayfold_orchestrator.py"

if ! command -v git >/dev/null 2>&1; then
  echo "git non trovato" >&2
  exit 2
fi

if ! command -v cursor-agent >/dev/null 2>&1; then
  cat >&2 <<'EOF'
Cursor Agent CLI non trovato.
Installa in WSL/Linux con:
  curl https://cursor.com/install -fsS | bash
poi verifica:
  cursor-agent --version
EOF
  exit 2
fi

if [[ -n "$(git status --porcelain)" ]]; then
  cat >&2 <<'EOF'
Working tree non pulito.
Prima di automatizzare, termina/controlla la Phase 1 corrente e fai commit o stash delle modifiche.
EOF
  git status --short >&2
  exit 2
fi

BRANCH="$(git branch --show-current)"
if [[ "$BRANCH" == "main" || "$BRANCH" == "master" ]]; then
  TARGET="wayfold/compliance-pipeline"
  echo "Creo branch dedicato: $TARGET"
  git switch -c "$TARGET"
fi

"$PYTHON_BIN" "$ORCH" doctor

echo
echo "Bootstrap OK. Stato corrente:"
"$PYTHON_BIN" "$ORCH" status

echo
echo "Per eseguire un solo passaggio:"
echo "  $PYTHON_BIN $ORCH step"
echo "Per eseguire tutta la pipeline fino a COMPLETE/BLOCKED:"
echo "  $PYTHON_BIN $ORCH run"
