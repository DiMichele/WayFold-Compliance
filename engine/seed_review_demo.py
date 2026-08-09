"""Deterministic, idempotent product-review demo dataset.

Marker: WF_REVIEW_DEMO_2026

Safe reset: only deletes/rewrites files under the review programs directory
and portfolio_registry entries pointing at those demo snapshots.
Never drops databases or truncates non-demo client data.

Usage:
  python -m engine.seed_review_demo
  python -m engine.seed_review_demo --write-fixtures
  python -m engine.seed_review_demo --data-dir /var/lib/wayfold-compliance
"""

from __future__ import annotations

import argparse
import json
import shutil
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from engine.runtime_paths import data_root

DATASET_MARKER = "WF_REVIEW_DEMO_2026"
SEED_VERSION = "2026.08.09-review-1"
PROGRAMS_SUBDIR = "programs"
REVIEW_FIXTURES = Path(__file__).resolve().parent / "fixtures" / "review"

PSNC_01_DELTA = (
    "È richiesta evidenza formale della revisione trimestrale "
    "degli accessi privilegiati per gli asset classificati critici."
)
NIS2_02_DELTA = (
    "La procedura implementata non documenta ancora "
    "tutte le tempistiche di escalation/notifica richieste."
)
PSNC_04_DELTA = (
    "Il test esistente non include ancora "
    "uno scenario specifico sul servizio critico."
)
NA_RATIONALE = (
    "Il controllo tecnico specifico è fuori dal perimetro "
    "del programma dimostrativo per il sistema legacy escluso dallo scope."
)


def _req(
    rid: str,
    fw_id: str,
    fw_name: str,
    fw_ver: str,
    code: str,
    title: str,
    *,
    result: str = "not_assessed",
) -> dict[str, Any]:
    return {
        "id": rid,
        "framework_id": fw_id,
        "framework_name": fw_name,
        "framework_version": fw_ver,
        "code": code,
        "title": title,
        "assessable": True,
        "is_leaf": True,
        "result": result,
    }


def _impl(
    iid: str,
    ref: str,
    name: str,
    status: str,
    *,
    owner: str | None = None,
    due: str | None = None,
    priority: str = "MEDIUM",
    evidence: int = 0,
    tasks: int = 0,
    folder: str,
    description: str = "",
    na_rationale: str = "",
    na_by: str | None = None,
    na_at: str | None = None,
) -> dict[str, Any]:
    return {
        "id": iid,
        "ref_id": ref,
        "name": name,
        "canonical_control_id": f"canon-{ref.lower()}",
        "canonical_control_ref": ref,
        "status": status,
        "owner": owner,
        "due_date": due,
        "priority": priority,
        "evidence_count": evidence,
        "open_task_count": tasks,
        "folder_id": folder,
        "description": description,
        "not_applicable_rationale": na_rationale,
        "not_applicable_approved_by": na_by,
        "not_applicable_approved_at": na_at,
    }


def _map(
    req_id: str,
    fw_id: str,
    fw_name: str,
    fw_ver: str,
    code: str,
    ctrl: str,
    relation: str,
    *,
    rationale: str = "",
    delta: str = "",
) -> dict[str, Any]:
    return {
        "requirement_id": req_id,
        "framework_id": fw_id,
        "framework_name": fw_name,
        "framework_version": fw_ver,
        "requirement_code": code,
        "canonical_control_id": f"canon-{ctrl.lower()}",
        "canonical_control_ref": ctrl,
        "relation": relation,
        "rationale": rationale
        or f"Il controllo {ctrl} copre il requisito {code} nel perimetro del programma.",
        "uncovered_delta": delta,
        "notes": "",
        "review_status": "APPROVED",
    }


def _ev(
    eid: str,
    title: str,
    filename: str,
    refs: list[str],
    *,
    status: str = "VALID",
    valid_until: str | None = None,
    review_by: str | None = None,
    notes: str = "",
) -> dict[str, Any]:
    return {
        "id": eid,
        "title": title,
        "filename": filename,
        "control_refs": refs,
        "status": status,
        "valid_until": valid_until,
        "review_by": review_by,
        "notes": notes,
    }


def _task(
    tid: str,
    title: str,
    ctrl: str | None,
    owner: str | None,
    status: str,
    *,
    due: str | None = None,
    priority: str = "MEDIUM",
    notes: str = "",
) -> dict[str, Any]:
    return {
        "id": tid,
        "title": title,
        "control_ref": ctrl,
        "owner": owner,
        "status": status,
        "due_date": due,
        "priority": priority,
        "notes": notes,
    }


