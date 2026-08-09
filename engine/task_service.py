"""Task lifecycle over program snapshot (interim → CISO TaskNode)."""

from __future__ import annotations

import json
import secrets
from datetime import datetime, timezone
from html import escape
from pathlib import Path
from typing import Any

from engine.domain import ProgramSnapshot, RemediationTaskSnapshot
from engine.program_authoring import find_program_path, save_program_snapshot
from engine.program_loader import load_program_snapshot
from engine.runtime_paths import data_root


def _now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def get_task(program: ProgramSnapshot, task_id: str) -> RemediationTaskSnapshot | None:
    for t in program.tasks or []:
        if t.id == task_id:
            return t
    return None


def render_task_form(
    *,
    nav_qs: str,
    csrf: str,
    task: RemediationTaskSnapshot | None,
    program: ProgramSnapshot,
) -> str:
    t = task
    action = f"/tasks/edit?{nav_qs}" if t else f"/tasks/new?{nav_qs}"
    title = escape(t.title if t else "")
    owner = escape(t.owner or "" if t else "")
    due = escape(t.due_date or "" if t else "")
    priority = (t.priority if t else "MEDIUM") or "MEDIUM"
    status = (t.status if t else "TODO") or "TODO"
    notes = escape(t.notes if t else "")
    control = escape(t.control_ref or "" if t else "")
    tid = escape(t.id if t else "")
    status_opts = "".join(
        f"<option value='{s}' {'selected' if status == s else ''}>{s}</option>"
        for s in ("TODO", "IN_PROGRESS", "REVIEW", "DONE")
    )
    pr_opts = "".join(
        f"<option value='{p}' {'selected' if priority == p else ''}>{p}</option>"
        for p in ("LOW", "MEDIUM", "HIGH")
    )
    reopen = ""
    if t and status == "DONE":
        reopen = (
            f"<button class='btn' type='submit' name='action' value='reopen'>Riapri</button>"
        )
    return f"""
<div class='page-head'><h1>{"Modifica attività" if t else "Nuova attività"}</h1>
<p class='subtitle'>Programma: {escape(program.program_name)}</p></div>
<form method='post' action='{action}' class='panel' style='padding:18px'>
<input type='hidden' name='csrf_token' value='{csrf}'>
<input type='hidden' name='task_id' value='{tid}'>
<div class='form-grid'>
<div class='form-field full'><label>Titolo</label><input name='title' value='{title}' required></div>
<div class='form-field'><label>Controllo</label><input name='control_ref' value='{control}'></div>
<div class='form-field'><label>Owner</label><input name='owner' value='{owner}'></div>
<div class='form-field'><label>Scadenza</label><input type='date' name='due_date' value='{due}'></div>
<div class='form-field'><label>Priorità</label><select name='priority'>{pr_opts}</select></div>
<div class='form-field'><label>Stato</label><select name='status'>{status_opts}</select></div>
<div class='form-field full'><label>Note</label><textarea name='notes'>{notes}</textarea></div>
</div>
<div class='page-actions' style='margin-top:14px'>
<button class='btn primary' type='submit' name='action' value='save'>Salva</button>
<button class='btn' type='submit' name='action' value='complete'>Completa</button>
{reopen}
<a class='btn ghost' href='/tasks?{nav_qs}'>Annulla</a>
</div></form>
"""


def upsert_task(
    *,
    program: ProgramSnapshot,
    registry_path: Path,
    title: str,
    actor: str,
    task_id: str | None = None,
    control_ref: str | None = None,
    owner: str | None = None,
    due_date: str | None = None,
    priority: str = "MEDIUM",
    status: str = "TODO",
    notes: str = "",
    requirement_id: str | None = None,
    action: str = "save",
) -> RemediationTaskSnapshot:
    snap_path = find_program_path(program.program_id, registry_path)
    if snap_path is None:
        raise FileNotFoundError("program_snapshot_not_writable")
    prog = load_program_snapshot(snap_path)
    tasks = list(prog.tasks or [])
    if action == "complete":
        status = "DONE"
    elif action == "reopen":
        status = "TODO"

    if task_id:
        found = False
        new_tasks: list[RemediationTaskSnapshot] = []
        for t in tasks:
            if t.id != task_id:
                new_tasks.append(t)
                continue
            found = True
            new_tasks.append(
                RemediationTaskSnapshot(
                    id=t.id,
                    title=title or t.title,
                    control_ref=control_ref if control_ref is not None else t.control_ref,
                    owner=owner if owner is not None else t.owner,
                    status=status or t.status,
                    due_date=due_date if due_date is not None else t.due_date,
                    priority=priority or t.priority,
                    notes=notes if notes is not None else t.notes,
                    requirement_id=requirement_id or t.requirement_id,
                    gap_taxonomy=t.gap_taxonomy,
                    created_by=t.created_by or actor,
                    updated_at=_now(),
                    tenant_id=prog.tenant_id,
                    program_id=prog.program_id,
                )
            )
        if not found:
            raise KeyError(task_id)
        tasks = new_tasks
        result = next(t for t in tasks if t.id == task_id)
    else:
        tid = f"task-{secrets.token_hex(4)}"
        result = RemediationTaskSnapshot(
            id=tid,
            title=title,
            control_ref=control_ref or None,
            owner=owner or None,
            status=status or "TODO",
            due_date=due_date or None,
            priority=priority or "MEDIUM",
            notes=notes or "",
            requirement_id=requirement_id,
            created_by=actor,
            updated_at=_now(),
            tenant_id=prog.tenant_id,
            program_id=prog.program_id,
        )
        tasks.append(result)

    from dataclasses import replace

    updated = replace(prog, tasks=tasks)
    # preserve owner/description via save that includes them
    save_program_snapshot(updated, snap_path)
    # re-write owner/description if present on disk
    try:
        raw = json.loads(snap_path.read_text(encoding="utf-8"))
        raw["owner"] = raw.get("owner") or getattr(prog, "owner", "") or ""
        raw["description"] = raw.get("description") or getattr(prog, "description", "") or ""
        snap_path.write_text(json.dumps(raw, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    except (OSError, json.JSONDecodeError):
        pass
    return result
