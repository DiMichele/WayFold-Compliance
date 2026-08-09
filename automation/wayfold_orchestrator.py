#!/usr/bin/env python3
"""WayFold Compliance overnight orchestrator (transition-based).

One NEW Cursor Agent session per transition:
  VERIFY Phase N (+ fix/reverify up to max attempts) → CLOSE N → DEVELOP N+1 → STOP

Independent verification: Phase N is never verified in the same agent run that developed it.
"""
from __future__ import annotations

import argparse
import json
import os
import shlex
import shutil
import signal
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

_AUTO_DIR = Path(__file__).resolve().parent
if str(_AUTO_DIR) not in sys.path:
    sys.path.insert(0, str(_AUTO_DIR))

from state_machine import (
    TRANSITIONS,
    apply_blocked,
    apply_complete,
    apply_final_regression_fail,
    apply_final_regression_pass,
    apply_fix_done,
    apply_interrupted,
    apply_invalid_result,
    apply_merge_conflict,
    apply_pass_transition,
    apply_push_failure,
    apply_verification_fail,
    default_state,
    resume_status,
    validate_state,
    validate_transition_result,
)

APP_REL = Path("apps/wayfold-compliance")
DOT_REL = APP_REL / ".wayfold"
CONFIG_REL = DOT_REL / "config.json"
STATE_REL = DOT_REL / "state.json"
RESULTS_REL = DOT_REL / "results"
LOGS_REL = DOT_REL / "logs"
LOCK_REL = DOT_REL / "orchestrator.lock"
PROMPTS_REL = APP_REL / "prompts"
REPORT_REL = APP_REL / "docs" / "AUTOMATION-RUN-REPORT.md"

STOP_STATUSES = {"COMPLETE", "HUMAN_REVIEW_REQUIRED", "BLOCKED"}


class OrchestratorError(RuntimeError):
    pass


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def stamp() -> str:
    return datetime.now().strftime("%Y%m%d-%H%M%S")


def _safe_print(text: str) -> None:
    """Print without crashing on Windows cp1252 consoles."""
    try:
        print(text)
    except UnicodeEncodeError:
        encoding = getattr(sys.stdout, "encoding", None) or "utf-8"
        sys.stdout.write(text.encode(encoding, errors="replace").decode(encoding, errors="replace"))
        sys.stdout.write("\n")



def run_cmd(
    args: list[str],
    cwd: Path,
    *,
    check: bool = False,
    capture: bool = True,
    timeout: int | None = None,
    env: dict[str, str] | None = None,
) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        args,
        cwd=str(cwd),
        text=True,
        capture_output=capture,
        check=check,
        timeout=timeout,
        env=env,
    )


def find_repo_root(start: Path | None = None) -> Path:
    start = (start or Path.cwd()).resolve()
    cp = run_cmd(["git", "rev-parse", "--show-toplevel"], start)
    if cp.returncode != 0:
        raise OrchestratorError("Run from inside the WayFold git repository.")
    return Path(cp.stdout.strip()).resolve()


def read_json(path: Path) -> dict[str, Any]:
    try:
        # utf-8-sig tolerates BOM occasionally written by Windows/agents
        return json.loads(path.read_text(encoding="utf-8-sig"))
    except FileNotFoundError as exc:
        raise OrchestratorError(f"Missing required file: {path}") from exc
    except json.JSONDecodeError as exc:
        raise OrchestratorError(f"Invalid JSON in {path}: {exc}") from exc


def atomic_write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    data = json.dumps(payload, indent=2, ensure_ascii=False) + "\n"
    with tmp.open("w", encoding="utf-8", newline="\n") as fh:
        fh.write(data)
        fh.flush()
        os.fsync(fh.fileno())
    os.replace(tmp, path)


def atomic_write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    with tmp.open("w", encoding="utf-8", newline="\n") as fh:
        fh.write(text)
        fh.flush()
        os.fsync(fh.fileno())
    os.replace(tmp, path)


class Context:
    def __init__(self, repo: Path):
        self.repo = repo
        self.config_path = repo / CONFIG_REL
        self.state_path = repo / STATE_REL
        self.lock_path = repo / LOCK_REL
        self.config = read_json(self.config_path)
        self.state = read_json(self.state_path)
        self._migrate_state()
        validate_state(self.state)
        self._validate_config()

    def _migrate_state(self) -> None:
        """Upgrade schemaVersion 1 → 2 if needed."""
        if int(self.state.get("schemaVersion", 1)) >= 2 and "nextTransition" in self.state:
            return
        migrated = default_state()
        action = self.state.get("action")
        phase = int(self.state.get("currentPhase", 1))
        last = int(self.state.get("lastCompletedPhase", 0))
        migrated["lastClosedPhase"] = last
        migrated["verificationAttempts"] = int(self.state.get("verificationAttempts", 0))
        migrated["history"] = list(self.state.get("history") or [])
        if action == "VERIFY":
            migrated["implementedPhase"] = phase
            migrated["nextTransition"] = f"{phase}_TO_{phase + 1}" if phase < 6 else "CLOSE_6"
            if phase == 6:
                migrated["nextTransition"] = "CLOSE_6"
        elif action == "DEVELOP":
            migrated["implementedPhase"] = phase
            prev = max(0, phase - 1)
            migrated["lastClosedPhase"] = prev
            migrated["nextTransition"] = f"{prev}_TO_{phase}" if prev >= 1 else "1_TO_2"
            migrated["status"] = "AWAITING_VERIFICATION"
        elif self.state.get("status") == "COMPLETE":
            migrated = apply_complete(migrated)
        # Normalize unknown transitions from migration
        if migrated.get("nextTransition") == "6_TO_7":
            migrated["nextTransition"] = "CLOSE_6"
        if migrated["nextTransition"] not in TRANSITIONS and migrated["status"] != "COMPLETE":
            migrated["nextTransition"] = "1_TO_2"
            migrated["lastClosedPhase"] = 0
            migrated["implementedPhase"] = 1
            migrated["status"] = "READY"
        self.state = migrated
        atomic_write_json(self.state_path, self.state)

    def _validate_config(self) -> None:
        for key in (
            "maxAutomaticFixAttempts",
            "maxPhase",
            "autoCommit",
            "autoPush",
            "autoTag",
            "autoMergeMain",
            "autoDeploy",
        ):
            if key not in self.config:
                raise OrchestratorError(f"config.json missing {key}")
        if self.config.get("autoDeployProductionDns"):
            raise OrchestratorError("autoDeployProductionDns is forbidden (use deploy scripts)")

    def save_state(self) -> None:
        self.state["updatedAt"] = now_iso()
        # Mirror config toggles into state for machine-readable audit
        for key in (
            "autoCommit",
            "autoPush",
            "autoTag",
            "autoMergeMain",
            "autoDeploy",
            "maxAutomaticFixAttempts",
            "maxPhase",
        ):
            if key in self.config:
                self.state[key] = self.config[key]
        validate_state(self.state)
        atomic_write_json(self.state_path, self.state)


# --- Lock -----------------------------------------------------------------


def _pid_alive(pid: int) -> bool:
    if pid <= 0:
        return False
    if os.name == "nt":
        cp = run_cmd(["tasklist", "/FI", f"PID eq {pid}"], Path.cwd())
        return str(pid) in (cp.stdout or "")
    try:
        os.kill(pid, 0)
    except OSError:
        return False
    return True


