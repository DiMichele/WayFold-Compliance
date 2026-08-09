"""Private evidence binary storage with authorization middleware.

Files are never served via static public URLs. Download requires:
authenticate → authorize tenant → authorize role → stream bytes.
"""

from __future__ import annotations

import hashlib
import json
import re
import secrets
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from engine.authz import assert_tenant_access
from engine.rbac import (
    PERM_EVIDENCE_DOWNLOAD,
    PERM_EVIDENCE_READ,
    PERM_EVIDENCE_WRITE,
    Role,
    has_permission,
    parse_role,
)
from engine.runtime_paths import data_root

MAX_UPLOAD_BYTES = 20 * 1024 * 1024  # 20 MiB
ALLOWED_EXTENSIONS = frozenset(
    {".pdf", ".png", ".jpg", ".jpeg", ".txt", ".md", ".docx", ".xlsx", ".csv", ".json"}
)
ALLOWED_CONTENT_TYPES = frozenset(
    {
        "application/pdf",
        "image/png",
        "image/jpeg",
        "text/plain",
        "text/markdown",
        "text/csv",
        "application/json",
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    }
)

# Magic byte signatures (extension → prefixes)
_MAGIC: dict[str, tuple[bytes, ...]] = {
    ".pdf": (b"%PDF",),
    ".png": (b"\x89PNG\r\n\x1a\n",),
    ".jpg": (b"\xff\xd8\xff",),
    ".jpeg": (b"\xff\xd8\xff",),
}


class EvidenceSensitivity:
    NORMAL = "NORMAL"
    CONFIDENTIAL = "CONFIDENTIAL"
    RESTRICTED = "RESTRICTED"


class EvidenceLifecycle:
    VALID = "VALID"
    EXPIRING = "EXPIRING"
    EXPIRED = "EXPIRED"
    REVIEW_REQUIRED = "REVIEW_REQUIRED"
    PARTIAL = "PARTIAL"


@dataclass
class StoredEvidence:
    id: str
    tenant_id: str
    program_id: str
    title: str
    filename: str
    content_type: str
    size_bytes: int
    sha256: str
    storage_relpath: str
    control_refs: list[str] = field(default_factory=list)
    status: str = EvidenceLifecycle.VALID
    sensitivity: str = EvidenceSensitivity.CONFIDENTIAL
    collected_at: str | None = None
    valid_until: str | None = None
    reviewed_at: str | None = None
    reviewed_by: str | None = None
    notes: str = ""
    dataset_marker: str = ""


@dataclass
class AuthzContext:
    username: str
    role: Role | str
    actor_tenant_ids: set[str]
    is_superuser: bool


def evidence_root() -> Path:
    root = data_root() / "evidence"
    root.mkdir(parents=True, exist_ok=True)
    return root


def catalog_path() -> Path:
    return evidence_root() / "catalog.json"


def sanitize_filename(name: str) -> str:
    base = Path(name or "file.bin").name
    base = base.replace("\\", "/").split("/")[-1]
    base = re.sub(r"[^\w.\- ()\[\]]+", "_", base, flags=re.UNICODE).strip(" .")
    if not base or base in {".", ".."}:
        base = "file.bin"
    if len(base) > 180:
        stem = Path(base).stem[:140]
        suf = Path(base).suffix[:20]
        base = f"{stem}{suf}"
    return base


def validate_upload(
    *,
    filename: str,
    content: bytes,
    content_type: str,
) -> str | None:
    """Return error code or None if OK. Hook for future antivirus scan."""
    if not content:
        return "empty_file"
    if len(content) > MAX_UPLOAD_BYTES:
        return "file_too_large"
    safe = sanitize_filename(filename)
    ext = Path(safe).suffix.lower()
    if ext not in ALLOWED_EXTENSIONS:
        return "extension_not_allowed"
    ctype = (content_type or "").split(";")[0].strip().lower()
    if not ctype or ctype == "application/octet-stream":
        # octet-stream alone is never sufficient validation
        ctype = _guess_content_type(ext)
    if ctype not in ALLOWED_CONTENT_TYPES:
        return "content_type_not_allowed"
    if ".." in safe or safe.startswith("/") or "\\" in safe:
        return "path_traversal"
    magic_err = _validate_magic(ext, content)
    if magic_err:
        return magic_err
    # Malware scan hook — NOT IMPLEMENTED (must not report PASS)
    scan_result = scan_content(content, filename=safe)
    if scan_result and scan_result != "NOT_IMPLEMENTED":
        return scan_result
    return None


