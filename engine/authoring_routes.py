"""HTTP helpers for Knowledge Base + client/program authoring."""

from __future__ import annotations

from typing import Any
from urllib.parse import parse_qs, urlencode

from engine import audit as audit_mod
from engine import authoring_pages
from engine import control_catalog
from engine import framework_registry
from engine import framework_versions as fw_versions
from engine import kb_mappings
from engine import product_pages
from engine import program_authoring
from engine.domain import CoverageRelation, MappingRecord, ReviewStatus
from engine.portfolio import DEFAULT_REGISTRY, build_portfolio, load_portfolio_programs
from engine.program_loader import load_program_snapshot
from engine.rbac import (
    PERM_FRAMEWORK_PUBLISH,
    PERM_KB_READ,
    PERM_KB_WRITE,
    PERM_MAPPING_WRITE,
)
from engine.i18n import lang_from_qs
from engine.runtime_paths import portfolio_registry_path
from engine.serialize import to_jsonable
from pathlib import Path


def _form(raw: str) -> dict[str, list[str]]:
    return parse_qs(raw, keep_blank_values=True)


def _one(form: dict[str, list[str]], key: str, default: str = "") -> str:
    return (form.get(key) or [default])[0].strip()


def _nav_qs(
    qs: dict,
    *,
    program_id: str | None = None,
    tenant_name: str | None = None,
    program_name: str | None = None,
) -> str:
    actor = qs.get("actor_tenants", [""])[0]
    superuser = qs.get("superuser", ["0"])[0]
    pid = program_id or qs.get("program_id", [""])[0]
    lang = lang_from_qs(qs)
    data = {"lang": lang}
    if superuser in {"1", "true", "yes"}:
        data["superuser"] = "1"
    if actor:
        data["actor_tenants"] = actor
    if pid:
        data["program_id"] = pid
        tname = tenant_name or qs.get("tenant_name", [""])[0]
        pname = program_name or qs.get("program_name", [""])[0]
        if tname:
            data["tenant_name"] = tname
        if pname:
            data["program_name"] = pname
    return urlencode(data)


def _registry() -> Path:
    return portfolio_registry_path(DEFAULT_REGISTRY)


def _resolve_program(qs: dict):
    program_path = qs.get("program", [None])[0]
    program_id = qs.get("program_id", [None])[0]
    registry = _registry()
    if program_path:
        path = Path(program_path)
        if path.is_file():
            return load_program_snapshot(path)
        return None
    if program_id:
        for program, _ in load_portfolio_programs(registry):
            if program.program_id == program_id:
                return program
    return None


def seed_kb(programs: list[Any]) -> None:
    fw_versions.seed_from_programs(programs)
    control_catalog.seed_from_programs(programs)
    kb_mappings.seed_from_programs(programs)


def frameworks_list_context(programs: list[Any]) -> dict[str, Any]:
    seed_kb(programs)
    versions = fw_versions.list_versions()
    usage: dict[str, int] = {}
    for p in programs:
        for fw in {r.framework_id for r in p.requirements}:
            usage[fw] = usage.get(fw, 0) + 1
    meta = {f.id: f for f in framework_registry.list_frameworks()}
    coverage_by_fw: dict[str, str] = {}
    for fw_id in {v.framework_id for v in versions}:
        published = next(
            (v for v in versions if v.framework_id == fw_id and v.status == "PUBLISHED"),
            None,
        )
        if not published:
            coverage_by_fw[fw_id] = "—"
            continue
        maps = kb_mappings.list_mappings(
            framework_id=fw_id, framework_version=published.version
        )
        summary = kb_mappings.coverage_summary(published.requirements, maps)
        total = summary["total_requirements"] or 1
        pct = int(round(100 * summary["mapped"] / total))
        coverage_by_fw[fw_id] = f"{pct}% ({summary['mapped']}/{summary['total_requirements']})"
    return {
        "versions": versions,
        "usage": usage,
        "meta_by_id": meta,
        "coverage_by_fw": coverage_by_fw,
    }