def acquire_lock(ctx: Context) -> None:
    ctx.lock_path.parent.mkdir(parents=True, exist_ok=True)
    if ctx.lock_path.exists():
        try:
            meta = json.loads(ctx.lock_path.read_text(encoding="utf-8"))
            pid = int(meta.get("pid", -1))
            stale_sec = int(ctx.config.get("lockStaleSeconds", 21600))
            created = meta.get("createdAt")
            age_ok = True
            if created:
                try:
                    created_dt = datetime.fromisoformat(created.replace("Z", "+00:00"))
                    age_ok = (datetime.now(timezone.utc) - created_dt).total_seconds() < stale_sec
                except ValueError:
                    age_ok = True
            if _pid_alive(pid) and age_ok:
                raise OrchestratorError(
                    f"Another orchestrator is active (pid={pid}). Lock: {ctx.lock_path}"
                )
            print(f"Removing stale lock (pid={pid})")
            ctx.lock_path.unlink(missing_ok=True)
        except json.JSONDecodeError:
            ctx.lock_path.unlink(missing_ok=True)
    payload = {"pid": os.getpid(), "createdAt": now_iso(), "host": os.environ.get("COMPUTERNAME", "")}
    tmp = ctx.lock_path.with_suffix(".lock.tmp")
    tmp.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    os.replace(tmp, ctx.lock_path)


def release_lock(ctx: Context) -> None:
    try:
        if ctx.lock_path.exists():
            meta = json.loads(ctx.lock_path.read_text(encoding="utf-8"))
            if int(meta.get("pid", -1)) == os.getpid():
                ctx.lock_path.unlink(missing_ok=True)
    except Exception:
        pass


# --- Git helpers ----------------------------------------------------------


def git_branch(repo: Path) -> str:
    return run_cmd(["git", "branch", "--show-current"], repo).stdout.strip()


def git_head(repo: Path) -> str:
    return run_cmd(["git", "rev-parse", "HEAD"], repo).stdout.strip()


def git_dirty(repo: Path) -> list[str]:
    cp = run_cmd(["git", "status", "--porcelain"], repo)
    return [line for line in cp.stdout.splitlines() if line.strip()]


def ensure_automation_branch(ctx: Context) -> None:
    desired = str(ctx.config.get("automationBranch", "automation/wayfold-compliance"))
    current = git_branch(ctx.repo)
    protected = set(ctx.config.get("protectedBranches", ["main", "master"]))
    if current == desired:
        return
    if current in protected:
        # Create/switch dedicated branch from current HEAD
        exists = run_cmd(["git", "show-ref", "--verify", "--quiet", f"refs/heads/{desired}"], ctx.repo)
        if exists.returncode == 0:
            cp = run_cmd(["git", "switch", desired], ctx.repo)
        else:
            cp = run_cmd(["git", "switch", "-c", desired], ctx.repo)
        if cp.returncode != 0:
            raise OrchestratorError(f"Unable to switch to {desired}: {cp.stderr}")
        print(f"Switched to branch {desired}")
    elif current not in protected and ctx.config.get("reuseExistingFeatureBranch", True):
        print(f"Reusing current feature branch: {current}")
        ctx.state["branch"] = current
        ctx.save_state()
    else:
        raise OrchestratorError(f"Unsafe branch '{current}'. Use {desired}.")


def classify_dirty(paths: list[str]) -> dict[str, list[str]]:
    compliance = []
    automation = []
    other = []
    shared_ok = []
    for line in paths:
        path = line[3:].strip().replace("\\", "/") if len(line) > 3 else line.replace("\\", "/")
        if path.startswith("apps/wayfold-compliance/") or path == "apps/wayfold-compliance":
            if any(x in path for x in ("/automation/", "/.wayfold/", "/prompts/")):
                automation.append(line)
            else:
                compliance.append(line)
        elif path.startswith(".github/workflows/wayfold-compliance"):
            automation.append(line)
        elif path in {".gitignore"} or path.startswith("wayfold-compliance-automation-overlay"):
            shared_ok.append(line)
        else:
            other.append(line)
    return {
        "compliance": compliance,
        "automation": automation,
        "shared_ok": shared_ok,
        "other": other,
    }


def ensure_no_nested_git(ctx: Context) -> None:
    """apps/wayfold-compliance must be a normal directory, not a nested repo/gitlink."""
    nested = ctx.repo / APP_REL / ".git"
    if not nested.exists():
        return
    print(f"Removing nested git metadata at {nested} (monorepo tracking required)")
    if nested.is_dir():
        shutil.rmtree(nested)
    else:
        nested.unlink()


def commit_changes(ctx: Context, message: str) -> bool:
    if not ctx.config.get("autoCommit", True):
        return False
    ensure_no_nested_git(ctx)
    dirty = git_dirty(ctx.repo)
    if not dirty:
        return False
    # Avoid committing unrelated apps / secrets
    for line in dirty:
        path = line[3:].strip()
        if path.endswith(".env") or "credentials" in path.lower():
            raise OrchestratorError(f"Refusing to commit secret-like path: {path}")
    # Drop accidental gitlink/submodule mode before re-adding real files
    ls = run_cmd(["git", "ls-files", "-s", "--", str(APP_REL)], ctx.repo)
    if ls.stdout.strip().startswith("160000"):
        run_cmd(["git", "rm", "--cached", "-f", "--", str(APP_REL)], ctx.repo)
    run_cmd(
        ["git", "add", "-A", "--", "apps/wayfold-compliance", ".github/workflows", ".gitignore"],
        ctx.repo,
    )
    staged = run_cmd(["git", "diff", "--cached", "--name-only"], ctx.repo).stdout.strip()
    if not staged:
        return False
    cp = run_cmd(["git", "commit", "-m", message], ctx.repo)
    if cp.returncode != 0:
        raise OrchestratorError(f"git commit failed:\n{cp.stdout}\n{cp.stderr}")
    print(cp.stdout.strip() or f"Committed: {message}")
    return True


def push_branch(ctx: Context) -> None:
    if not ctx.config.get("autoPush", True):
        return
    branch = git_branch(ctx.repo)
    cp = run_cmd(["git", "push", "-u", "origin", "HEAD"], ctx.repo)
    if cp.returncode != 0:
        raise OrchestratorError(f"git push failed:\n{cp.stdout}\n{cp.stderr}")
    print(f"Pushed branch {branch}")


def tag_phase(ctx: Context, phase: int) -> None:
    if not ctx.config.get("autoTag", True):
        return
    tag = f"phase-{phase}-complete"
    exists = run_cmd(["git", "tag", "--list", tag], ctx.repo).stdout.strip()
    if exists:
        print(f"Tag {tag} already exists")
        return
    cp = run_cmd(
        ["git", "tag", "-a", tag, "-m", f"WayFold Compliance Phase {phase} independently verified"],
        ctx.repo,
    )
    if cp.returncode != 0:
        raise OrchestratorError(f"tag failed: {cp.stderr}")
    print(f"Created tag {tag}")
    if ctx.config.get("autoPush", True):
        cp = run_cmd(["git", "push", "origin", tag], ctx.repo)
        if cp.returncode != 0:
            raise OrchestratorError(f"tag push failed: {cp.stderr}")


# --- Cursor agent ---------------------------------------------------------


def _windows_agent_node_argv(local_dir: Path) -> list[str] | None:
    """Resolve node.exe + index.js so stdin/UTF-8 work (avoid cmd.ps1 wrappers)."""
    versions = local_dir / "versions"
    if not versions.is_dir():
        return None
    dirs = [p for p in versions.iterdir() if p.is_dir()]
    if not dirs:
        return None

    def sort_key(p: Path) -> tuple:
        # Names like 2026.08.04-aaa8809 or 2026.08.04-12-00-00-aaa8809
        return p.name

    for version_dir in sorted(dirs, key=sort_key, reverse=True):
        node = version_dir / "node.exe"
        index = version_dir / "index.js"
        if node.exists() and index.exists():
            return [str(node), str(index)]
    return None


