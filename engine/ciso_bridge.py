"""Export a ProgramSnapshot from a live CISO Assistant ORM session.

Intended to run inside the CISO backend container:

  PYTHONPATH=/code:/wayfold python /wayfold/engine/ciso_bridge.py \\
    --folder "Michele Demo" --perimeter "Cyber Compliance Demo" \\
    --out /wayfold/engine/fixtures/michele_from_ciso.json

Does not mutate global KB libraries. Optional --seed-phase2-mappings writes
WayFold overlay mappings for the first assessable requirements of each
assessment, preserving PARTIAL deltas for demo.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


def export_program(folder_name: str, perimeter_name: str, seed_phase2: bool = False) -> dict:
    import os

    import django

    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "ciso_assistant.settings")
    django.setup()
    from core.models import (
        AppliedControl,
        ComplianceAssessment,
        Perimeter,
        RequirementAssessment,
        TaskNode,
    )
    from iam.models import Folder

    from engine.checklist import map_ciso_applied_status

    folder = Folder.objects.get(name=folder_name)
    perimeter = Perimeter.objects.get(name=perimeter_name, folder=folder)
    assessments = list(
        ComplianceAssessment.objects.filter(folder=folder, perimeter=perimeter).select_related(
            "framework", "framework__library"
        )
    )
    if len(assessments) < 1:
        raise SystemExit("no compliance assessments for program")

    requirements = []
    links: dict[str, list[str]] = {}
    leaf_by_assessment: list[list[str]] = []

    for ca in assessments:
        fw = ca.framework
        lib_ver = str(getattr(fw.library, "version", "") if fw.library_id else "")
        ras = list(
            RequirementAssessment.objects.filter(
                compliance_assessment=ca, requirement__assessable=True
            ).select_related("requirement")
        )
        leaf_ids = []
        for ra in ras:
            req = ra.requirement
            rid = str(req.id)
            leaf_ids.append(rid)
            requirements.append(
                {
                    "id": rid,
                    "framework_id": str(fw.id),
                    "framework_name": fw.name,
                    "framework_version": lib_ver,
                    "code": req.ref_id or req.urn or rid[:8],
                    "title": req.name or "",
                    "assessable": True,
                    "is_leaf": True,
                    "result": ra.result,
                }
            )
            ac_ids = [str(x) for x in ra.applied_controls.values_list("id", flat=True)]
            if ac_ids:
                links[rid] = ac_ids
        leaf_by_assessment.append(leaf_ids)

    implementations = []
    for ac in AppliedControl.objects.filter(folder=folder):
        owners = []
        if hasattr(ac, "owner"):
            owners = [str(o) for o in ac.owner.all()[:3]]
        open_tasks = 0
        try:
            if hasattr(ac, "task_templates"):
                open_tasks = TaskNode.objects.filter(
                    task_template__in=ac.task_templates.all(), status="pending"
                ).count()
        except Exception:
            open_tasks = 0
        implementations.append(
            {
                "id": str(ac.id),
                "ref_id": ac.ref_id or "",
                "name": ac.name,
                "canonical_control_id": str(ac.reference_control_id)
                if getattr(ac, "reference_control_id", None)
                else None,
                "canonical_control_ref": ac.ref_id or None,
                "status": map_ciso_applied_status(ac.status).value,
                "owner": owners[0] if owners else None,
                "due_date": ac.eta.isoformat() if ac.eta else None,
                "priority": f"P{ac.priority}" if ac.priority else None,
                "evidence_count": ac.evidences.count(),
                "open_task_count": open_tasks,
                "folder_id": str(folder.id),
            }
        )

    mappings = []
    if seed_phase2 and len(assessments) >= 3:
        # Demo overlay: map first leaves to shared AppliedControl refs with PARTIAL/SUPPORTING
        ac_three = AppliedControl.objects.filter(folder=folder, ref_id="CTRL-IAM-DEMO-3").first()
        ac_two = AppliedControl.objects.filter(folder=folder, ref_id="CTRL-IAM-DEMO-2").first()
        ac_triple_id = str(ac_three.id) if ac_three else None
        ac_dual_id = str(ac_two.id) if ac_two else None

        def _fw_meta(ca):
            fw = ca.framework
            return str(fw.id), fw.name, str(getattr(fw.library, "version", "") if fw.library_id else "")

        # Assessment A/B/C first requirement -> triple control
        for idx, relation, delta in [
            (0, "PARTIAL", "Annual privileged access review not evidenced"),
            (1, "PARTIAL", "Semi-annual privileged account review expected by NIS2-like baseline"),
            (2, "FULL", ""),
        ]:
            if idx >= len(assessments) or not leaf_by_assessment[idx]:
                continue
            rid = leaf_by_assessment[idx][0]
            ca = assessments[idx]
            fw_id, fw_name, fw_ver = _fw_meta(ca)
            req = next(r for r in requirements if r["id"] == rid)
            mappings.append(
                {
                    "requirement_id": rid,
                    "framework_id": fw_id,
                    "framework_name": fw_name,
                    "framework_version": fw_ver,
                    "requirement_code": req["code"],
                    "canonical_control_id": "canon-CTRL-IAM-DEMO-3",
                    "canonical_control_ref": "CTRL-IAM-DEMO-3",
                    "relation": relation,
                    "rationale": "WayFold Phase 2 demo mapping on shared AppliedControl",
                    "uncovered_delta": delta,
                    "review_status": "APPROVED",
                }
            )
            if ac_triple_id:
                links.setdefault(rid, [])
                if ac_triple_id not in links[rid]:
                    links[rid].append(ac_triple_id)

        # Dual framework mapping on second leaves of A+B
        for idx in (0, 1):
            if idx >= len(assessments) or len(leaf_by_assessment[idx]) < 2:
                continue
            rid = leaf_by_assessment[idx][1]
            ca = assessments[idx]
            fw_id, fw_name, fw_ver = _fw_meta(ca)
            req = next(r for r in requirements if r["id"] == rid)
            mappings.append(
                {
                    "requirement_id": rid,
                    "framework_id": fw_id,
                    "framework_name": fw_name,
                    "framework_version": fw_ver,
                    "requirement_code": req["code"],
                    "canonical_control_id": "canon-CTRL-IAM-DEMO-2",
                    "canonical_control_ref": "CTRL-IAM-DEMO-2",
                    "relation": "SUPPORTING" if idx == 1 else "FULL",
                    "rationale": "Dual-framework shared control",
                    "uncovered_delta": "Supporting only for Framework B leaf — sector specifics remain"
                    if idx == 1
                    else "",
                    "review_status": "APPROVED",
                }
            )
            if ac_dual_id:
                links.setdefault(rid, [])
                if ac_dual_id not in links[rid]:
                    links[rid].append(ac_dual_id)

        # Force at least two unmapped: clear links/maps for last leaf of each of first two FW if present
        # (leave requirements without mappings by not mapping leaves[2])
        # Ensure leaves index 2 exist and stay unmapped — already true if we only mapped 0 and 1.

    return {
        "tenant_id": str(folder.id),
        "tenant_name": folder.name,
        "program_id": str(perimeter.id),
        "program_name": perimeter.name,
        "requirements": requirements,
        "implementations": implementations,
        "mappings": mappings,
        "requirement_implementation_links": links,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--folder", default="Michele Demo")
    parser.add_argument("--perimeter", default="Cyber Compliance Demo")
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--seed-phase2-mappings", action="store_true")
    args = parser.parse_args(argv)

    # Allow importing engine when mounted beside /code
    here = Path(__file__).resolve().parents[1]
    if str(here) not in sys.path:
        sys.path.insert(0, str(here))

    data = export_program(args.folder, args.perimeter, seed_phase2=args.seed_phase2_mappings)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"Wrote {args.out} requirements={len(data['requirements'])} mappings={len(data['mappings'])}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
