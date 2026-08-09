from __future__ import annotations

import json
from pathlib import Path
from typing import Protocol

from .domain import FindingStatus, NormalizedFinding
from .hashutil import content_hash


class ScannerAdapter(Protocol):
    """Boundary: external scanner output → NormalizedFinding. No GRC writes."""

    name: str

    def parse(self, payload: bytes | str | Path, *, observed_at: str) -> list[NormalizedFinding]: ...


def _status_from_prowler(raw: str) -> FindingStatus:
    s = (raw or "").strip().upper()
    if s in {"PASS", "PASSED", "OK"}:
        return FindingStatus.PASS
    if s in {"FAIL", "FAILED", "CRITICAL"}:
        return FindingStatus.FAIL
    if s in {"MANUAL", "INFO"}:
        return FindingStatus.MANUAL if s == "MANUAL" else FindingStatus.INFO
    if s in {"ERROR"}:
        return FindingStatus.ERROR
    return FindingStatus.MANUAL


class ProwlerJsonAdapter:
    """Parse Prowler JSON / OCSF-like export (fixture-compatible).

    Does not execute Prowler. Live scan deferred when environment blocks clone/run
    (Windows path length — see DECISIONS / open-source-evaluation).
    """

    name = "prowler-json-v1"

    def parse(self, payload: bytes | str | Path, *, observed_at: str) -> list[NormalizedFinding]:
        if isinstance(payload, Path):
            text = payload.read_text(encoding="utf-8")
        elif isinstance(payload, bytes):
            text = payload.decode("utf-8")
        else:
            text = payload
        data = json.loads(text)
        rows = data if isinstance(data, list) else data.get("findings") or data.get("Checks") or []
        out: list[NormalizedFinding] = []
        for row in rows:
            check_id = str(
                row.get("CheckID")
                or row.get("check_id")
                or row.get("finding_info", {}).get("uid")
                or ""
            )
            if not check_id:
                continue
            title = str(
                row.get("CheckTitle")
                or row.get("check_title")
                or row.get("finding_info", {}).get("title")
                or check_id
            )
            status = _status_from_prowler(
                str(row.get("Status") or row.get("status") or row.get("status_code") or "MANUAL")
            )
            resource = row.get("ResourceId") or row.get("resource_uid") or row.get("resources", [{}])
            if isinstance(resource, list):
                resource_uid = str((resource[0] or {}).get("uid") or (resource[0] or {}).get("name") or "")
                resource_name = str((resource[0] or {}).get("name") or resource_uid)
            else:
                resource_uid = str(resource or row.get("ResourceName") or "")
                resource_name = str(row.get("ResourceName") or resource_uid)
            provider = str(row.get("Provider") or row.get("provider") or "aws")
            region = str(row.get("Region") or row.get("region") or "")
            description = str(row.get("StatusExtended") or row.get("description") or "")
            remediation = str(
                (row.get("Remediation") or {}).get("Recommendation", {}).get("Text")
                if isinstance(row.get("Remediation"), dict)
                else row.get("remediation") or ""
            )
            raw_slice = json.dumps(row, sort_keys=True, ensure_ascii=False)
            out.append(
                NormalizedFinding(
                    check_id=check_id,
                    check_title=title,
                    status=status,
                    severity=str(row.get("Severity") or row.get("severity") or "medium"),
                    resource_uid=resource_uid,
                    resource_name=resource_name,
                    provider=provider,
                    region=region,
                    description=description,
                    remediation=remediation,
                    raw_ref=f"prowler:{check_id}:{resource_uid}",
                    observed_at=str(row.get("Timestamp") or row.get("timestamp") or observed_at),
                    content_hash=content_hash(raw_slice),
                )
            )
        return out


def load_adapter(kind: str) -> ScannerAdapter:
    k = kind.upper()
    if k in {"PROWLER_JSON", "FIXTURE", "PROWLER"}:
        return ProwlerJsonAdapter()
    raise ValueError(f"unsupported_adapter:{kind}")