def resolve_cursor_command(config: dict[str, Any]) -> list[str]:
    """Return a subprocess-safe argv for the Cursor Agent CLI."""
    local_dir = Path(os.environ.get("LOCALAPPDATA", "")) / "cursor-agent"
    # Prefer direct node entry on Windows for reliable stdin piping.
    if os.name == "nt":
        node_argv = _windows_agent_node_argv(local_dir)
        if node_argv:
            return node_argv

    candidates: list[list[str]] = []
    raw = str(config.get("cursorCommand", "agent")).strip()
    if raw and raw not in {"agent", "cursor-agent"}:
        candidates.append(shlex.split(raw, posix=(os.name != "nt")))
    for name in ("agent", "cursor-agent"):
        path = shutil.which(name)
        if path:
            if os.name == "nt" and path.lower().endswith((".cmd", ".bat")):
                candidates.append(["cmd", "/c", path])
            else:
                candidates.append([path])
    for exe in ("agent.exe", "cursor-agent.exe"):
        local = local_dir / exe
        if local.exists():
            candidates.append([str(local)])
    for parts in candidates:
        if not parts:
            continue
        if parts[0] in {"cmd", "powershell"} or shutil.which(parts[0]) or Path(parts[0]).exists():
            return parts
    raise OrchestratorError(
        "Cursor Agent CLI not found. Install with: "
        "irm 'https://cursor.com/install?win32=true' | iex   "
        "or: curl https://cursor.com/install -fsS | bash"
    )


def cursor_auth_ok(cmd: list[str]) -> tuple[bool, str]:
    if os.environ.get("CURSOR_API_KEY"):
        return True, "CURSOR_API_KEY set"
    try:
        cp = run_cmd(cmd + ["status"], Path.cwd(), timeout=60)
        out = ((cp.stdout or "") + (cp.stderr or "")).strip()
        low = out.lower()
        if "not logged in" in low or "logged out" in low:
            return False, out or "Not logged in"
        if cp.returncode == 0:
            return True, out or "authenticated"
        return False, out or f"exit {cp.returncode}"
    except Exception as exc:
        return False, str(exc)


def render_transition_prompt(ctx: Context, transition: str) -> tuple[str, Path]:
    meta = TRANSITIONS[transition]
    prompt_path = ctx.repo / meta["prompt"]
    if not prompt_path.exists():
        raise OrchestratorError(f"Missing prompt: {prompt_path}")
    common_path = ctx.repo / ctx.config.get("commonPrompt", (PROMPTS_REL / "common.md").as_posix())
    common = common_path.read_text(encoding="utf-8") if common_path.exists() else ""
    body = prompt_path.read_text(encoding="utf-8")
    result_path = ctx.repo / RESULTS_REL / f"transition-{transition.lower().replace('_', '-')}-{stamp()}.json"
    verify_phase = meta["verify"]
    develop_phase = meta["develop"]
    report_path = ctx.repo / APP_REL / "docs" / f"PHASE{verify_phase}-VERIFICATION.md"
    replacements = {
        "{{TRANSITION}}": transition,
        "{{VERIFY_PHASE}}": str(verify_phase),
        "{{DEVELOP_PHASE}}": str(develop_phase) if develop_phase is not None else "NONE",
        "{{RESULT_PATH}}": result_path.relative_to(ctx.repo).as_posix(),
        "{{STATE_PATH}}": STATE_REL.as_posix(),
        "{{VERIFY_REPORT_PATH}}": report_path.relative_to(ctx.repo).as_posix(),
        "{{PROGRESS_PATH}}": f"{APP_REL.as_posix()}/docs/PROGRESS.md",
        "{{DECISIONS_PATH}}": f"{APP_REL.as_posix()}/docs/DECISIONS.md",
        "{{AUTOMATION_REPORT_PATH}}": REPORT_REL.as_posix(),
        "{{MAX_FIX_ATTEMPTS}}": str(ctx.config.get("maxAutomaticFixAttempts", 3)),
    }
    text = common + "\n\n---\n\n" + body
    for old, new in replacements.items():
        text = text.replace(old, new)

    develop_block = ""
    if develop_phase is not None:
        develop_block = f"""
PART B — DEVELOP PHASE {develop_phase}
- Implement ONLY Phase {develop_phase} scope from the master plan.
- Run tests/build relevant to the change.
- Update PROGRESS.md: PHASE {develop_phase} IMPLEMENTATION FINISHED — AWAITING INDEPENDENT VERIFICATION
- Do NOT claim PHASE {develop_phase} COMPLETE.
- Do NOT create git tags.
- developmentStatus must be IMPLEMENTED (or BLOCKED).
"""
    else:
        develop_block = """
PART B — NONE
This is close-phase-06. Do not develop a Phase 7.
developmentStatus must be SKIPPED and developedPhase null after PASS.
"""

    contract = f"""

---
# RUNTIME CONTRACT — OBBLIGATORIO

Transition: {transition}
Verify phase: {verify_phase}
Develop phase: {develop_phase}
Max automatic fix attempts inside PART A: {ctx.config.get('maxAutomaticFixAttempts', 3)}
Machine result file (write exactly here): `{result_path.relative_to(ctx.repo).as_posix()}`
Verification report: `{report_path.relative_to(ctx.repo).as_posix()}`
Automation report: `{REPORT_REL.as_posix()}`

PART A — VERIFY PHASE {verify_phase}
- Adversarial independent verification.
- If FAIL: FIX, TEST, REVERIFY (full criteria), up to {{{{MAX_FIX_ATTEMPTS}}}} attempts.
- If still FAIL or BLOCKED: do NOT develop next phase.
- If PASS: CLOSE phase, update docs, write verification report. Orchestrator creates tag/push.

{develop_block}

STOP THIS AGENT RUN after writing the JSON result. Do not start the next transition.

JSON schema (exact keys):

```json
{{
  "transition": "{transition}",
  "verifiedPhase": {verify_phase},
  "verificationStatus": "PASS",
  "developedPhase": {json.dumps(develop_phase)},
  "developmentStatus": "IMPLEMENTED",
  "fixAttemptsUsed": 0,
  "blockingIssues": [],
  "nonBlockingIssues": [],
  "summary": "..."
}}
```

On verification failure:

```json
{{
  "transition": "{transition}",
  "verifiedPhase": {verify_phase},
  "verificationStatus": "FAIL",
  "developedPhase": null,
  "developmentStatus": "NOT_STARTED",
  "fixAttemptsUsed": 3,
  "blockingIssues": [{{"severity": "BLOCKING", "description": "..."}}],
  "summary": "..."
}}
```

Do not modify `{STATE_REL.as_posix()}` directly.
"""
    return text + contract.replace("{{MAX_FIX_ATTEMPTS}}", str(ctx.config.get("maxAutomaticFixAttempts", 3))), result_path


def run_cursor_agent(ctx: Context, prompt: str, log_name: str) -> tuple[int, Path]:
    cmd = resolve_cursor_command(ctx.config)
    args = list(cmd)
    # Flags supported by agent 2026.08.x
    args += ["-p", "--force", "--trust", "--output-format", "text"]
    sandbox = ctx.config.get("sandbox", "disabled")
    if sandbox in {"enabled", "disabled"}:
        args += ["--sandbox", sandbox]
    model = str(ctx.config.get("model", "")).strip()
    if model:
        args += ["--model", model]
    args += ["--workspace", str(ctx.repo)]
    # Never pass the full prompt on argv: Windows CreateProcess limit ~8191 chars
    # truncates transition prompts. Feed via stdin (agent reads it in -p mode).

    logs = ctx.repo / LOGS_REL
    logs.mkdir(parents=True, exist_ok=True)
    ts = stamp()
    log_path = logs / f"{log_name}-{ts}.log"
    prompt_path = logs / f"{log_name}-{ts}.prompt.md"
    prompt_path.write_text(prompt, encoding="utf-8")
    timeout = int(ctx.config.get("agentTimeoutSeconds", 14400))
    print(f"\n=== Cursor Agent ===\nLog: {log_path.relative_to(ctx.repo)}")
    print(f"Prompt file: {prompt_path.relative_to(ctx.repo)} ({len(prompt)} chars via stdin)\n")

    env = os.environ.copy()
    env.setdefault("PYTHONIOENCODING", "utf-8")
    env.setdefault("LANG", "C.UTF-8")
    try:
        cp = subprocess.run(
            args,
            cwd=str(ctx.repo),
            input=prompt.encode("utf-8"),
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            timeout=timeout,
            env=env,
        )
        output = (cp.stdout or b"").decode("utf-8", errors="replace")
        log_path.write_text(output, encoding="utf-8")
        if output:
            _safe_print(output[-5000:])
        return cp.returncode, log_path
    except subprocess.TimeoutExpired as exc:
        output = exc.stdout or b""
        if isinstance(output, bytes):
            output = output.decode("utf-8", errors="replace")
        log_path.write_text(output + "\nTIMEOUT\n", encoding="utf-8")
        return 124, log_path