def build_michele() -> dict[str, Any]:
    tenant = "tenant-michele-demo"
    iso = ("fw-iso27001-2022", "ISO/IEC 27001", "2022")
    nis2 = ("fw-nis2-it-2026-1", "NIS2 Italia", "2026.1")
    psnc = ("fw-psnc-2025-3", "PSNC", "2025.3")

    requirements = [
        _req("m-iso-a515", *iso, "ISO-A.5.15", "Principi di controllo degli accessi", result="partially_compliant"),
        _req("m-iso-a518", *iso, "ISO-A.5.18", "Revisione dei diritti di accesso", result="partially_compliant"),
        _req("m-iso-a524", *iso, "ISO-A.5.24", "Gestione degli incidenti di sicurezza", result="compliant"),
        _req("m-iso-a519", *iso, "ISO-A.5.19", "Sicurezza nei rapporti con i fornitori", result="non_compliant"),
        _req("m-iso-a815", *iso, "ISO-A.8.15", "Logging delle attività", result="partially_compliant"),
        _req("m-iso-a88", *iso, "ISO-A.8.8", "Gestione delle vulnerabilità tecniche", result="not_applicable"),
        # Hierarchy demo parent/child (parent non-leaf)
        {
            "id": "m-iso-iam-parent",
            "framework_id": iso[0],
            "framework_name": iso[1],
            "framework_version": iso[2],
            "code": "IAM",
            "title": "Identity and Access Management",
            "assessable": False,
            "is_leaf": False,
            "result": None,
        },
        {
            "id": "m-iso-iam-1",
            "framework_id": iso[0],
            "framework_name": iso[1],
            "framework_version": iso[2],
            "code": "IAM.1",
            "title": "Privileged access domain",
            "assessable": False,
            "is_leaf": False,
            "result": None,
        },
        _req("m-nis2-01", *nis2, "NIS2-01", "Governance degli accessi privilegiati", result="partially_compliant"),
        _req("m-nis2-02", *nis2, "NIS2-02", "Gestione e classificazione degli incidenti", result="partially_compliant"),
        _req("m-nis2-03", *nis2, "NIS2-03", "Sicurezza della supply chain", result="non_compliant"),
        _req("m-nis2-04", *nis2, "NIS2-04", "Continuità operativa", result="compliant"),
        _req("m-nis2-05", *nis2, "NIS2-05", "Risk management cyber", result="compliant"),
        _req("m-nis2-06", *nis2, "NIS2-06", "Gestione delle vulnerabilità", result="not_applicable"),
        _req("m-psnc-01", *psnc, "PSNC-01", "Revisione periodica degli accessi privilegiati sui sistemi critici", result="partially_compliant"),
        _req("m-psnc-02", *psnc, "PSNC-02", "Logging e conservazione degli eventi", result="partially_compliant"),
        _req("m-psnc-03", *psnc, "PSNC-03", "Gestione degli incidenti critici", result="compliant"),
        _req("m-psnc-04", *psnc, "PSNC-04", "Test periodici di continuità sui sistemi critici", result="partially_compliant"),
        _req("m-psnc-05", *psnc, "PSNC-05", "Protezione crittografica delle informazioni critiche", result="non_compliant"),
        _req("m-psnc-06", *psnc, "PSNC-06", "Requisito operativo specifico non ancora mappato", result="not_assessed"),
        _req("m-psnc-sup", *psnc, "PSNC-SUP", "Clausole di sicurezza supply chain (supporto)", result="not_assessed"),
    ]

    implementations = [
        _impl(
            "m-impl-iam",
            "CTRL-IAM-001",
            "Gestione degli accessi privilegiati",
            "IN_PROGRESS",
            owner="Luca Rinaldi",
            due="2026-08-07",
            priority="HIGH",
            evidence=3,
            tasks=1,
            folder=tenant,
            description=(
                "PAM centralizzato per gli account amministrativi di dominio "
                "e per le principali piattaforme cloud. MFA attiva. "
                "È in corso la formalizzazione della recertificazione "
                "trimestrale sugli asset critici."
            ),
        ),
        _impl(
            "m-impl-ir",
            "CTRL-IR-001",
            "Classificazione e gestione degli incidenti",
            "IMPLEMENTED",
            owner="Sara Moretti",
            priority="HIGH",
            evidence=2,
            tasks=1,
            folder=tenant,
            description=(
                "Processo di incident management formalizzato, "
                "con classificazione della severità, escalation interna "
                "e registro degli incidenti."
            ),
        ),
        _impl(
            "m-impl-sup",
            "CTRL-SUP-001",
            "Due diligence di sicurezza dei fornitori",
            "NOT_IMPLEMENTED",
            owner="Sara Bianchi",
            due="2026-08-18",
            priority="HIGH",
            evidence=1,
            tasks=1,
            folder=tenant,
            description=(
                "Sono presenti clausole contrattuali di sicurezza, "
                "ma non esiste ancora una procedura uniforme "
                "di due diligence periodica per i fornitori critici."
            ),
        ),
        _impl(
            "m-impl-bcp",
            "CTRL-BCP-001",
            "Test di continuità operativa",
            "IMPLEMENTED",
            owner="Marco Conti",
            priority="MEDIUM",
            evidence=1,
            tasks=1,
            folder=tenant,
            description=(
                "Business Continuity Plan formalizzato e testato annualmente. "
                "Rimane da includere uno scenario specifico per alcuni sistemi critici."
            ),
        ),
        _impl(
            "m-impl-log",
            "CTRL-LOG-001",
            "Logging e monitoraggio centralizzato",
            "IN_PROGRESS",
            owner="Luca Rinaldi",
            due="2026-08-25",
            priority="MEDIUM",
            evidence=1,
            tasks=1,
            folder=tenant,
            description="SIEM centralizzato in corso di allineamento retention.",
        ),
        _impl(
            "m-impl-gov",
            "CTRL-GOV-001",
            "Governance del rischio cyber",
            "IMPLEMENTED",
            owner="Michele Ferri",
            priority="MEDIUM",
            evidence=1,
            tasks=0,
            folder=tenant,
            description="Comitato rischio cyber e policy di governance aggiornate.",
        ),
        _impl(
            "m-impl-vuln",
            "CTRL-VULN-001",
            "Gestione delle vulnerabilità",
            "NOT_APPLICABLE",
            owner="Luca Rinaldi",
            priority="LOW",
            evidence=0,
            tasks=0,
            folder=tenant,
            description="Escluso dallo scope dimostrativo.",
            na_rationale=NA_RATIONALE,
            na_by="admin",
            na_at="2026-08-09",
        ),
        _impl(
            "m-impl-enc",
            "CTRL-ENC-001",
            "Protezione crittografica dei dati",
            "NOT_IMPLEMENTED",
            owner="Luca Rinaldi",
            due="2026-09-15",
            priority="HIGH",
            evidence=0,
            tasks=1,
            folder=tenant,
            description="Standard crittografico per dataset critici da definire.",
        ),
    ]

    mappings = [
        _map("m-iso-a515", *iso, "ISO-A.5.15", "CTRL-IAM-001", "FULL"),
        _map("m-iso-a518", *iso, "ISO-A.5.18", "CTRL-IAM-001", "FULL"),
        _map("m-nis2-01", *nis2, "NIS2-01", "CTRL-IAM-001", "FULL"),
        _map("m-psnc-01", *psnc, "PSNC-01", "CTRL-IAM-001", "PARTIAL", delta=PSNC_01_DELTA),
        _map("m-iso-a524", *iso, "ISO-A.5.24", "CTRL-IR-001", "FULL"),
        _map("m-nis2-02", *nis2, "NIS2-02", "CTRL-IR-001", "PARTIAL", delta=NIS2_02_DELTA),
        _map("m-psnc-03", *psnc, "PSNC-03", "CTRL-IR-001", "FULL"),
        _map("m-iso-a519", *iso, "ISO-A.5.19", "CTRL-SUP-001", "FULL"),
        _map("m-nis2-03", *nis2, "NIS2-03", "CTRL-SUP-001", "FULL"),
        _map("m-psnc-sup", *psnc, "PSNC-SUP", "CTRL-SUP-001", "SUPPORTING", rationale="Supporto documentale alle clausole PSNC"),
        _map("m-nis2-04", *nis2, "NIS2-04", "CTRL-BCP-001", "FULL"),
        _map("m-psnc-04", *psnc, "PSNC-04", "CTRL-BCP-001", "PARTIAL", delta=PSNC_04_DELTA),
        _map("m-iso-a815", *iso, "ISO-A.8.15", "CTRL-LOG-001", "FULL"),
        _map("m-psnc-02", *psnc, "PSNC-02", "CTRL-LOG-001", "FULL"),
        _map("m-nis2-05", *nis2, "NIS2-05", "CTRL-GOV-001", "FULL"),
        _map("m-iso-a88", *iso, "ISO-A.8.8", "CTRL-VULN-001", "FULL"),
        _map("m-nis2-06", *nis2, "NIS2-06", "CTRL-VULN-001", "FULL"),
        _map("m-psnc-05", *psnc, "PSNC-05", "CTRL-ENC-001", "FULL"),
    ]

    links = {
        "m-iso-a515": ["m-impl-iam"],
        "m-iso-a518": ["m-impl-iam"],
        "m-nis2-01": ["m-impl-iam"],
        "m-psnc-01": ["m-impl-iam"],
        "m-iso-a524": ["m-impl-ir"],
        "m-nis2-02": ["m-impl-ir"],
        "m-psnc-03": ["m-impl-ir"],
        "m-iso-a519": ["m-impl-sup"],
        "m-nis2-03": ["m-impl-sup"],
        "m-psnc-sup": ["m-impl-sup"],
        "m-nis2-04": ["m-impl-bcp"],
        "m-psnc-04": ["m-impl-bcp"],
        "m-iso-a815": ["m-impl-log"],
        "m-psnc-02": ["m-impl-log"],
        "m-nis2-05": ["m-impl-gov"],
        "m-iso-a88": ["m-impl-vuln"],
        "m-nis2-06": ["m-impl-vuln"],
        "m-psnc-05": ["m-impl-enc"],
    }

    evidences = [
        _ev("EV-001", "Access Control Policy v4", "Access Control Policy v4.pdf", ["CTRL-IAM-001", "CTRL-GOV-001"], valid_until="2027-08-01"),
        _ev("EV-002", "PAM Configuration Export", "PAM Configuration Export.json", ["CTRL-IAM-001"], status="EXPIRING", review_by="2026-08-31"),
        _ev(
            "EV-003",
            "Q2 Privileged Access Review",
            "Q2 Privileged Access Review.csv",
            ["CTRL-IAM-001"],
            status="PARTIAL",
            notes="non include subset asset critici",
        ),
        _ev("EV-004", "Incident Response Plan v3", "Incident Response Plan v3.pdf", ["CTRL-IR-001", "CTRL-BCP-001"], valid_until="2027-01-15"),
        _ev("EV-005", "Incident Exercise Report", "Incident Exercise Report.pdf", ["CTRL-IR-001"], valid_until="2026-12-01"),
        _ev("EV-006", "BCP Exercise Report 2026", "BCP Exercise Report 2026.pdf", ["CTRL-BCP-001"], valid_until="2027-03-01"),
        _ev("EV-007", "SIEM Retention Configuration", "SIEM Retention Configuration.txt", ["CTRL-LOG-001"], status="REVIEW_REQUIRED", review_by="2026-08-25"),
        _ev("EV-008", "Supplier Security Procedure Draft", "Supplier Security Procedure Draft.pdf", ["CTRL-SUP-001"], status="PARTIAL"),
    ]

    tasks = [
        _task("TASK-001", "Completare recertificazione accessi privilegiati sugli asset critici", "CTRL-IAM-001", "Luca Rinaldi", "IN_PROGRESS", due="2026-08-07", priority="HIGH"),
        _task("TASK-002", "Formalizzare processo di due diligence fornitori", "CTRL-SUP-001", "Sara Bianchi", "TODO", due="2026-08-18", priority="HIGH"),
        _task("TASK-003", "Integrare tempistiche regolatorie nella matrice incidenti", "CTRL-IR-001", "Sara Moretti", "REVIEW", due="2026-08-20", priority="MEDIUM"),
        _task("TASK-004", "Aggiornare scenario BCP per sistema critico", "CTRL-BCP-001", "Marco Conti", "TODO", due="2026-08-29", priority="MEDIUM"),
        _task("TASK-005", "Validare retention SIEM", "CTRL-LOG-001", "Luca Rinaldi", "IN_PROGRESS", due="2026-08-25", priority="MEDIUM"),
        _task("TASK-006", "Aggiornare policy di governance", "CTRL-GOV-001", "Michele Ferri", "DONE", due="2026-07-15", priority="LOW"),
        _task("TASK-007", "Definire standard crittografico per dataset critici", "CTRL-ENC-001", "Luca Rinaldi", "TODO", due="2026-09-15", priority="HIGH"),
        _task("TASK-008", "Analizzare requirement PSNC-06 non mappato", None, "Michele Ferri", "TODO", due="2026-09-01", priority="MEDIUM", notes="Knowledge Base / mapping"),
    ]

    return {
        "tenant_id": tenant,
        "tenant_name": "Michele S.r.l. [Demo]",
        "program_id": "program-michele-cyber-2026",
        "program_name": "Cyber Compliance 2026",
        "scope": "Corporate IT + servizi critici",
        "program_status": "ACTIVE",
        "dataset_marker": DATASET_MARKER,
        "seed_version": SEED_VERSION,
        "requirements": requirements,
        "implementations": implementations,
        "mappings": mappings,
        "requirement_implementation_links": links,
        "evidences": evidences,
        "tasks": tasks,
        "available_framework_versions": [
            {
                "framework_id": nis2[0],
                "framework_name": nis2[1],
                "framework_version": "2026.2",
                "version": "2026.2",
                "status": "DRAFT",
                "assigned_to_program": False,
                "notes": "Nuova versione disponibile — programma pinned a 2026.1",
            },
            {
                "framework_id": nis2[0],
                "framework_name": nis2[1],
                "framework_version": nis2[2],
                "version": nis2[2],
                "status": "PUBLISHED",
                "assigned_to_program": True,
            },
        ],
    }