def _guess_content_type(ext: str) -> str:
    return {
        ".pdf": "application/pdf",
        ".png": "image/png",
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg",
        ".txt": "text/plain",
        ".md": "text/markdown",
        ".csv": "text/csv",
        ".json": "application/json",
        ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        ".xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    }.get(ext, "")


def _validate_magic(ext: str, content: bytes) -> str | None:
    prefixes = _MAGIC.get(ext)
    if not prefixes:
        return None
    if not any(content.startswith(p) for p in prefixes):
        return "file_signature_mismatch"
    return None


def scan_content(content: bytes, *, filename: str) -> str | None:  # noqa: ARG001
    """Antivirus/scan hook — NOT IMPLEMENTED (do not claim PASS)."""
    return "NOT_IMPLEMENTED"


def _load_catalog() -> dict[str, Any]:
    path = catalog_path()
    if not path.is_file():
        return {"items": []}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {"items": []}


def _save_catalog(data: dict[str, Any]) -> None:
    path = catalog_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    tmp.replace(path)


def _row_to_item(row: dict[str, Any]) -> StoredEvidence:
    return StoredEvidence(
        id=str(row["id"]),
        tenant_id=str(row["tenant_id"]),
        program_id=str(row.get("program_id") or ""),
        title=str(row.get("title") or row.get("filename") or row["id"]),
        filename=str(row.get("filename") or "file.bin"),
        content_type=str(row.get("content_type") or "application/octet-stream"),
        size_bytes=int(row.get("size_bytes") or 0),
        sha256=str(row.get("sha256") or ""),
        storage_relpath=str(row.get("storage_relpath") or ""),
        control_refs=list(row.get("control_refs") or []),
        status=str(row.get("status") or EvidenceLifecycle.VALID),
        sensitivity=str(row.get("sensitivity") or EvidenceSensitivity.CONFIDENTIAL),
        collected_at=row.get("collected_at"),
        valid_until=row.get("valid_until"),
        reviewed_at=row.get("reviewed_at"),
        reviewed_by=row.get("reviewed_by"),
        notes=str(row.get("notes") or ""),
        dataset_marker=str(row.get("dataset_marker") or ""),
    )


def list_evidence(*, tenant_id: str | None = None, program_id: str | None = None) -> list[StoredEvidence]:
    items = [_row_to_item(r) for r in _load_catalog().get("items", [])]
    if tenant_id:
        items = [i for i in items if i.tenant_id == tenant_id]
    if program_id:
        items = [i for i in items if i.program_id == program_id]
    return items


def get_evidence(evidence_id: str) -> StoredEvidence | None:
    for item in list_evidence():
        if item.id == evidence_id:
            return item
    return None


def authorize_evidence_access(
    item: StoredEvidence,
    ctx: AuthzContext,
    *,
    permission: str = PERM_EVIDENCE_DOWNLOAD,
) -> tuple[bool, str]:
    role = ctx.role if isinstance(ctx.role, Role) else parse_role(ctx.role)
    if not has_permission(role, permission):
        return False, "permission_denied"
    decision = assert_tenant_access(
        actor_tenant_ids=ctx.actor_tenant_ids,
        is_superuser=ctx.is_superuser,
        target_tenant_id=item.tenant_id,
    )
    if not decision.allowed:
        return False, decision.reason
    return True, "ok"


def store_evidence(
    *,
    tenant_id: str,
    program_id: str,
    title: str,
    filename: str,
    content: bytes,
    content_type: str = "application/octet-stream",
    control_refs: list[str] | None = None,
    status: str = EvidenceLifecycle.VALID,
    sensitivity: str = EvidenceSensitivity.CONFIDENTIAL,
    valid_until: str | None = None,
    notes: str = "",
    evidence_id: str | None = None,
    dataset_marker: str = "",
    ctx: AuthzContext | None = None,
) -> StoredEvidence:
    if ctx is not None:
        role = ctx.role if isinstance(ctx.role, Role) else parse_role(ctx.role)
        if not has_permission(role, PERM_EVIDENCE_WRITE):
            raise PermissionError("permission_denied")
        decision = assert_tenant_access(
            actor_tenant_ids=ctx.actor_tenant_ids,
            is_superuser=ctx.is_superuser,
            target_tenant_id=tenant_id,
        )
        if not decision.allowed:
            raise PermissionError(decision.reason)

    err = validate_upload(filename=filename, content=content, content_type=content_type)
    if err:
        raise ValueError(err)

    eid = evidence_id or f"ev-{secrets.token_hex(8)}"
    safe = sanitize_filename(filename)
    rel = Path(tenant_id) / eid / safe
    abs_path = (evidence_root() / rel).resolve()
    try:
        abs_path.relative_to(evidence_root().resolve())
    except ValueError as exc:
        raise ValueError("path_traversal") from exc
    abs_path.parent.mkdir(parents=True, exist_ok=True)
    abs_path.write_bytes(content)

    item = StoredEvidence(
        id=eid,
        tenant_id=tenant_id,
        program_id=program_id,
        title=title or safe,
        filename=safe,
        content_type=content_type.split(";")[0].strip().lower(),
        size_bytes=len(content),
        sha256=hashlib.sha256(content).hexdigest(),
        storage_relpath=rel.as_posix(),
        control_refs=list(control_refs or []),
        status=status,
        sensitivity=sensitivity,
        collected_at=datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        valid_until=valid_until,
        notes=notes,
        dataset_marker=dataset_marker,
    )
    data = _load_catalog()
    items = [r for r in data.get("items", []) if str(r.get("id")) != eid]
    items.append(asdict(item))
    data["items"] = items
    _save_catalog(data)
    return item


def read_evidence_bytes(item: StoredEvidence, ctx: AuthzContext) -> bytes:
    ok, reason = authorize_evidence_access(item, ctx, permission=PERM_EVIDENCE_DOWNLOAD)
    if not ok:
        raise PermissionError(reason)
    # Also require read
    role = ctx.role if isinstance(ctx.role, Role) else parse_role(ctx.role)
    if not has_permission(role, PERM_EVIDENCE_READ):
        raise PermissionError("permission_denied")
    path = (evidence_root() / item.storage_relpath).resolve()
    try:
        path.relative_to(evidence_root().resolve())
    except ValueError as exc:
        raise PermissionError("path_traversal") from exc
    if not path.is_file():
        raise FileNotFoundError("evidence_file_missing")
    return path.read_bytes()


def seed_demo_evidence_files(program) -> list[StoredEvidence]:
    """Materialize binary placeholders for program evidence snapshots."""
    created: list[StoredEvidence] = []
    for ev in getattr(program, "evidences", []) or []:
        raw_name = ev.filename or f"{ev.id}.txt"
        ext = Path(raw_name).suffix.lower()
        if ext == ".pdf":
            # Minimal valid PDF signature for magic validation
            body = (
                b"%PDF-1.4\n%\xe2\xe3\xcf\xd3\n"
                b"1 0 obj<<>>endobj\ntrailer<<>>\n%%EOF\n"
                + f"% id={ev.id} title={ev.title}\n".encode("utf-8")
            )
            ctype = "application/pdf"
            fname = raw_name
        else:
            body = (
                f"WayFold Compliance evidence placeholder\n"
                f"id={ev.id}\n"
                f"title={ev.title}\n"
                f"program={program.program_id}\n"
                f"marker={getattr(program, 'dataset_marker', '')}\n"
            ).encode("utf-8")
            ctype = "text/plain"
            fname = raw_name if ext in ALLOWED_EXTENSIONS else f"{ev.id}.txt"
        item = store_evidence(
            tenant_id=program.tenant_id,
            program_id=program.program_id,
            title=ev.title,
            filename=fname,
            content=body,
            content_type=ctype,
            control_refs=list(ev.control_refs or []),
            status=getattr(ev, "status", EvidenceLifecycle.VALID) or EvidenceLifecycle.VALID,
            sensitivity=EvidenceSensitivity.CONFIDENTIAL,
            valid_until=getattr(ev, "valid_until", None),
            notes=getattr(ev, "notes", "") or "",
            evidence_id=ev.id,
            dataset_marker=getattr(program, "dataset_marker", "") or "",
        )
        created.append(item)
    return created