# --- Reporting ------------------------------------------------------------


def ensure_automation_report(ctx: Context) -> None:
    path = ctx.repo / REPORT_REL
    if path.exists():
        return
    atomic_write_text(
        path,
        "# WayFold Compliance Overnight Automation\n\n"
        f"Started: {now_iso()}\n"
        f"Branch: {git_branch(ctx.repo)}\n"
        f"Initial commit: {git_head(ctx.repo)}\n\n"
        "## Status\nREADY\n",
    )


def append_report(ctx: Context, section: str) -> None:
    path = ctx.repo / REPORT_REL
    ensure_automation_report(ctx)
    with path.open("a", encoding="utf-8") as fh:
        fh.write("\n" + section.rstrip() + "\n")


# --- Doctor / preflight ---------------------------------------------------


def check_phase1_readiness(ctx: Context) -> tuple[str, str]:
    """Return (PASS|WARN|FAIL, detail)."""
    docs = ctx.repo / APP_REL / "docs"
    decisions = docs / "DECISIONS.md"
    arch = docs / "architecture.md"
    progress = docs / "PROGRESS.md"
    vendor = ctx.repo / APP_REL / "vendor" / "ciso-assistant-community"
    missing = []
    if not decisions.exists():
        missing.append("DECISIONS.md")
    if not arch.exists():
        missing.append("architecture.md")
    if missing:
        return "FAIL", f"missing {', '.join(missing)}"
    text = progress.read_text(encoding="utf-8", errors="replace") if progress.exists() else ""
    decisions_text = decisions.read_text(encoding="utf-8", errors="replace")
    if "CISO Assistant" not in decisions_text and "ciso-assistant" not in decisions_text.lower():
        return "FAIL", "core selection not recorded in DECISIONS.md"
    if not vendor.exists():
        return "WARN", "vendor/ciso-assistant-community missing (Phase 1 verify will likely FAIL)"
    if "Phase 1" not in text and "Working Core" not in text and "PHASE 1" not in text:
        return "WARN", (
            "PROGRESS.md does not show Phase 1 implementation; overnight will start with "
            "VERIFY Phase 1 and may enter FIX / HUMAN_REVIEW_REQUIRED"
        )
    return "PASS", "Phase 0 artifacts present; Phase 1 subject to independent verification"


def doctor(ctx: Context) -> int:
    rows: list[tuple[str, str, str]] = []

    def add(name: str, level: str, detail: str) -> None:
        rows.append((name, level, detail))

    add("git", "PASS" if shutil.which("git") else "FAIL", shutil.which("git") or "missing")
    add("python", "PASS", sys.version.split()[0])
    try:
        cmd = resolve_cursor_command(ctx.config)
        add("cursor CLI", "PASS", " ".join(cmd))
        ok, detail = cursor_auth_ok(cmd)
        add("cursor auth", "PASS" if ok else "FAIL", detail)
    except OrchestratorError as exc:
        add("cursor CLI", "FAIL", str(exc))
        add("cursor auth", "FAIL", "n/a")

    remote = run_cmd(["git", "remote", "get-url", "origin"], ctx.repo)
    add("git remote origin", "PASS" if remote.returncode == 0 else "FAIL", (remote.stdout or remote.stderr).strip())

    push = run_cmd(
        ["git", "push", "--dry-run", "origin", f"HEAD:refs/heads/wayfold-compliance-push-probe-{os.getpid()}"],
        ctx.repo,
        timeout=120,
    )
    add("git push auth", "PASS" if push.returncode == 0 else "FAIL", "dry-run ok" if push.returncode == 0 else (push.stderr or push.stdout)[:200])

    gh = shutil.which("gh")
    if gh:
        st = run_cmd(["gh", "auth", "status"], ctx.repo)
        add("gh auth", "PASS" if st.returncode == 0 else "WARN", "ok" if st.returncode == 0 else "not logged in (git push may still work)")
    else:
        add("gh auth", "WARN", "gh not installed")

    branch = git_branch(ctx.repo)
    protected = branch in set(ctx.config.get("protectedBranches", ["main", "master"]))
    add("branch", "WARN" if protected else "PASS", f"{branch} (overnight will move to automation branch)" if protected else branch)

    for key, path in [
        ("config", ctx.config_path),
        ("state", ctx.state_path),
        ("common prompt", ctx.repo / PROMPTS_REL / "common.md"),
    ]:
        add(key, "PASS" if path.exists() else "FAIL", path.relative_to(ctx.repo).as_posix())

    for name, meta in TRANSITIONS.items():
        p = ctx.repo / meta["prompt"]
        add(f"prompt {name}", "PASS" if p.exists() else "FAIL", meta["prompt"])

    for doc in ("PROGRESS.md", "DECISIONS.md", "architecture.md"):
        p = ctx.repo / APP_REL / "docs" / doc
        add(f"doc {doc}", "PASS" if p.exists() else "FAIL", p.relative_to(ctx.repo).as_posix())

    lvl, detail = check_phase1_readiness(ctx)
    add("phase1 readiness", lvl, detail)

    docker = shutil.which("docker")
    add("docker", "PASS" if docker else "WARN", docker or "not found (needed for Phase 1 core)")

    dirty = git_dirty(ctx.repo)
    classes = classify_dirty(dirty)
    if classes["other"] and not ctx.config.get("allowDirtyStart", False):
        add("working tree", "WARN", f"{len(dirty)} changes; {len(classes['other'])} outside compliance")
    else:
        add("working tree", "PASS" if not dirty else "WARN", "clean" if not dirty else f"{len(dirty)} paths")

    writable = True
    try:
        (ctx.repo / LOGS_REL).mkdir(parents=True, exist_ok=True)
        (ctx.repo / RESULTS_REL).mkdir(parents=True, exist_ok=True)
        probe = ctx.repo / LOGS_REL / ".write-probe"
        probe.write_text("ok", encoding="utf-8")
        probe.unlink()
    except Exception as exc:
        writable = False
        add("logs/results writable", "FAIL", str(exc))
    if writable:
        add("logs/results writable", "PASS", "ok")

    print("WayFold automation doctor\n")
    failed = False
    for name, level, detail in rows:
        print(f"[{level:4}] {name}: {detail}")
        if level == "FAIL":
            failed = True
    print(
        "\nMODE: LOCAL_OVERNIGHT\n"
        "CLOUD_AUTOMATION: not configured (agent worker / cloud not verified)\n"
        "CAN I TURN OFF THE PC? NO - keep powered on, awake, networked.\n"
    )
    return 1 if failed else 0


