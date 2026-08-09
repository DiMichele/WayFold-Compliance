from __future__ import annotations

import difflib


def unified_diff(old: str, new: str, *, fromfile: str = "old", tofile: str = "new") -> str:
    old_lines = old.splitlines(keepends=True)
    new_lines = new.splitlines(keepends=True)
    if old and not old.endswith("\n"):
        old_lines = old.splitlines(keepends=True)
    diff = difflib.unified_diff(old_lines, new_lines, fromfile=fromfile, tofile=tofile, lineterm="\n")
    return "".join(diff)


def classify_relevance(*, raw_changed: bool, normalized_changed: bool) -> str:
    """Cosmetic HTML churn must not become a normative change automatically."""
    if not raw_changed and not normalized_changed:
        return "NONE"
    if normalized_changed:
        return "SUBSTANTIVE"
    if raw_changed:
        return "COSMETIC"
    return "UNKNOWN"


def summarize_diff(diff_text: str, *, max_lines: int = 12) -> str:
    lines = [ln for ln in diff_text.splitlines() if ln.startswith("+") or ln.startswith("-")]
    lines = [ln for ln in lines if not ln.startswith("+++") and not ln.startswith("---")]
    if not lines:
        return "No textual delta in normalized content"
    preview = "; ".join(lines[:max_lines])
    if len(lines) > max_lines:
        preview += f" … (+{len(lines) - max_lines} more)"
    return preview[:500]
