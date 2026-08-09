"""Minimal multipart/form-data parser for evidence uploads."""

from __future__ import annotations

from dataclasses import dataclass
from email.parser import BytesParser
from email.policy import default


@dataclass
class UploadedFile:
    filename: str
    content_type: str
    content: bytes


def parse_multipart(
    content_type: str, body: bytes
) -> tuple[dict[str, str], dict[str, UploadedFile]]:
    if "multipart/form-data" not in (content_type or "").lower():
        raise ValueError("multipart_required")
    # Extract boundary
    boundary = ""
    for part in content_type.split(";"):
        part = part.strip()
        if part.lower().startswith("boundary="):
            boundary = part.split("=", 1)[1].strip().strip('"')
            break
    if not boundary:
        raise ValueError("multipart_boundary_missing")

    preamble = (
        b"MIME-Version: 1.0\r\nContent-Type: multipart/form-data; boundary="
        + boundary.encode("ascii", "ignore")
        + b"\r\n\r\n"
    )
    msg = BytesParser(policy=default).parsebytes(preamble + body)
    fields: dict[str, str] = {}
    files: dict[str, UploadedFile] = {}
    if not msg.is_multipart():
        raise ValueError("multipart_invalid")
    for part in msg.iter_parts():
        disp = part.get_content_disposition()
        if disp != "form-data":
            continue
        name = part.get_param("name", header="content-disposition")
        if not name:
            continue
        filename = part.get_filename()
        payload = part.get_payload(decode=True) or b""
        if filename:
            files[name] = UploadedFile(
                filename=filename,
                content_type=part.get_content_type() or "application/octet-stream",
                content=payload,
            )
        else:
            try:
                fields[name] = payload.decode("utf-8")
            except UnicodeDecodeError:
                fields[name] = payload.decode("latin-1", "replace")
    return fields, files