def preflight(ctx: Context, *, for_overnight: bool = True) -> int:
    print("=== Preflight overnight ===\n")
    code = doctor(ctx)
    if code != 0 and for_overnight:
        print("\nPREFLIGHT FAIL - resolve FAIL items before overnight.")
        return code

    # Require cursor auth for overnight
    try:
        cmd = resolve_cursor_command(ctx.config)
        ok, detail = cursor_auth_ok(cmd)
        if not ok:
            print(f"\nPREFLIGHT FAIL - Cursor auth: {detail}")
            print("Run: agent login")
            return 1
    except OrchestratorError as exc:
        print(f"\nPREFLIGHT FAIL - {exc}")
        return 1

    dirty = git_dirty(ctx.repo)
    classes = classify_dirty(dirty)
    ignore_untracked = bool(ctx.config.get("preflightIgnoreUntrackedOther", True))
    blocking_other = []
    for line in classes["other"]:
        untracked = line.startswith("??")
        if untracked and ignore_untracked:
            continue
        blocking_other.append(line)
    if blocking_other and not ctx.config.get("allowDirtyStart", False):
        print("\nPREFLIGHT FAIL - tracked/unexpected dirty paths outside compliance automation:")
        for line in blocking_other[:40]:
            print(" ", line)
        print("Commit/stash unrelated tracked work, or set allowDirtyStart only if understood.")
        return 1
    warned_other = [l for l in classes["other"] if l.startswith("??")]
    if warned_other:
        print(f"\nPREFLIGHT WARN - {len(warned_other)} untracked path(s) outside compliance (ignored for start).")


    if ctx.lock_path.exists():
        try:
            acquire_lock(ctx)
            release_lock(ctx)
        except OrchestratorError as exc:
            print(f"\nPREFLIGHT FAIL - {exc}")
            return 1

    print("\nPREFLIGHT PASS")
    return 0


# --- Core transition execution --------------------------------------------


def load_latest_result(path: Path) -> dict[str, Any]:
    return read_json(path)


def handle_transition_result(ctx: Context, transition: str, result_path: Path) -> str:
    """Apply result to state. Returns next action hint."""
    try:
        result = load_latest_result(result_path)
        validate_transition_result(result, transition)
    except (OrchestratorError, ValueError, json.JSONDecodeError) as exc:
        ctx.state = apply_invalid_result(ctx.state, str(exc))
        ctx.state["lastResultPath"] = result_path.relative_to(ctx.repo).as_posix()
        ctx.save_state()
        append_report(
            ctx,
            f"## Transition {transition}\nFailure: invalid agent result\nError: {exc}\n"
            f"Status: HUMAN_REVIEW_REQUIRED\n",
        )
        commit_changes(ctx, f"chore(compliance): invalid agent result for {transition}")
        try:
            push_branch(ctx)
        except OrchestratorError:
            pass
        return "STOP"

    ctx.state["lastResultPath"] = result_path.relative_to(ctx.repo).as_posix()
    vstatus = result["verificationStatus"]
    phase = int(result["verifiedPhase"])

    if vstatus == "BLOCKED":
        ctx.state = apply_blocked(ctx.state, result.get("blockingIssues"))
        ctx.save_state()
        append_report(ctx, f"## Transition {transition}\nVerification: BLOCKED\nStatus: BLOCKED\n")
        commit_changes(ctx, f"chore(compliance): blocked on phase {phase}")
        try:
            push_branch(ctx)
        except OrchestratorError as exc:
            ctx.state = apply_push_failure(ctx.state, str(exc))
            ctx.save_state()
        return "STOP"

    if vstatus == "FAIL":
        ctx.state = apply_verification_fail(ctx.state, result.get("blockingIssues"))
        # Agent already performed internal retries; treat FAIL as exhausted for this run
        ctx.state["verificationAttempts"] = int(ctx.config.get("maxAutomaticFixAttempts", 3))
        ctx.state["status"] = "HUMAN_REVIEW_REQUIRED"
        ctx.save_state()
        append_report(
            ctx,
            f"## Phase {phase}\nVerification: FAIL\nAttempts: {result.get('fixAttemptsUsed')}\n"
            f"Blocking: {json.dumps(result.get('blockingIssues'), ensure_ascii=False)}\n"
            f"Status: HUMAN_REVIEW_REQUIRED\n"
            f"Last successful commit: {git_head(ctx.repo)}\n"
            f"Recommended human action: inspect PHASE{phase}-VERIFICATION.md and resume after fix\n",
        )
        commit_changes(ctx, f"chore(compliance): phase {phase} human review required")
        try:
            push_branch(ctx)
        except OrchestratorError as exc:
            ctx.state = apply_push_failure(ctx.state, str(exc))
            ctx.save_state()
        return "STOP"

    # PASS
    commit_changes(ctx, f"docs(compliance): verify and close phase {phase}")
    tag_phase(ctx, phase)
    ctx.state = apply_pass_transition(ctx.state, transition)
    ctx.save_state()

    developed = result.get("developedPhase")
    if developed is not None and result.get("developmentStatus") == "IMPLEMENTED":
        commit_changes(ctx, f"feat(compliance): implement phase {developed}")
        append_report(
            ctx,
            f"## Phase {phase}\nVerification: PASS\nTag: phase-{phase}-complete\nPush: pending\n\n"
            f"## Phase {developed}\nDevelopment: DONE\nVerification: AWAITING INDEPENDENT VERIFICATION\n",
        )
    else:
        append_report(ctx, f"## Phase {phase}\nVerification: PASS\nTag: phase-{phase}-complete\n")

    try:
        push_branch(ctx)
    except OrchestratorError as exc:
        ctx.state = apply_push_failure(ctx.state, str(exc))
        ctx.save_state()
        commit_changes(ctx, "chore(compliance): record push failure")
        return "STOP"

    if ctx.state.get("status") == "FINAL_REGRESSION":
        return "FINAL"
    return "CONTINUE"


def execute_transition(ctx: Context, transition: str, *, dry: bool = False, simulated: dict | None = None) -> str:
    meta = TRANSITIONS[transition]
    ctx.state["status"] = "VERIFYING"
    ctx.save_state()

    if dry:
        assert simulated is not None
        result_path = ctx.repo / RESULTS_REL / f"dry-{transition.lower()}-{stamp()}.json"
        result_path.parent.mkdir(parents=True, exist_ok=True)
        atomic_write_json(result_path, simulated)
        return handle_transition_result(ctx, transition, result_path)

    prompt, result_path = render_transition_prompt(ctx, transition)
    # Ensure empty marker so we detect missing writes
    if result_path.exists():
        result_path.unlink()

    log_name = f"transition-{transition.lower().replace('_', '-')}"
    rc, log_path = run_cursor_agent(ctx, prompt, log_name)
    if rc != 0 and not result_path.exists():
        ctx.state = apply_invalid_result(ctx.state, f"Agent exit {rc}; see {log_path}")
        ctx.save_state()
        commit_changes(ctx, f"chore(compliance): agent failure {transition}")
        try:
            push_branch(ctx)
        except OrchestratorError:
            pass
        return "STOP"

    if not result_path.exists():
        # Try to find newest matching result
        results = sorted((ctx.repo / RESULTS_REL).glob(f"transition-{transition.lower().replace('_', '-')}*.json"))
        if results:
            result_path = results[-1]
        else:
            ctx.state = apply_invalid_result(ctx.state, "Agent did not write result JSON")
            ctx.save_state()
            commit_changes(ctx, f"chore(compliance): missing result {transition}")
            try:
                push_branch(ctx)
            except OrchestratorError:
                pass
            return "STOP"

    # Optional develop marker status
    if meta["develop"] is not None:
        ctx.state["status"] = "DEVELOPING"
        ctx.save_state()

    return handle_transition_result(ctx, transition, result_path)


def run_final_regression(ctx: Context, *, dry: bool = False, pass_: bool = True) -> str:
    ctx.state["status"] = "FINAL_REGRESSION"
    ctx.save_state()
    attempts = 0
    max_attempts = int(ctx.config.get("maxAutomaticFixAttempts", 3))

    while attempts < max_attempts:
        attempts += 1
        if dry:
            ok = pass_
        else:
            ok = _final_regression_checks(ctx)

        if ok:
            ctx.state = apply_final_regression_pass(ctx.state)
            ctx.save_state()
            append_report(ctx, "## Final Regression\nPASS\n")
            commit_changes(ctx, "chore(compliance): final regression PASS")
            try:
                push_branch(ctx)
            except OrchestratorError as exc:
                ctx.state = apply_push_failure(ctx.state, str(exc))
                ctx.save_state()
                return "STOP"
            return "MERGE"

        ctx.state = apply_final_regression_fail(ctx.state, attempts, max_attempts)
        ctx.save_state()
        if ctx.state["status"] == "HUMAN_REVIEW_REQUIRED":
            append_report(ctx, f"## Final Regression\nFAIL\nAttempts: {attempts}\nStatus: HUMAN_REVIEW_REQUIRED\n")
            commit_changes(ctx, "chore(compliance): final regression human review")
            try:
                push_branch(ctx)
            except OrchestratorError:
                pass
            return "STOP"
        if not dry:
            # One fix agent pass
            fix_prompt = (
                (ctx.repo / PROMPTS_REL / "common-fix.md").read_text(encoding="utf-8")
                + "\n\nFix ONLY final regression failures for WayFold Compliance. "
                "Do not invent new phases. Write a short summary in PROGRESS.md."
            )
            run_cursor_agent(ctx, fix_prompt, f"final-regression-fix-attempt-{attempts}")

    return "STOP"


