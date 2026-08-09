"""CoreGrcGateway — stable application boundary over GRC core / interim stores.

Production target: CISO Assistant DRF / service layer.
Current backend: WayFold stores + optional ciso_bridge (no direct ORM from UI).
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Protocol

from engine import clients_store, evidence_storage, framework_versions, kb_mappings
from engine.control_catalog import list_controls
from engine.domain import ProgramSnapshot
from engine.portfolio import load_portfolio_programs
from engine.program_authoring import create_program as _create_program
from engine.runtime_paths import data_root


@dataclass
class ClientDTO:
    tenant_id: str
    tenant_name: str
    status: str = "ACTIVE"
    description: str = ""


@dataclass
class ProgramDTO:
    program_id: str
    program_name: str
    tenant_id: str
    tenant_name: str
    status: str = "ACTIVE"
    owner: str = ""
    description: str = ""
    scope: str = ""


class CoreGrcGateway(Protocol):
    def list_clients(self) -> list[ClientDTO]: ...
    def create_client(self, *, name: str, **kwargs: Any) -> ClientDTO: ...
    def list_programs(self) -> list[ProgramDTO]: ...
    def create_program(self, **kwargs: Any) -> ProgramSnapshot: ...
    def get_framework_versions(self, *, framework_id: str | None = None) -> list[Any]: ...
    def get_requirements(self, version_id: str) -> list[Any]: ...
    def get_reference_controls(self) -> list[Any]: ...
    def list_evidence(self, *, tenant_id: str | None = None, program_id: str | None = None) -> list[Any]: ...
    def create_evidence(self, **kwargs: Any) -> Any: ...


class LocalStoreGateway:
    """Interim gateway backed by WayFold JSON stores (migration Slice 0)."""

    def __init__(self, registry_path: Path | None = None) -> None:
        self.registry_path = registry_path or (data_root() / "portfolio_registry.json")

    def list_clients(self) -> list[ClientDTO]:
        # Union first-class clients + tenants inferred from programs
        by_id: dict[str, ClientDTO] = {}
        for c in clients_store.list_clients():
            by_id[c.tenant_id] = ClientDTO(
                tenant_id=c.tenant_id,
                tenant_name=c.tenant_name,
                status=c.status,
                description=c.description,
            )
        for prog, _ in load_portfolio_programs(self.registry_path):
            by_id.setdefault(
                prog.tenant_id,
                ClientDTO(
                    tenant_id=prog.tenant_id,
                    tenant_name=prog.tenant_name,
                    status="ACTIVE",
                ),
            )
        return sorted(by_id.values(), key=lambda c: c.tenant_name.lower())

    def create_client(self, *, name: str, **kwargs: Any) -> ClientDTO:
        rec = clients_store.create_client(name=name, **kwargs)
        return ClientDTO(
            tenant_id=rec.tenant_id,
            tenant_name=rec.tenant_name,
            status=rec.status,
            description=rec.description,
        )

    def list_programs(self) -> list[ProgramDTO]:
        out: list[ProgramDTO] = []
        for prog, path in load_portfolio_programs(self.registry_path):
            owner = ""
            description = ""
            try:
                import json

                raw = json.loads(path.read_text(encoding="utf-8"))
                owner = str(raw.get("owner") or "")
                description = str(raw.get("description") or "")
            except (OSError, json.JSONDecodeError, AttributeError):
                pass
            out.append(
                ProgramDTO(
                    program_id=prog.program_id,
                    program_name=prog.program_name,
                    tenant_id=prog.tenant_id,
                    tenant_name=prog.tenant_name,
                    status=prog.program_status,
                    owner=owner or getattr(prog, "owner", "") or "",
                    description=description or getattr(prog, "description", "") or "",
                    scope=prog.scope,
                )
            )
        return out

    def create_program(self, **kwargs: Any) -> ProgramSnapshot:
        kwargs.setdefault("registry_path", self.registry_path)
        return _create_program(**kwargs)

    def get_framework_versions(self, *, framework_id: str | None = None) -> list[Any]:
        return framework_versions.list_versions(framework_id=framework_id)

    def get_requirements(self, version_id: str) -> list[Any]:
        ver = framework_versions.get_version(version_id)
        return list(ver.requirements) if ver else []

    def get_reference_controls(self) -> list[Any]:
        return list_controls()

    def list_evidence(self, *, tenant_id: str | None = None, program_id: str | None = None) -> list[Any]:
        return evidence_storage.list_evidence(tenant_id=tenant_id, program_id=program_id)

    def create_evidence(self, **kwargs: Any) -> Any:
        return evidence_storage.store_evidence(**kwargs)


_GATEWAY: CoreGrcGateway | None = None


def get_gateway() -> CoreGrcGateway:
    global _GATEWAY
    if _GATEWAY is None:
        _GATEWAY = LocalStoreGateway()
    return _GATEWAY


def set_gateway(gateway: CoreGrcGateway | None) -> None:
    global _GATEWAY
    _GATEWAY = gateway


# Mapping helpers remain WayFold-owned (structurally missing in core)
def list_approved_mappings(**filters: Any) -> list[Any]:
    rows = kb_mappings.list_mappings(**filters)
    return [m for m in rows if getattr(m.review_status, "value", m.review_status) == "APPROVED"]
