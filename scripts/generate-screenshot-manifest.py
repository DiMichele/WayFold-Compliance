"""Generate docs/review/SCREENSHOT-MANIFEST.json from pack PNGs + URL table."""
from __future__ import annotations

import hashlib
import json
import pathlib
from datetime import datetime, timezone

ROOT = pathlib.Path(__file__).resolve().parents[1]
REVIEW = ROOT / "docs" / "review"
BASE_URL = "https://compliance.wayfold.xyz"
ROLE = "SUPER_ADMIN (admin)"
PROGRAM = "program-michele-cyber-2026"
TS = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

# Primary entries for external review (one row per screenshot file).
ENTRIES: list[dict[str, str]] = [
    {"file": "docs/review/final/01-login.png", "page": "Login", "url": "/login", "program": ""},
    {"file": "docs/review/final/02-portfolio.png", "page": "Portfolio", "url": "/portfolio", "program": ""},
    {"file": "docs/review/realign/01-portfolio.png", "page": "Portfolio", "url": "/portfolio", "program": ""},
    {"file": "docs/review/final/03-clients.png", "page": "Clienti", "url": "/clients", "program": ""},
    {"file": "docs/review/realign/06-clients.png", "page": "Clienti", "url": "/clients", "program": ""},
    {
        "file": "docs/review/final/04-michele-workspace.png",
        "page": "Workspace Michele",
        "url": "/client",
        "program": PROGRAM,
    },
    {
        "file": "docs/review/final/05-unified-controls.png",
        "page": "Unified Controls",
        "url": "/checklist",
        "program": PROGRAM,
    },
    {
        "file": "docs/review/final/06-control-iam-detail.png",
        "page": "Control IAM",
        "url": "/control",
        "program": PROGRAM,
    },
    {
        "file": "docs/review/final/07-gap-assessment.png",
        "page": "Gap Assessment",
        "url": "/gaps",
        "program": PROGRAM,
    },
    {
        "file": "docs/review/final/08-tasks.png",
        "page": "Tasks",
        "url": "/tasks",
        "program": PROGRAM,
    },
    {
        "file": "docs/review/final/09-evidence.png",
        "page": "Evidence",
        "url": "/evidence",
        "program": PROGRAM,
    },
    {"file": "docs/review/final/10-frameworks.png", "page": "Frameworks", "url": "/frameworks", "program": ""},
    {
        "file": "docs/review/realign/02-framework-list.png",
        "page": "Frameworks",
        "url": "/frameworks",
        "program": "",
    },
    {
        "file": "docs/review/realign/03-framework-create.png",
        "page": "Nuovo framework",
        "url": "/frameworks/new",
        "program": "",
    },
    {
        "file": "docs/review/final/11-framework-nis2-detail.png",
        "page": "Framework NIS2 versions",
        "url": "/frameworks/detail?framework_id=fw-nis2-it-2026-1&tab=versions",
        "program": "",
    },
    {
        "file": "docs/review/realign/05-nis2-versions.png",
        "page": "Framework NIS2 versions",
        "url": "/frameworks/detail?framework_id=fw-nis2-it-2026-1&tab=versions",
        "program": "",
    },
    {
        "file": "docs/review/realign/04-control-catalog.png",
        "page": "Catalogo controlli",
        "url": "/controls",
        "program": "",
    },
    {"file": "docs/review/final/12-mappings.png", "page": "Mappature", "url": "/mappings", "program": ""},
    {"file": "docs/review/final/13-regulatory.png", "page": "Regulatory", "url": "/changes", "program": ""},
    {
        "file": "docs/review/final/14-report.png",
        "page": "Report",
        "url": "/report",
        "program": PROGRAM,
    },
    {"file": "docs/review/final/15-settings.png", "page": "Settings", "url": "/settings", "program": ""},
    {"file": "docs/review/final/16-audit-log.png", "page": "Audit log", "url": "/audit", "program": ""},
]


def sha256(path: pathlib.Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> None:
    items: list[dict[str, object]] = []
    seen_sha: dict[str, list[str]] = {}
    for row in ENTRIES:
        rel = row["file"]
        path = ROOT / rel.replace("docs/review/", "docs/review/").split("docs/review/", 1)[-1]
        path = ROOT / "docs" / "review" / rel.split("docs/review/", 1)[-1]
        if not path.is_file():
            raise SystemExit(f"missing screenshot: {path}")
        digest = sha256(path)
        seen_sha.setdefault(digest, []).append(rel)
        url = row["url"]
        if row["program"]:
            sep = "&" if "?" in url else "?"
            url = f"{url}{sep}program_id={row['program']}"
        items.append(
            {
                "page": row["page"],
                "url": f"{BASE_URL}{url}",
                "role": ROLE,
                "program": row["program"] or None,
                "timestamp": TS,
                "image_path": rel,
                "image_sha256": digest,
                "bytes": path.stat().st_size,
            }
        )

    dupes = {k: v for k, v in seen_sha.items() if len(v) > 1}
    manifest = {
        "generated_at": TS,
        "live": BASE_URL,
        "dataset": "WF_REVIEW_DEMO_2026",
        "entries": items,
        "duplicate_sha256_groups": dupes,
    }
    out = REVIEW / "SCREENSHOT-MANIFEST.json"
    out.write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"Wrote {out} ({len(items)} entries, {len(dupes)} duplicate groups)")


if __name__ == "__main__":
    main()