def _final_regression_checks(ctx: Context) -> bool:
    """Local deterministic gates + optional agent-authored marker."""
    # All phase verification reports must exist with PASS
    for phase in range(1, 7):
        report = ctx.repo / APP_REL / "docs" / f"PHASE{phase}-VERIFICATION.md"
        if not report.exists():
            print(f"Missing {report}")
            return False
        text = report.read_text(encoding="utf-8", errors="replace").upper()
        if "VERDICT: PASS" not in text and "FINAL VERDICT: PASS" not in text and "\nPASS\n" not in text:
            # Accept explicit Verdict line
            if "PASS" not in text.split("FAIL")[0] if "FAIL" in text else ("PASS" in text):
                print(f"No PASS verdict in {report.name}")
                return False
            if "VERDICT: FAIL" in text or "FINAL VERDICT: FAIL" in text:
                print(f"FAIL verdict in {report.name}")
                return False

    # Compile automation + validate setup
    py = sys.executable
    cp = run_cmd([py, "-m", "py_compile", str(ctx.repo / APP_REL / "automation" / "wayfold_orchestrator.py")], ctx.repo)
    if cp.returncode != 0:
        return False
    cp = run_cmd([py, str(ctx.repo / APP_REL / "automation" / "validate_setup.py")], ctx.repo)
    if cp.returncode != 0:
        print(cp.stdout, cp.stderr)
        return False
    return True


def deploy_production(ctx: Context) -> None:
    """Deploy Compliance to VPS (compliance.wayfold.xyz)."""
    if not ctx.config.get("autoDeploy", False):
        print("autoDeploy disabled — skipping production deploy")
        return
    script = ctx.repo / APP_REL / "deploy" / "deploy-compliance.ps1"
    if not script.exists():
        raise OrchestratorError(f"Missing deploy script: {script}")
    setup_tls = bool(ctx.config.get("autoDeploySetupTls", True))
    args = [
        "powershell",
        "-ExecutionPolicy",
        "Bypass",
        "-File",
        str(script),
    ]
    if setup_tls:
        args.append("-SetupTls")
    print(f"\n=== Production deploy ===\n{' '.join(args)}\n")
    cp = subprocess.run(args, cwd=str(ctx.repo), text=True, capture_output=True)
    log = (cp.stdout or "") + (cp.stderr or "")
    logs = ctx.repo / LOGS_REL
    logs.mkdir(parents=True, exist_ok=True)
    (logs / f"deploy-{stamp()}.log").write_text(log, encoding="utf-8")
    _safe_print(log[-4000:] if log else "")
    if cp.returncode != 0:
        raise OrchestratorError(f"Production deploy failed (exit {cp.returncode})")
    # Prefer public URL; fall back to VPS localhost health via SSH
    remote = str(ctx.config.get("deployRemote", "wayfold@167.233.121.159"))
    public_ok = False
    try:
        import urllib.request
        import ssl

        url = str(ctx.config.get("productionUrl", "https://compliance.wayfold.xyz/api/health/"))
        ctx_ssl = ssl.create_default_context()
        with urllib.request.urlopen(url, timeout=30, context=ctx_ssl) as resp:  # noqa: S310
            body = resp.read().decode("utf-8", errors="replace")
            print(f"Production health: HTTP {resp.status} {body[:200]}")
            public_ok = True
    except Exception as exc:
        print(f"Public HTTPS health not ready yet: {exc}")
    if not public_ok:
        cp = run_cmd(
            [
                "ssh",
                "-o",
                "BatchMode=yes",
                remote,
                "curl -fsS -H 'Host: localhost' http://127.0.0.1:18000/api/health/",
            ],
            ctx.repo,
            timeout=60,
        )
        if cp.returncode != 0:
            raise OrchestratorError(
                "Deploy finished but neither public HTTPS nor VPS localhost health passed. "
                "If Docker is up, run once: sudo bash /home/wayfold/apps/wayfold-compliance/deploy/setup-nginx-tls.sh"
            )
        print(f"VPS localhost health OK: {(cp.stdout or '').strip()}")
        print(
            "NOTE: Public TLS needs one root command on VPS "
            "(passwordless sudo not available): "
            "sudo bash /home/wayfold/apps/wayfold-compliance/deploy/setup-nginx-tls.sh"
        )


def merge_to_main(ctx: Context, *, dry: bool = False) -> str:
    if not ctx.config.get("autoMergeMain", True):
        ctx.state["status"] = "HUMAN_REVIEW_REQUIRED"
        ctx.state["blockingIssues"] = [{"severity": "BLOCKING", "description": "autoMergeMain disabled"}]
        ctx.save_state()
        return "STOP"

    ctx.state["status"] = "MERGING"
    ctx.save_state()
    branch = git_branch(ctx.repo)
    main = str(ctx.config.get("mainBranch", "main"))

    if dry:
        ctx.state = apply_complete(ctx.state)
        ctx.save_state()
        append_report(ctx, f"## Merge\nPASS (dry-run)\n## Deploy\nSKIPPED (dry-run)\n## Final Status\nCOMPLETE\n")
        return "DONE"

    # Checkpoint compliance work before leaving the branch
    commit_changes(ctx, "chore(compliance): pre-merge checkpoint")
    try:
        push_branch(ctx)
        run_cmd(["git", "push", "origin", "--tags"], ctx.repo)
    except OrchestratorError as exc:
        ctx.state = apply_push_failure(ctx.state, str(exc))
        ctx.save_state()
        return "STOP"

    # Stash unrelated dirty paths so switch to main can succeed
    dirty = git_dirty(ctx.repo)
    stashed = False
    if dirty:
        cp = run_cmd(
            ["git", "stash", "push", "-u", "-m", "wayfold-compliance-pre-merge-stash"],
            ctx.repo,
        )
        stashed = cp.returncode == 0

    cp = run_cmd(["git", "fetch", "origin", main], ctx.repo)
    if cp.returncode != 0:
        ctx.state = apply_blocked(ctx.state, [{"severity": "BLOCKING", "description": f"fetch {main} failed"}])
        ctx.save_state()
        return "STOP"

    cp = run_cmd(["git", "switch", main], ctx.repo)
    if cp.returncode != 0:
        cp = run_cmd(["git", "checkout", main], ctx.repo)
    if cp.returncode != 0:
        if stashed:
            run_cmd(["git", "stash", "pop"], ctx.repo)
        ctx.state = apply_blocked(
            ctx.state,
            [{"severity": "BLOCKING", "description": f"cannot switch to {main}: {(cp.stderr or cp.stdout)[:300]}"}],
        )
        ctx.save_state()
        return "STOP"

    cp = run_cmd(["git", "pull", "--ff-only", "origin", main], ctx.repo)
    if cp.returncode != 0:
        print("ff-only pull failed; continuing with merge attempt")

    cp = run_cmd(
        ["git", "merge", "--no-ff", branch, "-m", f"merge: wayfold compliance automation ({branch})"],
        ctx.repo,
    )
    if cp.returncode != 0:
        run_cmd(["git", "merge", "--abort"], ctx.repo)
        ctx.state = apply_merge_conflict(ctx.state, cp.stderr or cp.stdout or "merge failed")
        ctx.save_state()
        run_cmd(["git", "switch", branch], ctx.repo)
        if stashed:
            run_cmd(["git", "stash", "pop"], ctx.repo)
        commit_changes(ctx, "chore(compliance): merge conflict requires human review")
        try:
            push_branch(ctx)
        except OrchestratorError:
            pass
        return "STOP"

    if not _final_regression_checks(ctx):
        ctx.state["status"] = "HUMAN_REVIEW_REQUIRED"
        ctx.state["blockingIssues"] = [{"severity": "BLOCKING", "description": "Post-merge checks failed"}]
        ctx.save_state()
        append_report(ctx, "## Merge\nFAIL post-merge checks\nStatus: HUMAN_REVIEW_REQUIRED\n")
        return "STOP"

    cp = run_cmd(["git", "push", "origin", main], ctx.repo)
    if cp.returncode != 0:
        ctx.state = apply_push_failure(ctx.state, cp.stderr or cp.stdout or "push main failed")
        ctx.save_state()
        return "STOP"

    remote_main = run_cmd(["git", "rev-parse", f"origin/{main}"], ctx.repo).stdout.strip()
    local_main = git_head(ctx.repo)

    deploy_status = "SKIPPED"
    if ctx.config.get("autoDeploy", False):
        try:
            deploy_production(ctx)
            deploy_status = "PASS"
        except OrchestratorError as exc:
            ctx.state["status"] = "HUMAN_REVIEW_REQUIRED"
            ctx.state["blockingIssues"] = [{"severity": "BLOCKING", "description": str(exc)}]
            ctx.state["lastError"] = str(exc)
            ctx.save_state()
            append_report(
                ctx,
                f"## Merge\nPASS\n## Deploy\nFAIL\n{exc}\nStatus: HUMAN_REVIEW_REQUIRED\n",
            )
            commit_changes(ctx, "chore(compliance): deploy failed after merge")
            run_cmd(["git", "push", "origin", main], ctx.repo)
            return "STOP"

    ctx.state = apply_complete(ctx.state)
    ctx.save_state()
    commit_changes(ctx, "chore(compliance): mark automation COMPLETE")
    run_cmd(["git", "push", "origin", main], ctx.repo)
    append_report(
        ctx,
        f"## Merge\nPASS\n## Deploy\n{deploy_status}\n## origin/{main}\n{remote_main or local_main}\n"
        f"## Production\nhttps://compliance.wayfold.xyz\n## Final Status\nCOMPLETE\n",
    )
    run_cmd(["git", "push", "origin", main], ctx.repo)
    if stashed:
        run_cmd(["git", "stash", "pop"], ctx.repo)
    print(f"COMPLETE - origin/{main}={local_main} deploy={deploy_status}")
    return "DONE"