def handle_authoring_get(handler, path: str, qs: dict, auth) -> bool:
    """Return True if the request was handled."""
    nav = _nav_qs(qs)
    actor_tenants, is_super = auth

    if path == "/frameworks/new":
        if handler._gate(qs, permission=PERM_KB_WRITE) is None:  # type: ignore[attr-defined]
            return True
        handler._send(200, authoring_pages.framework_create_page(nav).encode("utf-8"), "text/html; charset=utf-8")  # type: ignore[attr-defined]
        return True

    if path == "/frameworks/versions/new":
        if handler._gate(qs, permission=PERM_KB_WRITE) is None:
            return True
        programs = [p for p, _ in load_portfolio_programs(_registry())]
        seed_kb(programs)
        for v in fw_versions.list_versions():
            framework_registry.ensure_from_version(
                framework_id=v.framework_id,
                framework_name=v.framework_name,
                publisher=v.publisher,
                source_url=v.source_url,
            )
        handler._send(
            200,
            authoring_pages.version_create_page(
                nav,
                frameworks=framework_registry.list_frameworks(),
                preselect=qs.get("framework_id", [""])[0],
            ).encode("utf-8"),
            "text/html; charset=utf-8",
        )
        return True

    if path == "/frameworks/requirements/new":
        if handler._gate(qs, permission=PERM_KB_WRITE) is None:
            return True
        seed_kb([p for p, _ in load_portfolio_programs(_registry())])
        handler._send(
            200,
            authoring_pages.requirement_create_page(
                nav,
                versions=fw_versions.list_versions(),
                preselect_version=qs.get("version_id", [""])[0],
            ).encode("utf-8"),
            "text/html; charset=utf-8",
        )
        return True

    if path == "/frameworks/requirements/import":
        if handler._gate(qs, permission=PERM_KB_WRITE) is None:
            return True
        handler._send(
            200,
            authoring_pages.csv_import_page(
                nav, version_id=qs.get("version_id", [""])[0]
            ).encode("utf-8"),
            "text/html; charset=utf-8",
        )
        return True

    if path == "/api/frameworks/requirements/template.csv":
        if handler._gate(qs, permission=PERM_KB_READ) is None:
            return True
        handler._send(
            200,
            fw_versions.CSV_TEMPLATE.encode("utf-8"),
            "text/csv; charset=utf-8",
        )
        return True

    if path == "/frameworks/publish":
        if handler._gate(qs, permission=PERM_FRAMEWORK_PUBLISH) is None:
            return True
        vid = qs.get("version_id", [""])[0]
        ver = fw_versions.get_version(vid)
        if ver is None:
            handler._deny(404, "version_not_found")
            return True
        maps = kb_mappings.list_mappings(
            framework_id=ver.framework_id, framework_version=ver.version
        )
        summary = kb_mappings.coverage_summary(ver.requirements, maps)
        handler._send(
            200,
            authoring_pages.publish_page(nav, version=ver, summary=summary).encode("utf-8"),
            "text/html; charset=utf-8",
        )
        return True

    if path in {"/controls", "/api/controls"}:
        if handler._gate(qs, permission=PERM_KB_READ) is None:
            return True
        programs = [p for p, _ in load_portfolio_programs(_registry())]
        seed_kb(programs)
        controls = control_catalog.list_controls(q=qs.get("q", [""])[0] or None)
        usage: dict[str, dict[str, int]] = {}
        for m in kb_mappings.list_mappings():
            u = usage.setdefault(m.canonical_control_ref, {"frameworks": 0, "requirements": 0})
            u["requirements"] += 1
        # approximate frameworks count
        for ref, u in usage.items():
            fws = {
                m.framework_id
                for m in kb_mappings.list_mappings()
                if m.canonical_control_ref == ref
            }
            u["frameworks"] = len(fws)
        if path.startswith("/api/"):
            handler._send(
                200,
                __import__("json").dumps({"controls": to_jsonable(controls)}, ensure_ascii=False).encode("utf-8"),
                "application/json",
            )
            return True
        handler._send(
            200,
            authoring_pages.control_catalog_page(controls, nav, usage=usage).encode("utf-8"),
            "text/html; charset=utf-8",
        )
        return True

    if path == "/controls/new":
        if handler._gate(qs, permission=PERM_KB_WRITE) is None:
            return True
        prefill = {
            "title": qs.get("title", [""])[0],
            "code": qs.get("code", [""])[0],
            "description": qs.get("description", [""])[0],
            "domain": qs.get("domain", [""])[0],
        }
        handler._send(
            200,
            authoring_pages.control_create_page(nav, prefill=prefill).encode("utf-8"),
            "text/html; charset=utf-8",
        )
        return True

    if path == "/controls/detail":
        if handler._gate(qs, permission=PERM_KB_READ) is None:
            return True
        ctrl = control_catalog.get_control(qs.get("control_id", [""])[0])
        if ctrl is None:
            handler._deny(404, "control_not_found")
            return True
        maps = [m for m in kb_mappings.list_mappings() if m.canonical_control_ref == ctrl.code]
        fws = sorted({m.framework_name for m in maps})
        programs = [p for p, _ in load_portfolio_programs(_registry())]
        prog_count = sum(
            1
            for p in programs
            if any(
                (i.canonical_control_ref or "") == ctrl.code for i in p.implementations
            )
        )
        from html import escape
        from engine.ui_components import page_header
        from engine.ui_shell import render_shell

        body = f"""
{page_header(eyebrow='Catalogo controlli', title=ctrl.title, subtitle=ctrl.code)}
<div class="panel" style="padding:16px">
  <p><strong>Dominio:</strong> {escape(ctrl.domain or '—')}</p>
  <p><strong>Obiettivo:</strong> {escape(ctrl.objective or '—')}</p>
  <p>{escape(ctrl.description or '')}</p>
  <div class="mapping-delta" style="margin-top:12px">
    Utilizzato da {len(maps)} mapping · Impatta {len(fws)} framework · Utilizzato in {prog_count} programmi
  </div>
  <h3>Requirement collegati</h3>
  <ul class="compact">{''.join(f"<li><code>{escape(m.requirement_code)}</code> · {escape(m.framework_name)} {escape(m.framework_version)}</li>" for m in maps) or '<li>—</li>'}</ul>
  <h3>Evidence suggerite</h3>
  <p class="meta">{escape(ctrl.suggested_evidence or '—')}</p>
</div>
"""
        handler._send(
            200,
            render_shell(ctrl.title, nav, body, lang="it", active_path="/controls", breadcrumb=ctrl.code).encode("utf-8"),
            "text/html; charset=utf-8",
        )
        return True

    if path == "/mappings/new":
        if handler._gate(qs, permission=PERM_MAPPING_WRITE) is None:
            return True
        seed_kb([p for p, _ in load_portfolio_programs(_registry())])
        reqs = []
        for v in fw_versions.list_versions():
            for r in v.requirements:
                setattr(r, "framework_name", v.framework_name)
                setattr(r, "framework_version", v.version)
                setattr(r, "framework_id", v.framework_id)
                reqs.append(r)
        handler._send(
            200,
            authoring_pages.mapping_create_page(
                nav,
                requirements=reqs,
                controls=control_catalog.list_controls(),
                prefill={
                    "requirement_id": qs.get("requirement_id", [""])[0],
                    "canonical_control_ref": qs.get("control", [""])[0],
                },
            ).encode("utf-8"),
            "text/html; charset=utf-8",
        )
        return True

    if path == "/clients/new":
        if handler._gate(qs) is None:
            return True
        handler._send(200, authoring_pages.client_create_page(nav).encode("utf-8"), "text/html; charset=utf-8")
        return True

    if path == "/programs/new":
        if handler._gate(qs) is None:
            return True
        rows = build_portfolio(
            actor_tenant_ids=actor_tenants,
            is_superuser=is_super,
            registry_path=_registry(),
        )
        clients = []
        seen = set()
        for r in rows:
            if r.tenant_id in seen:
                continue
            seen.add(r.tenant_id)
            clients.append({"tenant_id": r.tenant_id, "tenant_name": r.tenant_name})
        # Also allow brand-new tenants from pending client create via query
        if qs.get("tenant_id", [""])[0] and qs.get("tenant_name", [""])[0]:
            clients.append(
                {
                    "tenant_id": qs.get("tenant_id", [""])[0],
                    "tenant_name": qs.get("tenant_name", [""])[0],
                }
            )
        seed_kb([p for p, _ in load_portfolio_programs(_registry())])
        published = [v for v in fw_versions.list_versions() if v.status == "PUBLISHED"]
        handler._send(
            200,
            authoring_pages.program_create_page(
                nav,
                clients=clients,
                published_versions=published,
                preselect_tenant=qs.get("tenant_id", [""])[0],
            ).encode("utf-8"),
            "text/html; charset=utf-8",
        )
        return True

    if path == "/control/edit":
        if handler._gate(qs) is None:
            return True
        from engine.consultant_views import control_detail
        from engine.control_locking import get_version

        program = _resolve_program(qs)
        if program is None:
            handler._deny(404, "program_not_found")
            return True
        ref = qs.get("control_ref", [""])[0]
        detail = control_detail(program, ref)
        if detail is None:
            handler._deny(404, "control_not_found")
            return True
        ver = get_version(program.program_id, ref)
        handler._send(
            200,
            authoring_pages.control_edit_page(
                nav, detail=detail, expected_version=ver
            ).encode("utf-8"),
            "text/html; charset=utf-8",
        )
        return True

    return False