def _simple_client(
    *,
    tenant_id: str,
    tenant_name: str,
    program_id: str,
    program_name: str,
    scope: str,
    frameworks: list[tuple[str, str, str]],
    controls: list[dict[str, Any]],
    requirements: list[dict[str, Any]],
    mappings: list[dict[str, Any]],
    evidences: list[dict[str, Any]],
    tasks: list[dict[str, Any]],
    links: dict[str, list[str]],
) -> dict[str, Any]:
    return {
        "tenant_id": tenant_id,
        "tenant_name": tenant_name,
        "program_id": program_id,
        "program_name": program_name,
        "scope": scope,
        "program_status": "ACTIVE",
        "dataset_marker": DATASET_MARKER,
        "seed_version": SEED_VERSION,
        "requirements": requirements,
        "implementations": controls,
        "mappings": mappings,
        "requirement_implementation_links": links,
        "evidences": evidences,
        "tasks": tasks,
        "available_framework_versions": [],
    }


def build_alfa() -> dict[str, Any]:
    tenant = "tenant-alfa-demo"
    qc4 = ("fw-qc4-2025", "QC4 / Cloud Regulation", "2025.1")
    iso = ("fw-iso27001-2022", "ISO/IEC 27001", "2022")
    controls = [
        _impl("a-impl-iam", "CTRL-IAM-001", "Gestione accessi cloud", "IMPLEMENTED", owner="Ops Alfa", evidence=2, folder=tenant, priority="HIGH"),
        _impl("a-impl-log", "CTRL-LOG-001", "Logging cloud", "IMPLEMENTED", owner="Sec Alfa", evidence=2, folder=tenant),
        _impl("a-impl-enc", "CTRL-ENC-001", "Crittografia at-rest", "IMPLEMENTED", owner="Sec Alfa", evidence=1, folder=tenant),
        _impl("a-impl-ir", "CTRL-IR-001", "Incident cloud", "IMPLEMENTED", owner="Sec Alfa", evidence=1, folder=tenant),
        _impl("a-impl-gov", "CTRL-GOV-001", "Governance cloud", "IN_PROGRESS", owner="CISO Alfa", due="2026-08-28", evidence=1, tasks=1, folder=tenant, priority="HIGH"),
        _impl("a-impl-sup", "CTRL-SUP-001", "Fornitori cloud", "IMPLEMENTED", owner="Proc Alfa", evidence=1, folder=tenant),
    ]
    reqs = [
        _req("a-qc4-01", *qc4, "QC4-01", "Identity federation", result="compliant"),
        _req("a-qc4-02", *qc4, "QC4-02", "Logging & monitoring", result="compliant"),
        _req("a-qc4-03", *qc4, "QC4-03", "Encryption baseline", result="compliant"),
        _req("a-qc4-99", *qc4, "QC4-99", "Sector residual clause", result="not_assessed"),
        _req("a-iso-01", *iso, "ISO-A.5.15", "Access control", result="compliant"),
        _req("a-iso-02", *iso, "ISO-A.8.15", "Logging", result="compliant"),
        _req("a-iso-03", *iso, "ISO-A.5.24", "Incidents", result="compliant"),
    ]
    maps = [
        _map("a-qc4-01", *qc4, "QC4-01", "CTRL-IAM-001", "FULL"),
        _map("a-qc4-02", *qc4, "QC4-02", "CTRL-LOG-001", "FULL"),
        _map("a-qc4-03", *qc4, "QC4-03", "CTRL-ENC-001", "FULL"),
        _map("a-iso-01", *iso, "ISO-A.5.15", "CTRL-IAM-001", "FULL"),
        _map("a-iso-02", *iso, "ISO-A.8.15", "CTRL-LOG-001", "FULL"),
        _map("a-iso-03", *iso, "ISO-A.5.24", "CTRL-IR-001", "FULL"),
    ]
    links = {r["id"]: [c["id"]] for r, c in [
        (reqs[0], controls[0]), (reqs[1], controls[1]), (reqs[2], controls[2]),
        (reqs[4], controls[0]), (reqs[5], controls[1]), (reqs[6], controls[3]),
    ]}
    return _simple_client(
        tenant_id=tenant,
        tenant_name="Alfa Cloud S.p.A. [Demo]",
        program_id="program-alfa-cloud-2026",
        program_name="Cloud Qualification 2026",
        scope="Public cloud qualification",
        frameworks=[qc4, iso],
        controls=controls,
        requirements=reqs,
        mappings=maps,
        evidences=[
            _ev("A-EV-001", "Cloud IAM Design", "Cloud IAM Design.pdf", ["CTRL-IAM-001"], valid_until="2027-06-01"),
            _ev("A-EV-002", "SIEM Pack", "SIEM Pack.pdf", ["CTRL-LOG-001"], status="REVIEW_REQUIRED", review_by="2026-08-20"),
            _ev("A-EV-003", "Encryption Standard", "Encryption Standard.pdf", ["CTRL-ENC-001"]),
        ],
        tasks=[
            _task("A-TASK-001", "Chiudere gap governance cloud", "CTRL-GOV-001", "CISO Alfa", "IN_PROGRESS", due="2026-08-28", priority="HIGH"),
            _task("A-TASK-002", "Revisionare evidenza SIEM", "CTRL-LOG-001", "Sec Alfa", "REVIEW", due="2026-08-20"),
        ],
        links=links,
    )