def overnight(ctx: Context, *, dry: bool = False) -> int:
    acquire_lock(ctx)
    ensure_no_nested_git(ctx)
    interrupted = {"flag": False}

    def _handle_sig(signum, frame):  # type: ignore[no-untyped-def]
        interrupted["flag"] = True
        print("\nInterrupt received - saving INTERRUPTED state...")
        ctx.state = apply_interrupted(ctx.state)
        ctx.save_state()

    previous = signal.signal(signal.SIGINT, _handle_sig)
    try:
        ensure_automation_branch(ctx)
        ctx.state = resume_status(ctx.state)
        if not ctx.state.get("startedAt"):
            ctx.state["startedAt"] = now_iso()
        ctx.save_state()
        ensure_automation_report(ctx)
        commit_changes(ctx, "chore(compliance): start overnight automation")
        if ctx.config.get("autoPush", True) and not dry:
            try:
                push_branch(ctx)
            except OrchestratorError as exc:
                print(f"Initial push failed: {exc}")
                ctx.state = apply_push_failure(ctx.state, str(exc))
                ctx.save_state()
                return 2

        if dry:
            return _dry_run_suite(ctx)

        while ctx.state.get("status") not in STOP_STATUSES:
            if interrupted["flag"]:
                return 130
            status = ctx.state.get("status")
            if status == "DEPLOY_RETRY":
                # Merge already landed; retry production deploy only
                ctx.state["status"] = "MERGING"
                ctx.save_state()
                try:
                    deploy_production(ctx)
                except OrchestratorError as exc:
                    ctx.state["status"] = "HUMAN_REVIEW_REQUIRED"
                    ctx.state["blockingIssues"] = [{"severity": "BLOCKING", "description": str(exc)}]
                    ctx.state["lastError"] = str(exc)
                    ctx.save_state()
                    append_report(ctx, f"## Deploy retry\nFAIL\n{exc}\nStatus: HUMAN_REVIEW_REQUIRED\n")
                    commit_changes(ctx, "chore(compliance): deploy retry failed")
                    run_cmd(["git", "push", "origin", str(ctx.config.get("mainBranch", "main"))], ctx.repo)
                    return 2
                ctx.state = apply_complete(ctx.state)
                ctx.save_state()
                commit_changes(ctx, "chore(compliance): mark automation COMPLETE")
                run_cmd(["git", "push", "origin", str(ctx.config.get("mainBranch", "main"))], ctx.repo)
                append_report(
                    ctx,
                    "## Deploy retry\nPASS\n## Production\nhttps://compliance.wayfold.xyz\n## Final Status\nCOMPLETE\n",
                )
                run_cmd(["git", "push", "origin", str(ctx.config.get("mainBranch", "main"))], ctx.repo)
                print("COMPLETE after deploy retry")
                return 0

            if status == "FINAL_REGRESSION":
                action = run_final_regression(ctx)
                if action == "MERGE":
                    return 0 if merge_to_main(ctx) == "DONE" else 2
                return 2

            transition = ctx.state.get("nextTransition")
            if not transition:
                if int(ctx.state.get("lastClosedPhase", 0)) >= 6:
                    ctx.state["status"] = "FINAL_REGRESSION"
                    ctx.save_state()
                    continue
                break

            print(f"\n>>> Running transition {transition} in NEW agent session")
            action = execute_transition(ctx, transition)
            if action == "STOP":
                return 2
            if action == "FINAL":
                cont = run_final_regression(ctx)
                if cont == "MERGE":
                    return 0 if merge_to_main(ctx) == "DONE" else 2
                return 2
            time.sleep(float(ctx.config.get("delayBetweenAgentsSeconds", 2)))

        print("\nFinal state:")
        print(json.dumps(ctx.state, indent=2, ensure_ascii=False))
        return 0 if ctx.state.get("status") == "COMPLETE" else 2
    finally:
        signal.signal(signal.SIGINT, previous)
        release_lock(ctx)


