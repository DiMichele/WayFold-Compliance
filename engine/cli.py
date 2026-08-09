from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from engine.authz import assert_tenant_access
from engine.checklist import build_unified_checklist
from engine.impact import rank_control_impact
from engine.program_loader import load_program_snapshot
from engine.readiness import framework_readiness
from engine.serialize import to_jsonable


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="WayFold Unified Compliance CLI")
    parser.add_argument(
        "--program",
        type=Path,
        default=ROOT / "engine" / "fixtures" / "michele_phase2_program.json",
    )
    parser.add_argument(
        "--actor-tenants",
        default="",
        help="Comma-separated tenant ids the actor may access",
    )
    parser.add_argument("--superuser", action="store_true")
    parser.add_argument(
        "--format",
        choices=("json", "text"),
        default="text",
    )
    args = parser.parse_args(argv)

    program = load_program_snapshot(args.program)
    actor_tenants = {t.strip() for t in args.actor_tenants.split(",") if t.strip()}
    # Default deny: omitting --actor-tenants must NOT imply superuser.
    if not args.superuser and not actor_tenants:
        print(
            json.dumps(
                {
                    "error": "authentication_required",
                    "hint": "pass --superuser or --actor-tenants=<tenant-id>",
                    "tenant_id": program.tenant_id,
                }
            )
        )
        return 2
    decision = assert_tenant_access(
        actor_tenant_ids=actor_tenants,
        is_superuser=args.superuser,
        target_tenant_id=program.tenant_id,
    )
    if not decision.allowed:
        print(json.dumps({"error": decision.reason, "tenant_id": program.tenant_id}))
        return 2

    checklist = build_unified_checklist(program)
    readiness = framework_readiness(program, checklist)
    impact = rank_control_impact(program, checklist)

    if args.format == "json":
        print(
            json.dumps(
                {
                    "checklist": to_jsonable(checklist),
                    "readiness": to_jsonable(readiness),
                    "impact": to_jsonable(impact),
                },
                indent=2,
                ensure_ascii=False,
            )
        )
        return 0

    print(f"Program: {checklist.program_name}")
    print(
        f"Raw requirements: {checklist.raw_requirement_count} | "
        f"Unified controls: {checklist.unified_control_count} | "
        f"Unmapped: {len(checklist.unmapped)}"
    )
    print("\n== Unified checklist ==")
    for c in checklist.controls:
        fws = ", ".join(
            f"{x.framework_name}:{x.requirement_code}/{x.relation.value}"
            for x in c.framework_coverage
        )
        print(
            f"- {c.canonical_control_ref or c.name} | {c.status.value} | "
            f"owner={c.owner} due={c.due_date} evid={c.evidence_count} | {fws}"
        )
        if c.gap_notes:
            print(f"  delta: {c.gap_notes}")
    print("\n== Unmapped ==")
    for u in checklist.unmapped:
        print(f"- {u.framework_name} {u.code}: {u.title}")
    print("\n== Framework readiness ==")
    for r in readiness:
        pct = (
            f"{r.implementation_readiness:.0%}"
            if r.implementation_readiness is not None
            else "n/a"
        )
        print(
            f"- {r.framework_name}@{r.framework_version}: readiness={pct} "
            f"FULL={r.fully_covered} PARTIAL={r.partially_covered} "
            f"NOT={r.not_covered} UNMAPPED={r.unmapped} N/A={r.not_applicable}"
        )
    print("\n== Control impact (top) ==")
    for row in impact[:5]:
        print(f"- {row.canonical_control_ref}: {row.readable_summary}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