def build_beta() -> dict[str, Any]:
    tenant = "tenant-beta-demo"
    dora = ("fw-dora-2025", "DORA", "2025.1")
    nis2 = ("fw-nis2-it-2026-1", "NIS2 Italia", "2026.1")
    controls = [
        _impl("b-impl-iam", "CTRL-IAM-001", "PAM finance", "NOT_IMPLEMENTED", owner="IAM Beta", due="2026-08-05", evidence=0, tasks=1, folder=tenant, priority="CRITICAL"),
        _impl("b-impl-ir", "CTRL-IR-001", "Incident ICT", "IN_PROGRESS", owner="SOC Beta", due="2026-08-06", evidence=1, tasks=1, folder=tenant, priority="HIGH"),
        _impl("b-impl-bcp", "CTRL-BCP-001", "ICT continuity", "NOT_IMPLEMENTED", owner="BCM Beta", due="2026-08-08", evidence=0, tasks=1, folder=tenant, priority="HIGH"),
        _impl("b-impl-sup", "CTRL-SUP-001", "ICT third parties", "NOT_IMPLEMENTED", owner="Proc Beta", due="2026-08-12", evidence=0, tasks=1, folder=tenant, priority="HIGH"),
        _impl("b-impl-gov", "CTRL-GOV-001", "ICT risk governance", "IN_PROGRESS", owner="CRO Beta", due="2026-08-22", evidence=1, tasks=1, folder=tenant),
        _impl("b-impl-log", "CTRL-LOG-001", "Monitoring ICT", "IN_PROGRESS", owner="SOC Beta", evidence=1, tasks=0, folder=tenant),
    ]
    reqs = [
        _req("b-dora-01", *dora, "DORA-01", "ICT risk management", result="non_compliant"),
        _req("b-dora-02", *dora, "DORA-02", "Incident management", result="partially_compliant"),
        _req("b-dora-03", *dora, "DORA-03", "Business continuity", result="non_compliant"),
        _req("b-dora-04", *dora, "DORA-04", "Third-party risk", result="non_compliant"),
        _req("b-nis2-01", *nis2, "NIS2-01", "Privileged access", result="non_compliant"),
        _req("b-nis2-02", *nis2, "NIS2-04", "Continuity", result="non_compliant"),
        _req("b-nis2-99", *nis2, "NIS2-X", "Reporting channel", result="not_assessed"),
    ]
    maps = [
        _map("b-dora-01", *dora, "DORA-01", "CTRL-GOV-001", "PARTIAL", delta="Manca formalizzazione board reporting DORA"),
        _map("b-dora-02", *dora, "DORA-02", "CTRL-IR-001", "PARTIAL", delta="Tempistiche DORA non complete"),
        _map("b-dora-03", *dora, "DORA-03", "CTRL-BCP-001", "FULL"),
        _map("b-dora-04", *dora, "DORA-04", "CTRL-SUP-001", "FULL"),
        _map("b-nis2-01", *nis2, "NIS2-01", "CTRL-IAM-001", "FULL"),
        _map("b-nis2-02", *nis2, "NIS2-04", "CTRL-BCP-001", "FULL"),
    ]
    links = {
        "b-dora-01": ["b-impl-gov"],
        "b-dora-02": ["b-impl-ir"],
        "b-dora-03": ["b-impl-bcp"],
        "b-dora-04": ["b-impl-sup"],
        "b-nis2-01": ["b-impl-iam"],
        "b-nis2-02": ["b-impl-bcp"],
    }
    return _simple_client(
        tenant_id=tenant,
        tenant_name="Beta Finance S.p.A. [Demo]",
        program_id="program-beta-ict-2026",
        program_name="ICT Resilience 2026",
        scope="ICT services essenziali",
        frameworks=[dora, nis2],
        controls=controls,
        requirements=reqs,
        mappings=maps,
        evidences=[
            _ev("B-EV-001", "Incident Runbook Draft", "Incident Runbook Draft.pdf", ["CTRL-IR-001"], status="PARTIAL"),
            _ev("B-EV-002", "Risk Register Extract", "Risk Register Extract.csv", ["CTRL-GOV-001"], status="REVIEW_REQUIRED"),
        ],
        tasks=[
            _task("B-TASK-001", "Attivare PAM sui sistemi critici", "CTRL-IAM-001", "IAM Beta", "TODO", due="2026-08-05", priority="CRITICAL"),
            _task("B-TASK-002", "Chiudere gap incident DORA", "CTRL-IR-001", "SOC Beta", "IN_PROGRESS", due="2026-08-06", priority="HIGH"),
            _task("B-TASK-003", "Eseguire test BCP ICT", "CTRL-BCP-001", "BCM Beta", "TODO", due="2026-08-08", priority="HIGH"),
            _task("B-TASK-004", "Due diligence fornitori ICT", "CTRL-SUP-001", "Proc Beta", "TODO", due="2026-08-12", priority="HIGH"),
        ],
        links=links,
    )