def _dry_run_suite(ctx: Context) -> int:
    """Simulate happy path + failure paths without product changes / agents."""
    print("=== DRY RUN simulation ===")
    base = default_state()
    base["startedAt"] = now_iso()

    # Happy-ish path with phase 3 fail then pass
    state = deepcopy_state(base)
    scenarios = [
        ("1_TO_2", _sim_pass("1_TO_2", 1, 2)),
        ("2_TO_3", _sim_pass("2_TO_3", 2, 3)),
        ("3_TO_4", _sim_fail("3_TO_4", 3)),
    ]
    # First: 3 fails once → human? In dry we simulate fix then pass via orchestrator helpers
    for tr, sim in scenarios[:2]:
        state = apply_pass_transition(state, tr)
    state = apply_verification_fail(state, [{"severity": "BLOCKING", "description": "simulated"}])
    assert state["status"] == "FIXING"
    state = apply_fix_done(state)
    state = apply_pass_transition(state, "3_TO_4")
    for tr in ("4_TO_5", "5_TO_6", "CLOSE_6"):
        state = apply_pass_transition(state, tr)
    assert state["status"] == "FINAL_REGRESSION"
    state = apply_final_regression_pass(state)
    assert state["status"] == "MERGING"
    state = apply_complete(state)
    assert state["status"] == "COMPLETE"
    print("[PASS] happy path + phase3 fix -> COMPLETE")

    # Triple fail -> HUMAN_REVIEW
    state = deepcopy_state(base)
    state["nextTransition"] = "3_TO_4"
    state["lastClosedPhase"] = 2
    state["implementedPhase"] = 3
    for _ in range(3):
        state = apply_verification_fail(state, [{"severity": "BLOCKING", "description": "x"}])
    assert state["status"] == "HUMAN_REVIEW_REQUIRED"
    print("[PASS] 3x FAIL -> HUMAN_REVIEW_REQUIRED")

    # Push failure
    state = deepcopy_state(base)
    state = apply_push_failure(state, "simulated")
    assert state["status"] == "HUMAN_REVIEW_REQUIRED"
    print("[PASS] push failure -> STOP")

    # Final regression fail -> no merge
    state = deepcopy_state(base)
    state = apply_pass_transition(state, "CLOSE_6")
    state = apply_final_regression_fail(state, 3, 3)
    assert state["status"] == "HUMAN_REVIEW_REQUIRED"
    assert state.get("nextTransition") is None
    print("[PASS] final regression FAIL -> no merge")

    # Invalid JSON
    state = deepcopy_state(base)
    state = apply_invalid_result(state, "not json")
    assert state["status"] == "HUMAN_REVIEW_REQUIRED"
    print("[PASS] invalid JSON -> safe stop")

    # Merge conflict
    state = deepcopy_state(base)
    state = apply_merge_conflict(state, "conflict")
    assert state["status"] == "HUMAN_REVIEW_REQUIRED"
    print("[PASS] merge conflict -> safe stop")

    # Interruption recoverable
    state = deepcopy_state(base)
    state["status"] = "VERIFYING"
    state = apply_interrupted(state)
    assert state["status"] == "INTERRUPTED"
    state = resume_status(state)
    assert state["status"] == "READY"
    print("[PASS] interruption -> recoverable")

    # Stale lock handling tested indirectly via acquire; unit test covers pid
    print("\nDRY RUN COMPLETE")
    return 0


def deepcopy_state(state: dict[str, Any]) -> dict[str, Any]:
    return json.loads(json.dumps(state))


def _sim_pass(transition: str, verify: int, develop: int | None) -> dict[str, Any]:
    return {
        "transition": transition,
        "verifiedPhase": verify,
        "verificationStatus": "PASS",
        "developedPhase": develop,
        "developmentStatus": "IMPLEMENTED" if develop is not None else "SKIPPED",
        "fixAttemptsUsed": 0,
        "blockingIssues": [],
        "summary": "dry-run",
    }


def _sim_fail(transition: str, verify: int) -> dict[str, Any]:
    return {
        "transition": transition,
        "verifiedPhase": verify,
        "verificationStatus": "FAIL",
        "developedPhase": None,
        "developmentStatus": "NOT_STARTED",
        "fixAttemptsUsed": 3,
        "blockingIssues": [{"severity": "BLOCKING", "description": "dry-run fail"}],
        "summary": "dry-run",
    }


def cmd_status(ctx: Context) -> None:
    branch = git_branch(ctx.repo)
    head = git_head(ctx.repo)
    print("WayFold Compliance automation status\n")
    print(f"Current transition : {ctx.state.get('nextTransition')}")
    print(f"Last closed phase  : {ctx.state.get('lastClosedPhase')}")
    print(f"Implemented phase  : {ctx.state.get('implementedPhase')}")
    print(f"Status             : {ctx.state.get('status')}")
    print(f"Verification attempts: {ctx.state.get('verificationAttempts')}")
    print(f"Blocking issues    : {json.dumps(ctx.state.get('blockingIssues'), ensure_ascii=False)}")
    print(f"Current branch     : {branch}")
    print(f"Last commit        : {head}")
    print(f"Last result        : {ctx.state.get('lastResultPath')}")
    print(f"Last error         : {ctx.state.get('lastError')}")
    nxt = ctx.state.get("nextTransition")
    if ctx.state.get("status") == "COMPLETE":
        next_action = "NONE (COMPLETE)"
    elif ctx.state.get("status") == "HUMAN_REVIEW_REQUIRED":
        next_action = "Human fix -> reset/resume overnight"
    elif ctx.state.get("status") == "FINAL_REGRESSION":
        next_action = "Final regression -> merge main"
    elif nxt:
        meta = TRANSITIONS[nxt]
        next_action = f"VERIFY Phase {meta['verify']}" + (
            f" -> DEVELOP Phase {meta['develop']}" if meta["develop"] else " -> FINAL REGRESSION"
        )
    else:
        next_action = "Inspect state"
    print(f"Next action        : {next_action}")


def cmd_reset(ctx: Context, transition: str) -> None:
    if transition not in TRANSITIONS:
        raise OrchestratorError(f"Unknown transition {transition}")
    meta = TRANSITIONS[transition]
    ctx.state = default_state()
    ctx.state["nextTransition"] = transition
    ctx.state["lastClosedPhase"] = int(meta["verify"]) - 1
    ctx.state["implementedPhase"] = int(meta["verify"])
    ctx.state["status"] = "READY"
    ctx.state["startedAt"] = None
    ctx.save_state()
    print(f"Reset to transition {transition}")


def main() -> int:
    # Ensure automation dir on sys.path for state_machine import when run as script
    auto_dir = Path(__file__).resolve().parent
    if str(auto_dir) not in sys.path:
        sys.path.insert(0, str(auto_dir))

    parser = argparse.ArgumentParser(description="WayFold Compliance overnight orchestrator")
    sub = parser.add_subparsers(dest="cmd", required=True)
    sub.add_parser("doctor")
    sub.add_parser("status")
    sub.add_parser("preflight")
    sub.add_parser("overnight")
    sub.add_parser("dry-run")
    step = sub.add_parser("step", help="Debug: run only the next transition")
    step.add_argument("--dry-result", help="Path to a simulated result JSON")
    reset = sub.add_parser("reset")
    reset.add_argument("--transition", required=True, choices=sorted(TRANSITIONS.keys()))

    args = parser.parse_args()
    try:
        # Re-import friendly when executed as __main__
        repo = find_repo_root()
        os.chdir(repo)
        ctx = Context(repo)

        if args.cmd == "doctor":
            return doctor(ctx)
        if args.cmd == "status":
            cmd_status(ctx)
            return 0
        if args.cmd == "preflight":
            return preflight(ctx)
        if args.cmd == "reset":
            cmd_reset(ctx, args.transition)
            return 0
        if args.cmd == "dry-run":
            acquire_lock(ctx)
            try:
                return _dry_run_suite(ctx)
            finally:
                release_lock(ctx)
        if args.cmd == "step":
            acquire_lock(ctx)
            try:
                ensure_automation_branch(ctx)
                ctx.state = resume_status(ctx.state)
                ctx.save_state()
                tr = ctx.state.get("nextTransition")
                if not tr:
                    print("No next transition")
                    return 0
                if args.dry_result:
                    sim = read_json(Path(args.dry_result))
                    return 0 if execute_transition(ctx, tr, dry=True, simulated=sim) != "STOP" else 2
                action = execute_transition(ctx, tr)
                return 0 if action != "STOP" else 2
            finally:
                release_lock(ctx)

        # overnight
        pf = preflight(ctx, for_overnight=True)
        if pf != 0:
            return pf
        return overnight(ctx, dry=False)
    except OrchestratorError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2
    except KeyboardInterrupt:
        print("Interrupted.", file=sys.stderr)
        try:
            repo = find_repo_root()
            ctx = Context(repo)
            ctx.state = apply_interrupted(ctx.state)
            ctx.save_state()
            release_lock(ctx)
        except Exception:
            pass
        return 130


if __name__ == "__main__":
    # Path bootstrap before importing state_machine when run as file
    _auto = Path(__file__).resolve().parent
    if str(_auto) not in sys.path:
        sys.path.insert(0, str(_auto))
    raise SystemExit(main())
