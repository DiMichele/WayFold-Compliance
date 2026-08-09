"""Optimistic locking for control implementations (overlay version counter)."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from engine.runtime_paths import data_root


class ConflictError(Exception):
    """Raised when a stale version is submitted."""

    def __init__(self, message: str = "concurrent_modification"):
        super().__init__(message)
        self.user_message_it = (
            "Il controllo è stato modificato da un altro utente. "
            "Ricarica i dati prima di salvare."
        )


def versions_path() -> Path:
    return data_root() / "control_versions.json"


def _load() -> dict[str, Any]:
    path = versions_path()
    if not path.is_file():
        return {"versions": {}}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {"versions": {}}


def _save(data: dict[str, Any]) -> None:
    path = versions_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    tmp.replace(path)


def get_version(program_id: str, control_id: str) -> int:
    data = _load()
    key = f"{program_id}:{control_id}"
    return int(data.get("versions", {}).get(key, 1))


@dataclass
class ControlPatch:
    program_id: str
    control_id: str
    expected_version: int
    changes: dict[str, Any]


def apply_patch(patch: ControlPatch) -> int:
    """Validate expected version and bump. Returns new version."""
    data = _load()
    key = f"{patch.program_id}:{patch.control_id}"
    current = int(data.setdefault("versions", {}).get(key, 1))
    if patch.expected_version != current:
        raise ConflictError()
    new_v = current + 1
    data["versions"][key] = new_v
    _save(data)
    return new_v