def build_nova() -> dict[str, Any]:
    tenant = "tenant-nova-demo"
    ai_act = ("fw-aiact-2026", "AI Act", "2026.1")
    iso42001 = ("fw-iso42001-2023", "ISO/IEC 42001", "2023")
    nis2 = ("fw-nis2-it-2026-1", "NIS2 Italia", "2026.1")
    controls = [
        _impl("n-impl-gov", "CTRL-GOV-001", "AI risk governance", "IMPLEMENTED", owner="AI Lead Nova", evidence=2, folder=tenant),
        _impl("n-impl-iam", "CTRL-IAM-001", "Accesso modelli AI", "IN_PROGRESS", owner="Sec Nova", due="2026-08-30", evidence=1, tasks=1, folder=tenant),
        _impl("n-impl-log", "CTRL-LOG-001", "Logging decisioni AI", "IN_PROGRESS", owner="Sec Nova", due="2026-09-10", evidence=1, tasks=1, folder=tenant),
        _impl("n-impl-ir", "CTRL-IR-001", "Incident AI security", "IMPLEMENTED", owner="Sec Nova", evidence=1, folder=tenant),
        _impl("n-impl-sup", "CTRL-SUP-001", "Fornitori modelli", "NOT_IMPLEMENTED", owner="Proc Nova", due="2026-09-05", evidence=0, tasks=1, folder=tenant, priority="HIGH"),
    ]
    reqs = [
        _req("n-ai-01", *ai_act, "AIA-01", "Risk management system", result="compliant"),
        _req("n-ai-02", *ai_act, "AIA-02", "Human oversight / access", result="partially_compliant"),
        _req("n-ai-03", *ai_act, "AIA-03", "Logging of high-risk AI", result="partially_compliant"),
        _req("n-420-01", *iso42001, "42001-5.2", "AI policy", result="compliant"),
        _req("n-420-02", *iso42001, "42001-8.2", "AI risk assessment", result="compliant"),
        _req("n-nis2-01", *nis2, "NIS2-01", "Privileged access", result="partially_compliant"),
        _req("n-nis2-03", *nis2, "NIS2-03", "Supply chain", result="non_compliant"),
    ]
    maps = [
        _map("n-ai-01", *ai_act, "AIA-01", "CTRL-GOV-001", "FULL"),
        _map("n-ai-02", *ai_act, "AIA-02", "CTRL-IAM-001", "PARTIAL", delta="Manca matrice oversight per modelli high-risk"),
        _map("n-ai-03", *ai_act, "AIA-03", "CTRL-LOG-001", "PARTIAL", delta="Retention logging AI non allineata"),
        _map("n-420-01", *iso42001, "42001-5.2", "CTRL-GOV-001", "FULL"),
        _map("n-420-02", *iso42001, "42001-8.2", "CTRL-GOV-001", "FULL"),
        _map("n-nis2-01", *nis2, "NIS2-01", "CTRL-IAM-001", "FULL"),
        _map("n-nis2-03", *nis2, "NIS2-03", "CTRL-SUP-001", "FULL"),
    ]
    links = {
        "n-ai-01": ["n-impl-gov"],
        "n-ai-02": ["n-impl-iam"],
        "n-ai-03": ["n-impl-log"],
        "n-420-01": ["n-impl-gov"],
        "n-420-02": ["n-impl-gov"],
        "n-nis2-01": ["n-impl-iam"],
        "n-nis2-03": ["n-impl-sup"],
    }
    return _simple_client(
        tenant_id=tenant,
        tenant_name="Nova Health S.r.l. [Demo]",
        program_id="program-nova-ai-2026",
        program_name="AI Governance & Security 2026",
        scope="AI systems in ambito sanitario (demo)",
        frameworks=[ai_act, iso42001, nis2],
        controls=controls,
        requirements=reqs,
        mappings=maps,
        evidences=[
            _ev("N-EV-001", "AI Policy Pack", "AI Policy Pack.pdf", ["CTRL-GOV-001"]),
            _ev("N-EV-002", "Model Access Matrix", "Model Access Matrix.xlsx", ["CTRL-IAM-001"], status="PARTIAL"),
            _ev("N-EV-003", "AI Logging Spec", "AI Logging Spec.pdf", ["CTRL-LOG-001"]),
        ],
        tasks=[
            _task("N-TASK-001", "Completare oversight accessi modelli", "CTRL-IAM-001", "Sec Nova", "IN_PROGRESS", due="2026-08-30"),
            _task("N-TASK-002", "Allineare retention log AI", "CTRL-LOG-001", "Sec Nova", "TODO", due="2026-09-10"),
            _task("N-TASK-003", "Due diligence fornitori modelli", "CTRL-SUP-001", "Proc Nova", "TODO", due="2026-09-05", priority="HIGH"),
        ],
        links=links,
    )