def handle_authoring_post(handler, path: str, qs: dict, raw: str) -> bool:
    form = _form(raw)
    nav = _nav_qs(qs)
    ctx = getattr(handler, "_auth_ctx", None)
    actor = (ctx.username if ctx else "unknown") or "unknown"

    if path == "/frameworks/new":
        if handler._gate(qs, permission=PERM_KB_WRITE) is None:
            return True
        try:
            fw = framework_registry.create_framework(
                name=_one(form, "name"),
                short_name=_one(form, "short_name"),
                type=_one(form, "type", "Framework"),
                publisher=_one(form, "publisher"),
                jurisdiction=_one(form, "jurisdiction"),
                language=_one(form, "language", "it"),
                description=_one(form, "description"),
                official_url=_one(form, "official_url"),
            )
            ver = fw_versions.create_version(
                framework_id=fw.id,
                framework_name=fw.name,
                publisher=fw.publisher,
                version=_one(form, "version_label", "1.0"),
                source_url=fw.official_url,
            )
        except ValueError as exc:
            handler._send(
                400,
                authoring_pages.framework_create_page(nav, error=str(exc)).encode("utf-8"),
                "text/html; charset=utf-8",
            )
            return True
        audit_mod.record_event(
            actor_user_id=actor,
            action=audit_mod.FRAMEWORK_CREATED,
            entity_type="Framework",
            entity_id=fw.id,
            new_value={"name": fw.name, "type": fw.type},
        )
        audit_mod.record_event(
            actor_user_id=actor,
            action=audit_mod.FRAMEWORK_VERSION_CREATED,
            entity_type="FrameworkVersion",
            entity_id=ver.id,
            new_value={"version": ver.version, "status": ver.status},
        )
        handler._redirect(
            f"/frameworks/detail?framework_id={fw.id}&version_id={ver.id}&{nav}"
        )
        return True

    if path == "/frameworks/versions/new":
        if handler._gate(qs, permission=PERM_KB_WRITE) is None:
            return True
        fw = framework_registry.get_framework(_one(form, "framework_id"))
        if fw is None:
            handler._deny(404, "framework_not_found")
            return True
        try:
            ver = fw_versions.create_version(
                framework_id=fw.id,
                framework_name=fw.name,
                publisher=fw.publisher,
                version=_one(form, "version"),
                notes=_one(form, "notes"),
                effective_date=_one(form, "effective_date") or None,
                publication_date=_one(form, "publication_date") or None,
                source_url=fw.official_url,
            )
        except ValueError as exc:
            handler._send(
                400,
                authoring_pages.version_create_page(
                    nav, frameworks=framework_registry.list_frameworks(), error=str(exc)
                ).encode("utf-8"),
                "text/html; charset=utf-8",
            )
            return True
        audit_mod.record_event(
            actor_user_id=actor,
            action=audit_mod.FRAMEWORK_VERSION_CREATED,
            entity_type="FrameworkVersion",
            entity_id=ver.id,
            new_value={"version": ver.version},
        )
        handler._redirect(
            f"/frameworks/detail?framework_id={fw.id}&version_id={ver.id}&tab=versions&{nav}"
        )
        return True

    if path == "/frameworks/requirements/new":
        if handler._gate(qs, permission=PERM_KB_WRITE) is None:
            return True
        vid = _one(form, "version_id")
        try:
            req = fw_versions.add_requirement(
                vid,
                code=_one(form, "code"),
                title=_one(form, "title"),
                description=_one(form, "description"),
                req_type=_one(form, "req_type", "Requisito"),
                section=_one(form, "section"),
                parent_code=_one(form, "parent_code") or None,
                order=int(_one(form, "order") or "0"),
                source_reference=_one(form, "source_reference"),
                conditions=_one(form, "conditions"),
                frequency=_one(form, "frequency"),
            )
        except fw_versions.ImmutabilityError:
            handler._deny(403, "published_version_immutable")
            return True
        except (ValueError, KeyError) as exc:
            handler._send(
                400,
                authoring_pages.requirement_create_page(
                    nav, versions=fw_versions.list_versions(), error=str(exc)
                ).encode("utf-8"),
                "text/html; charset=utf-8",
            )
            return True
        ver = fw_versions.get_version(vid)
        audit_mod.record_event(
            actor_user_id=actor,
            action=audit_mod.REQUIREMENT_CREATED,
            entity_type="Requirement",
            entity_id=req.id,
            new_value={"code": req.code, "version_id": vid},
        )
        handler._redirect(
            f"/frameworks/detail?framework_id={ver.framework_id}&version_id={vid}&tab=requirements&{nav}"
        )
        return True

    if path == "/frameworks/requirements/import":
        if handler._gate(qs, permission=PERM_KB_WRITE) is None:
            return True
        vid = _one(form, "version_id")
        action = _one(form, "action", "preview")
        try:
            result = fw_versions.import_requirements_csv(
                vid, _one(form, "csv_text"), apply=(action == "apply")
            )
        except fw_versions.ImmutabilityError:
            handler._deny(403, "published_version_immutable")
            return True
        except (ValueError, KeyError) as exc:
            handler._send(
                400,
                authoring_pages.csv_import_page(nav, version_id=vid, error=str(exc)).encode(
                    "utf-8"
                ),
                "text/html; charset=utf-8",
            )
            return True
        if action == "apply" and result.get("applied"):
            ver = fw_versions.get_version(vid)
            handler._redirect(
                f"/frameworks/detail?framework_id={ver.framework_id}&version_id={vid}&tab=requirements&{nav}"
            )
            return True
        handler._send(
            200,
            authoring_pages.csv_import_page(nav, version_id=vid, preview=result).encode(
                "utf-8"
            ),
            "text/html; charset=utf-8",
        )
        return True

    if path == "/frameworks/publish":
        if handler._gate(qs, permission=PERM_FRAMEWORK_PUBLISH) is None:
            return True
        if _one(form, "confirm") != "1":
            handler._deny(400, "confirm_required")
            return True
        vid = _one(form, "version_id")
        try:
            pub = fw_versions.publish_version(vid)
        except KeyError:
            handler._deny(404, "version_not_found")
            return True
        audit_mod.record_event(
            actor_user_id=actor,
            action=audit_mod.FRAMEWORK_VERSION_PUBLISHED,
            entity_type="FrameworkVersion",
            entity_id=pub.id,
            new_value={"version": pub.version, "status": pub.status},
        )
        handler._redirect(
            f"/frameworks/detail?framework_id={pub.framework_id}&version_id={pub.id}&{nav}"
        )
        return True

    if path == "/controls/new":
        if handler._gate(qs, permission=PERM_KB_WRITE) is None:
            return True
        try:
            ctrl = control_catalog.create_control(
                code=_one(form, "code"),
                title=_one(form, "title"),
                domain=_one(form, "domain"),
                objective=_one(form, "objective"),
                description=_one(form, "description"),
                implementation_guidance=_one(form, "implementation_guidance"),
                suggested_evidence=_one(form, "suggested_evidence"),
                default_priority=_one(form, "default_priority", "MEDIUM"),
            )
        except ValueError as exc:
            handler._send(
                400,
                authoring_pages.control_create_page(nav, error=str(exc)).encode("utf-8"),
                "text/html; charset=utf-8",
            )
            return True
        audit_mod.record_event(
            actor_user_id=actor,
            action=audit_mod.CONTROL_CREATED,
            entity_type="CanonicalControl",
            entity_id=ctrl.id,
            new_value={"code": ctrl.code, "title": ctrl.title},
        )
        # If created from requirement, go to mapping create
        req_id = qs.get("from_requirement", [""])[0]
        if req_id:
            handler._redirect(
                f"/mappings/new?requirement_id={req_id}&control={ctrl.code}&{nav}"
            )
            return True
        handler._redirect(f"/controls/detail?control_id={ctrl.id}&{nav}")
        return True

    if path == "/mappings/new":
        if handler._gate(qs, permission=PERM_MAPPING_WRITE) is None:
            return True
        req_id = _one(form, "requirement_id")
        ctrl_ref = _one(form, "canonical_control_ref")
        relation = _one(form, "relation", "FULL").upper()
        # Resolve requirement metadata from versions
        req_meta = None
        ver_meta = None
        for v in fw_versions.list_versions():
            for r in v.requirements:
                if r.id == req_id:
                    req_meta = r
                    ver_meta = v
                    break
            if req_meta:
                break
        if not req_meta or not ver_meta:
            handler._deny(404, "requirement_not_found")
            return True
        if ver_meta.status == "PUBLISHED":
            # Allow mapping edits on published? Spec says published version immutable for requirements.
            # Mappings on published should also be immutable — require clone.
            handler._deny(403, "published_version_immutable")
            return True
        ctrl = control_catalog.get_by_code(ctrl_ref)
        try:
            mid, record = kb_mappings.upsert_mapping(
                MappingRecord(
                    requirement_id=req_id,
                    framework_id=ver_meta.framework_id,
                    framework_name=ver_meta.framework_name,
                    framework_version=ver_meta.version,
                    requirement_code=req_meta.code,
                    canonical_control_id=(ctrl.id if ctrl else ctrl_ref),
                    canonical_control_ref=ctrl_ref,
                    relation=CoverageRelation(relation),
                    rationale=_one(form, "rationale"),
                    uncovered_delta=_one(form, "uncovered_delta"),
                    review_status=ReviewStatus(_one(form, "review_status", "DRAFT")),
                )
            )
        except ValueError as exc:
            seed_kb([])
            reqs = []
            for v in fw_versions.list_versions():
                for r in v.requirements:
                    r.framework_name = v.framework_name  # type: ignore[attr-defined]
                    r.framework_version = v.version  # type: ignore[attr-defined]
                    reqs.append(r)
            handler._send(
                400,
                authoring_pages.mapping_create_page(
                    nav,
                    requirements=reqs,
                    controls=control_catalog.list_controls(),
                    error=str(exc),
                    prefill={
                        "requirement_id": req_id,
                        "canonical_control_ref": ctrl_ref,
                        "relation": relation,
                        "uncovered_delta": _one(form, "uncovered_delta"),
                    },
                ).encode("utf-8"),
                "text/html; charset=utf-8",
            )
            return True
        audit_mod.record_event(
            actor_user_id=actor,
            action=audit_mod.MAPPING_CREATED,
            entity_type="Mapping",
            entity_id=mid,
            new_value={
                "requirement": record.requirement_code,
                "control": record.canonical_control_ref,
                "relation": record.relation.value,
            },
        )
        handler._redirect(
            f"/frameworks/detail?framework_id={ver_meta.framework_id}&version_id={ver_meta.id}&tab=mappings&{nav}"
        )
        return True

    if path == "/clients/new":
        if handler._gate(qs) is None:
            return True
        try:
            client = program_authoring.create_client_shell(
                name=_one(form, "name"),
                code=_one(form, "code"),
                description=_one(form, "description"),
                contact=_one(form, "contact"),
                status=_one(form, "status", "ACTIVE"),
            )
        except ValueError as exc:
            handler._send(
                400,
                authoring_pages.client_create_page(nav, error=str(exc)).encode("utf-8"),
                "text/html; charset=utf-8",
            )
            return True
        audit_mod.record_event(
            actor_user_id=actor,
            action=audit_mod.CLIENT_CREATED,
            entity_type="Client",
            entity_id=client["tenant_id"],
            tenant_id=client["tenant_id"],
            new_value={"name": client["tenant_name"]},
        )
        # Persist pending client marker
        from pathlib import Path
        import json
        from engine.runtime_paths import data_root

        pending = data_root() / "pending_clients.json"
        rows = []
        if pending.is_file():
            try:
                rows = json.loads(pending.read_text(encoding="utf-8")).get("clients") or []
            except (OSError, json.JSONDecodeError):
                rows = []
        rows = [r for r in rows if r.get("tenant_id") != client["tenant_id"]]
        rows.append(client)
        pending.write_text(
            json.dumps({"clients": rows}, indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )
        q = urlencode(
            {
                **dict(__import__("urllib.parse", fromlist=["parse_qsl"]).parse_qsl(nav)),
                "tenant_id": client["tenant_id"],
                "tenant_name": client["tenant_name"],
            }
        )
        handler._redirect(f"/programs/new?{q}")
        return True

    if path == "/programs/new":
        if handler._gate(qs) is None:
            return True
        action = _one(form, "action", "create")
        version_ids = form.get("version_ids") or []
        tenant_id = _one(form, "tenant_id")
        tenant_name = qs.get("tenant_name", [""])[0]
        # resolve tenant name from portfolio or pending
        if not tenant_name:
            for p, _ in load_portfolio_programs(_registry()):
                if p.tenant_id == tenant_id:
                    tenant_name = p.tenant_name
                    break
        if not tenant_name:
            import json
            from engine.runtime_paths import data_root

            pending = data_root() / "pending_clients.json"
            if pending.is_file():
                try:
                    for c in json.loads(pending.read_text(encoding="utf-8")).get("clients") or []:
                        if c.get("tenant_id") == tenant_id:
                            tenant_name = c.get("tenant_name") or tenant_id
                            break
                except (OSError, json.JSONDecodeError):
                    pass
        tenant_name = tenant_name or tenant_id
        if action == "preview":
            try:
                preview = program_authoring.checklist_preview(version_ids)
            except (ValueError, KeyError) as exc:
                preview = None
                err = str(exc)
            else:
                err = ""
            rows = build_portfolio(
                actor_tenant_ids=set(),
                is_superuser=True,
                registry_path=_registry(),
            )
            clients = [{"tenant_id": r.tenant_id, "tenant_name": r.tenant_name} for r in rows]
            clients.append({"tenant_id": tenant_id, "tenant_name": tenant_name})
            published = [v for v in fw_versions.list_versions() if v.status == "PUBLISHED"]
            handler._send(
                200,
                authoring_pages.program_create_page(
                    nav,
                    clients=clients,
                    published_versions=published,
                    preselect_tenant=tenant_id,
                    preview=preview,
                    error=err,
                ).encode("utf-8"),
                "text/html; charset=utf-8",
            )
            return True
        try:
            program = program_authoring.create_program(
                name=_one(form, "name"),
                tenant_id=tenant_id,
                tenant_name=tenant_name,
                scope=_one(form, "scope"),
                owner=_one(form, "owner"),
                description=_one(form, "description"),
                status=_one(form, "status", "ACTIVE"),
                version_ids=version_ids,
                registry_path=_registry(),
            )
        except (ValueError, KeyError) as exc:
            handler._deny(400, str(exc))
            return True
        audit_mod.record_event(
            actor_user_id=actor,
            action=audit_mod.PROGRAM_CREATED,
            entity_type="Program",
            entity_id=program.program_id,
            tenant_id=program.tenant_id,
            new_value={"name": program.program_name, "versions": version_ids},
        )
        q = urlencode(
            {
                **dict(__import__("urllib.parse", fromlist=["parse_qsl"]).parse_qsl(nav)),
                "program_id": program.program_id,
                "tenant_name": program.tenant_name,
                "program_name": program.program_name,
            }
        )
        handler._redirect(f"/client?{q}")
        return True

    return False
