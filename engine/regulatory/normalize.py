from __future__ import annotations

import json
import re
from html.parser import HTMLParser


class _TextExtractor(HTMLParser):
    def __init__(self):
        super().__init__()
        self._chunks: list[str] = []
        self._skip = 0

    def handle_starttag(self, tag, attrs):  # noqa: ARG002
        if tag in {"script", "style", "noscript"}:
            self._skip += 1

    def handle_endtag(self, tag):
        if tag in {"script", "style", "noscript"} and self._skip:
            self._skip -= 1

    def handle_data(self, data):
        if self._skip:
            return
        text = data.strip()
        if text:
            self._chunks.append(text)

    def text(self) -> str:
        return "\n".join(self._chunks)


_WS = re.compile(r"[ \t]+")
_BLANK = re.compile(r"\n{3,}")


def normalize_html(raw: str) -> str:
    parser = _TextExtractor()
    try:
        parser.feed(raw)
        parser.close()
        text = parser.text()
    except Exception:  # noqa: BLE001
        text = re.sub(r"<[^>]+>", " ", raw)
    return _collapse(text)


def normalize_json(raw: str) -> str:
    try:
        data = json.loads(raw)
        return json.dumps(data, sort_keys=True, ensure_ascii=False, indent=2)
    except json.JSONDecodeError:
        return _collapse(raw)


def normalize_text(raw: str) -> str:
    return _collapse(raw)


def normalize_content(raw: str, *, content_type: str) -> str:
    ct = (content_type or "").lower()
    if "json" in ct:
        return normalize_json(raw)
    if "html" in ct or ct.endswith("html"):
        return normalize_html(raw)
    return normalize_text(raw)


def _collapse(text: str) -> str:
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = "\n".join(_WS.sub(" ", line).strip() for line in text.split("\n"))
    text = _BLANK.sub("\n\n", text).strip()
    return text