def build_delta() -> dict[str, Any]:
    tenant = "tenant-delta-demo"
    ccm = ("fw-ccm-v4", "CSA STAR / CCM", "4.0")
    iso = ("fw-iso27001-2022", "ISO/IEC 27001", "2022")
    controls = [
        _impl("d-impl-iam", "CTRL-IAM-001", "CCM IAM", "IMPLEMENTED", owner="Sec Delta", evidence=2, folder=tenant),
        _impl("d-impl-log", "CTRL-LOG-001", "CCM Logging", "IMPLEMENTED", owner="Sec Delta", evidence=1, folder=tenant),
        _impl("d-impl-enc", "CTRL-ENC-001", "CCM Encryption", "IMPLEMENTED", owner="Sec Delta", evidence=1, folder=tenant),
        _impl("d-impl-ir", "CTRL-IR-001", "CCM Incident", "IN_PROGRESS", owner="Sec Delta", due="2026-09-01", evidence=1, tasks=1, folder=tenant),
        _impl("d-impl-bcp", "CTRL-BCP-001", "CCM Continuity", "IMPLEMENTED", owner="BCM Delta", evidence=1, folder=tenant),
        _impl("d-impl-sup", "CTRL-SUP-001", "CCM Supply", "IN_PROGRESS", owner="Proc Delta", due="2026-08-27", evidence=1, tasks=1, folder=tenant),
    ]
    reqs = [
        _req("d-ccm-01", *ccm, "CCM-IAM-01", "Identity management", result="compliant"),
        _req("d-ccm-02", *ccm, "CCM-LOG-01", "Logging", result="compliant"),
        _req("d-ccm-03", *ccm, "CCM-ENC-01", "Encryption", result="compliant"),
        _req("d-ccm-04", *ccm, "CCM-IR-01", "Incident response", result="partially_compliant"),
        _req("d-iso-01", *iso, "ISO-A.5.15", "Access control", result="compliant"),
        _req("d-iso-02", *iso, "ISO-A.5.24", "Incidents", result="partially_compliant"),
        _req("d-iso-99", *iso, "ISO-X", "Residual requirement", result="not_assessed"),
    ]
    maps = [
        _map("d-ccm-01", *ccm, "CCM-IAM-01", "CTRL-IAM-001", "FULL"),
        _map("d-ccm-02", *ccm, "CCM-LOG-01", "CTRL-LOG-001", "FULL"),
        _map("d-ccm-03", *ccm, "CCM-ENC-01", "CTRL-ENC-001", "FULL"),
        _map("d-ccm-04", *ccm, "CCM-IR-01", "CTRL-IR-001", "PARTIAL", delta="Manca tabletop exercise annuale CCM"),
        _map("d-iso-01", *iso, "ISO-A.5.15", "CTRL-IAM-001", "FULL"),
        _map("d-iso-02", *iso, "ISO-A.5.24", "CTRL-IR-001", "FULL"),
    ]
    links = {
        "d-ccm-01": ["d-impl-iam"],
        "d-ccm-02": ["d-impl-log"],
        "d-ccm-03": ["d-impl-enc"],
        "d-ccm-04": ["d-impl-ir"],
        "d-iso-01": ["d-impl-iam"],
        "d-iso-02": ["d-impl-ir"],
    }
    return _simple_client(
        tenant_id=tenant,
        tenant_name="Delta Services S.p.A. [Demo]",
        program_id="program-delta-cloud-2026",
        program_name="Cloud Security Assurance 2026",
        scope="Managed cloud services",
        frameworks=[ccm, iso],
        controls=controls,
        requirements=reqs,
        mappings=maps,
        evidences=[
            _ev("D-EV-001", "CCM IAM Evidence Pack", "CCM IAM Evidence Pack.pdf", ["CTRL-IAM-001"]),
            _ev("D-EV-002", "Encryption Config", "Encryption Config.json", ["CTRL-ENC-001"]),
            _ev("D-EV-003", "IR Playbook", "IR Playbook.pdf", ["CTRL-IR-001"], status="REVIEW_REQUIRED"),
        ],
        tasks=[
            _task("D-TASK-001", "Eseguire tabletop CCM IR", "CTRL-IR-001", "Sec Delta", "TODO", due="2026-09-01"),
            _task("D-TASK-002", "Chiudere gap supply CCM", "CTRL-SUP-001", "Proc Delta", "IN_PROGRESS", due="2026-08-27"),
        ],
        links=links,
    )


