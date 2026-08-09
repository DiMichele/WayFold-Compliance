"""Centralized SVG icon system for WayFold Compliance UI.

Icons are Lucide-inspired stroke SVGs (16–18px). Never use emoji or Unicode glyphs as icons.
"""

from __future__ import annotations

from html import escape

# path → icon key used by the sidebar
PATH_ICONS: dict[str, str] = {
    "/": "grid",
    "/portfolio": "grid",
    "/clients": "building",
    "/client": "briefcase",
    "/checklist": "shield",
    "/gaps": "gap",
    "/tasks": "checklist",
    "/evidence": "paperclip",
    "/report": "report",
    "/owners": "users",
    "/deadlines": "clock",
    "/frameworks": "book",
    "/controls": "shield",
    "/mappings": "network",
    "/audit": "checklist",
    "/settings": "settings",
    "/users": "users",
    "/sources": "database",
    "/changes": "radar",
    "/change": "radar",
    "/suggestions": "book",
    "/ai/suggestions": "trend",
    "/ai/settings": "settings",
    "/connectors": "link",
    "/auto-evidence": "file",
    "/control": "shield",
}

_PATHS: dict[str, str] = {
    "logo": (
        '<path d="M4.2 5.1h6.3v6.3H4.2zM13.5 5.1h6.3v6.3h-6.3zM8.85 14.1h6.3v6.3h-6.3z" '
        'fill="none" stroke="currentColor" stroke-width="1.8" stroke-linejoin="round"/>'
    ),
    "grid": (
        '<rect x="3.5" y="3.5" width="7" height="7" rx="1.4" fill="none" stroke="currentColor" stroke-width="1.7"/>'
        '<rect x="13.5" y="3.5" width="7" height="4.5" rx="1.4" fill="none" stroke="currentColor" stroke-width="1.7"/>'
        '<rect x="13.5" y="10.5" width="7" height="10" rx="1.4" fill="none" stroke="currentColor" stroke-width="1.7"/>'
        '<rect x="3.5" y="13" width="7" height="7.5" rx="1.4" fill="none" stroke="currentColor" stroke-width="1.7"/>'
    ),
    "building": (
        '<path d="M4 20.5h16M6 20.5V6.2l6-2.7 6 2.7v14.3M9 8.5h.01M15 8.5h.01M9 12h.01M15 12h.01'
        'M9 15.5h.01M15 15.5h.01" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linecap="round"/>'
    ),
    "briefcase": (
        '<path d="M4 8h16v11H4zM9 8V5h6v3M4 12h16" fill="none" stroke="currentColor" '
        'stroke-width="1.7" stroke-linejoin="round"/>'
    ),
    "shield": (
        '<path d="M12 3.4l7 2.8v5.4c0 4.4-2.7 7.3-7 9-4.3-1.7-7-4.6-7-9V6.2l7-2.8z'
        'M8.8 11.8l2.1 2.1 4.4-4.6" fill="none" stroke="currentColor" stroke-width="1.7" '
        'stroke-linecap="round" stroke-linejoin="round"/>'
    ),
    "gap": (
        '<path d="M4 4.5h6.2v6.2H4zM13.8 13.3H20v6.2h-6.2zM14 4.7l5.3 5.3M19.3 4.7L14 10" '
        'fill="none" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round"/>'
    ),
    "checklist": (
        '<path d="M9.5 6h10M9.5 12h10M9.5 18h10M4.2 6l1 1 1.8-2M4.2 12l1 1 1.8-2M4.2 18l1 1 1.8-2" '
        'fill="none" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round"/>'
    ),
    "paperclip": (
        '<path d="M8.2 12.9l6.7-6.7a3.3 3.3 0 014.6 4.7l-8.4 8.4a5 5 0 01-7-7l8.2-8.2" '
        'fill="none" stroke="currentColor" stroke-width="1.7" stroke-linecap="round"/>'
    ),
    "book": (
        '<path d="M4.2 4.5h6.3a3 3 0 013 3v12H7.2a3 3 0 00-3 1zM19.8 4.5h-6.3v15H16.8a3 3 0 013 1z" '
        'fill="none" stroke="currentColor" stroke-width="1.7" stroke-linejoin="round"/>'
    ),
    "network": (
        '<circle cx="5.5" cy="6" r="2" fill="none" stroke="currentColor" stroke-width="1.7"/>'
        '<circle cx="18.5" cy="6" r="2" fill="none" stroke="currentColor" stroke-width="1.7"/>'
        '<circle cx="12" cy="18" r="2" fill="none" stroke="currentColor" stroke-width="1.7"/>'
        '<path d="M7.4 6h9.2M6.6 7.6l4.2 8.8M17.4 7.6l-4.2 8.8" fill="none" stroke="currentColor" stroke-width="1.7"/>'
    ),
    "radar": (
        '<path d="M12 12V4M12 12l5.4-5.4M20 12a8 8 0 11-8-8" fill="none" stroke="currentColor" '
        'stroke-width="1.7" stroke-linecap="round"/>'
        '<circle cx="12" cy="12" r="2" fill="none" stroke="currentColor" stroke-width="1.7"/>'
    ),
    "report": (
        '<path d="M5 3.8h10l4 4v12.4H5zM15 3.8v4h4M8 16v-3M12 16V9M16 16v-5" fill="none" '
        'stroke="currentColor" stroke-width="1.7" stroke-linejoin="round"/>'
    ),
    "settings": (
        '<circle cx="12" cy="12" r="3" fill="none" stroke="currentColor" stroke-width="1.7"/>'
        '<path d="M19.4 15a1.65 1.65 0 00.33 1.82l.06.06a2 2 0 11-2.83 2.83l-.06-.06a1.65 1.65 0 00-1.82-.33 '
        '1.65 1.65 0 00-1 1.51V21a2 2 0 11-4 0v-.09A1.65 1.65 0 009 19.4a1.65 1.65 0 00-1.82.33l-.06.06a2 2 0 '
        '11-2.83-2.83l.06-.06A1.65 1.65 0 004.68 15a1.65 1.65 0 00-1.51-1H3a2 2 0 110-4h.09A1.65 1.65 0 004.6 '
        '9a1.65 1.65 0 00-.33-1.82l-.06-.06a2 2 0 112.83-2.83l.06.06A1.65 1.65 0 009 4.68a1.65 1.65 0 001-1.51V3a2 '
        '2 0 114 0v.09a1.65 1.65 0 001 1.51 1.65 1.65 0 001.82-.33l.06-.06a2 2 0 112.83 2.83l-.06.06A1.65 1.65 0 '
        '0019.4 9a1.65 1.65 0 001.51 1H21a2 2 0 110 4h-.09a1.65 1.65 0 00-1.51 1z" fill="none" '
        'stroke="currentColor" stroke-width="1.5" stroke-linejoin="round"/>'
    ),
    "chevron-right": (
        '<path d="M9 5l7 7-7 7" fill="none" stroke="currentColor" stroke-width="1.8" '
        'stroke-linecap="round" stroke-linejoin="round"/>'
    ),
    "chevron-down": (
        '<path d="M5 9l7 7 7-7" fill="none" stroke="currentColor" stroke-width="1.8" '
        'stroke-linecap="round" stroke-linejoin="round"/>'
    ),
    "search": (
        '<circle cx="10.5" cy="10.5" r="6" fill="none" stroke="currentColor" stroke-width="1.8"/>'
        '<path d="M15 15l5 5" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round"/>'
    ),
    "plus": (
        '<path d="M12 5v14M5 12h14" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round"/>'
    ),
    "download": (
        '<path d="M12 4v11M8 11l4 4 4-4M5 19h14" fill="none" stroke="currentColor" stroke-width="1.7" '
        'stroke-linecap="round" stroke-linejoin="round"/>'
    ),
    "alert": (
        '<path d="M12 4l9 16H3L12 4zM12 9v5M12 17.5h.01" fill="none" stroke="currentColor" '
        'stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round"/>'
    ),
    "users": (
        '<circle cx="9" cy="8" r="3" fill="none" stroke="currentColor" stroke-width="1.7"/>'
        '<path d="M3.5 19a5.5 5.5 0 0111 0M16 5.5a3 3 0 010 5.7M15.5 14a5 5 0 015 5" fill="none" '
        'stroke="currentColor" stroke-width="1.7" stroke-linecap="round"/>'
    ),
    "trend": (
        '<path d="M4 17l5-5 4 3 7-8M15 7h5v5" fill="none" stroke="currentColor" stroke-width="1.7" '
        'stroke-linecap="round" stroke-linejoin="round"/>'
    ),
    "clock": (
        '<circle cx="12" cy="12" r="8.5" fill="none" stroke="currentColor" stroke-width="1.7"/>'
        '<path d="M12 7v5l3 2" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linecap="round"/>'
    ),
    "file": (
        '<path d="M5 3.5h9l5 5v12H5zM14 3.5v5h5" fill="none" stroke="currentColor" '
        'stroke-width="1.7" stroke-linejoin="round"/>'
    ),
    "link": (
        '<path d="M9.5 14.5l5-5M7 17H5.8a4 4 0 010-8H9M17 7h1.2a4 4 0 010 8H15" fill="none" '
        'stroke="currentColor" stroke-width="1.7" stroke-linecap="round"/>'
    ),
    "database": (
        '<ellipse cx="12" cy="5.5" rx="7" ry="3" fill="none" stroke="currentColor" stroke-width="1.7"/>'
        '<path d="M5 5.5v6c0 1.7 3.1 3 7 3s7-1.3 7-3v-6M5 11.5v6c0 1.7 3.1 3 7 3s7-1.3 7-3v-6" '
        'fill="none" stroke="currentColor" stroke-width="1.7"/>'
    ),
    "arrow-right": (
        '<path d="M4 12h15M14 7l5 5-5 5" fill="none" stroke="currentColor" stroke-width="1.7" '
        'stroke-linecap="round" stroke-linejoin="round"/>'
    ),
    "check": (
        '<path d="M5 12l4 4L19 6" fill="none" stroke="currentColor" stroke-width="1.9" '
        'stroke-linecap="round" stroke-linejoin="round"/>'
    ),
    "x": (
        '<path d="M6 6l12 12M18 6L6 18" fill="none" stroke="currentColor" stroke-width="1.8" '
        'stroke-linecap="round"/>'
    ),
    "lang": (
        '<circle cx="12" cy="12" r="9" fill="none" stroke="currentColor" stroke-width="1.7"/>'
        '<path d="M3 12h18M12 3a14 14 0 010 18M12 3a14 14 0 000 18" fill="none" '
        'stroke="currentColor" stroke-width="1.5"/>'
    ),
}


def icon(name: str, *, css_class: str = "wf-icon", size: int | None = None) -> str:
    """Inline SVG icon. Falls back to alert if unknown."""
    body = _PATHS.get(name) or _PATHS["alert"]
    size_attr = f' width="{size}" height="{size}"' if size else ""
    return (
        f'<svg class="{escape(css_class)}" viewBox="0 0 24 24" aria-hidden="true"{size_attr}>'
        f"{body}</svg>"
    )


def icon_for_path(path: str, *, css_class: str = "nav-icon") -> str:
    key = PATH_ICONS.get(path, "grid")
    return icon(key, css_class=css_class)


def sprite_defs() -> str:
    """Optional hidden sprite (kept for future <use> refs)."""
    symbols = []
    for name, body in _PATHS.items():
        symbols.append(f'<symbol id="i-{escape(name)}" viewBox="0 0 24 24">{body}</symbol>')
    return (
        '<svg class="hidden-svg" aria-hidden="true" focusable="false">'
        + "".join(symbols)
        + "</svg>"
    )