PROGRAM_BUILDERS: list[tuple[str, Any]] = [
    ("michele_cyber_2026.json", build_michele),
    ("alfa_cloud_2026.json", build_alfa),
    ("beta_finance_2026.json", build_beta),
    ("nova_health_2026.json", build_nova),
    ("delta_services_2026.json", build_delta),
]


def build_all_programs() -> dict[str, dict[str, Any]]:
    return {name: builder() for name, builder in PROGRAM_BUILDERS}


def _write_json(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def write_fixtures(out_dir: Path | None = None) -> list[Path]:
    out_dir = out_dir or REVIEW_FIXTURES
    written: list[Path] = []
    for name, data in build_all_programs().items():
        path = out_dir / name
        _write_json(path, data)
        written.append(path)
    registry = {
        "dataset_marker": DATASET_MARKER,
        "seed_version": SEED_VERSION,
        "programs": [
            {"snapshot": name, "last_activity": "2026-08-09", "dataset_marker": DATASET_MARKER}
            for name, _ in PROGRAM_BUILDERS
        ],
    }
    reg_path = out_dir / "portfolio_registry.json"
    _write_json(reg_path, registry)
    written.append(reg_path)
    return written


def _safe_clear_demo_programs(programs_dir: Path, registry_path: Path) -> None:
    """Remove only previous demo program files and demo registry entries."""
    if programs_dir.is_dir():
        for path in programs_dir.glob("*.json"):
            try:
                raw = json.loads(path.read_text(encoding="utf-8"))
            except Exception:  # noqa: BLE001
                continue
            if raw.get("dataset_marker") == DATASET_MARKER or "[Demo]" in str(
                raw.get("tenant_name", "")
            ):
                path.unlink(missing_ok=True)
    if registry_path.is_file():
        try:
            reg = json.loads(registry_path.read_text(encoding="utf-8"))
        except Exception:  # noqa: BLE001
            reg = {"programs": []}
        kept = []
        for entry in reg.get("programs", []):
            snap = str(entry.get("snapshot") or "")
            marker = entry.get("dataset_marker")
            if marker == DATASET_MARKER:
                continue
            # Drop entries that resolve to demo snapshots under programs/
            snap_path = Path(snap)
            if not snap_path.is_file():
                snap_path = programs_dir / Path(snap).name
            if snap_path.is_file():
                try:
                    raw = json.loads(snap_path.read_text(encoding="utf-8"))
                    if raw.get("dataset_marker") == DATASET_MARKER:
                        continue
                except Exception:  # noqa: BLE001
                    pass
            if DATASET_MARKER in snap or snap.endswith(
                tuple(n for n, _ in PROGRAM_BUILDERS)
            ):
                # Prefer keeping non-demo absolute/other paths
                if programs_dir.name in snap.replace("\\", "/"):
                    continue
            kept.append(entry)
        reg["programs"] = kept
        _write_json(registry_path, reg)


def install_to_data_dir(target: Path | None = None) -> dict[str, Any]:
    """Install review dataset into writable data dir (production/local)."""
    root = target or data_root()
    programs_dir = root / PROGRAMS_SUBDIR
    registry_path = root / "portfolio_registry.json"
    programs_dir.mkdir(parents=True, exist_ok=True)
    _safe_clear_demo_programs(programs_dir, registry_path)

    # Prefer versioned fixtures (already in image). Fall back to in-memory build
    # when fixtures are missing (e.g. fresh checkout). Never require writing to
    # the app tree — production mounts /app read-only.
    programs = build_all_programs()
    installed: list[str] = []
    for name, _ in PROGRAM_BUILDERS:
        dst = programs_dir / name
        src = REVIEW_FIXTURES / name
        if src.is_file():
            shutil.copy2(src, dst)
        else:
            _write_json(dst, programs[name])
        installed.append(name)

    # Merge demo registry entries with any preserved non-demo programs
    if registry_path.is_file():
        reg = json.loads(registry_path.read_text(encoding="utf-8"))
    else:
        reg = {"programs": []}
    existing = list(reg.get("programs") or [])
    demo_entries = [
        {
            "snapshot": f"{PROGRAMS_SUBDIR}/{name}",
            "last_activity": "2026-08-09",
            "dataset_marker": DATASET_MARKER,
        }
        for name, _ in PROGRAM_BUILDERS
    ]
    reg = {
        "dataset_marker": DATASET_MARKER,
        "seed_version": SEED_VERSION,
        "programs": existing + demo_entries,
    }
    _write_json(registry_path, reg)

    # Regulatory demo sources (engine store under same data root)
    try:
        from engine.regulatory.demo import run_demo_change_cycle, seed_demo_source
        from engine.regulatory.domain import Source, SourceType
        from engine.regulatory.store import RegulatoryStore

        store = RegulatoryStore(root=root / "regulatory")
        seed_demo_source(store)
        run_demo_change_cycle(store)
        for src in (
            Source(
                id="src-acn-cloud-demo",
                title="ACN Cloud Qualification [Demo]",
                url="fixture://demo-nis2/v1.html",
                publisher="ACN",
                type=SourceType.HTML,
                language="it",
                official=True,
                monitoring_enabled=True,
                check_frequency_hours=24,
                notes=DATASET_MARKER,
                linked_framework_ids=["fw-qc4-2025"],
                linked_framework_versions=["2025.1"],
                linked_requirement_ids=["QC4-01"],
            ),
            Source(
                id="src-eurlex-nis2-demo",
                title="EUR-Lex NIS2 [Demo]",
                url="fixture://demo-nis2/v2.html",
                publisher="EUR-Lex",
                type=SourceType.HTML,
                language="it",
                official=True,
                monitoring_enabled=True,
                check_frequency_hours=24,
                notes=DATASET_MARKER,
                linked_framework_ids=["fw-nis2-it-2026-1"],
                linked_framework_versions=["2026.1"],
                linked_requirement_ids=["NIS2-01"],
            ),
            Source(
                id="src-enisa-nis2-demo",
                title="ENISA NIS2 Guidance [Demo]",
                url="fixture://demo-nis2/v1-cosmetic.html",
                publisher="ENISA",
                type=SourceType.HTML,
                language="en",
                official=True,
                monitoring_enabled=True,
                check_frequency_hours=24,
                notes=DATASET_MARKER,
                linked_framework_ids=["fw-nis2-it-2026-1"],
                linked_framework_versions=["2026.1"],
                linked_requirement_ids=["NIS2-02"],
            ),
        ):
            store.upsert_source(src)
    except Exception as exc:  # noqa: BLE001
        print(f"WARN: regulatory seed skipped: {exc}", file=sys.stderr)

    # Private evidence binaries + framework KB versions (additive, demo-safe)
    try:
        import os

        from engine.evidence_storage import seed_demo_evidence_files
        from engine.framework_versions import seed_from_programs
        from engine.program_loader import load_program_snapshot

        prev = os.environ.get("WAYFOLD_DATA_DIR")
        os.environ["WAYFOLD_DATA_DIR"] = str(root)
        programs = []
        for name in installed:
            path = root / PROGRAMS_SUBDIR / name
            if path.is_file():
                programs.append(load_program_snapshot(path))
        for program in programs:
            seed_demo_evidence_files(program)
        seed_from_programs(programs)
        if prev is None:
            os.environ.pop("WAYFOLD_DATA_DIR", None)
        else:
            os.environ["WAYFOLD_DATA_DIR"] = prev
    except Exception as exc:  # noqa: BLE001
        print(f"WARN: evidence/framework seed skipped: {exc}", file=sys.stderr)

    return {
        "data_root": str(root),
        "registry": str(registry_path),
        "programs_installed": installed,
        "dataset_marker": DATASET_MARKER,
        "seed_version": SEED_VERSION,
        "clients": 5,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Seed WayFold Compliance review demo dataset")
    parser.add_argument("--data-dir", type=Path, default=None, help="Writable data root")
    parser.add_argument(
        "--write-fixtures",
        action="store_true",
        help="Also write versioned fixtures under engine/fixtures/review/",
    )
    parser.add_argument("--fixtures-only", action="store_true")
    args = parser.parse_args(argv)

    if args.write_fixtures or args.fixtures_only:
        paths = write_fixtures()
        print(f"Wrote {len(paths)} fixture files to {REVIEW_FIXTURES}")
        if args.fixtures_only:
            return 0

    result = install_to_data_dir(args.data_dir)
    print(json.dumps(result, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
