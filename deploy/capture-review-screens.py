"""Capture live review screenshots at 1920x1080 (and key pages at 1440x900)."""

from __future__ import annotations

from pathlib import Path

from playwright.sync_api import sync_playwright

BASE = "https://compliance.wayfold.xyz"
OUT = Path(__file__).resolve().parents[1] / "docs" / "review" / "final"
PID = "program-michele-cyber-2026"

PAGES = [
    ("01-login.png", "/login", False),
    ("02-portfolio.png", "/portfolio", True),
    ("03-clients.png", "/clients", True),
    ("04-michele-workspace.png", f"/client?program_id={PID}", True),
    ("05-unified-controls.png", f"/checklist?program_id={PID}", True),
    ("06-control-iam-detail.png", f"/control?program_id={PID}&control_ref=CTRL-IAM-001", True),
    ("07-gap-assessment.png", f"/gaps?program_id={PID}", True),
    ("08-tasks.png", f"/tasks?program_id={PID}", True),
    ("09-evidence.png", f"/evidence?program_id={PID}", True),
    ("10-frameworks.png", "/frameworks", True),
    ("11-framework-nis2-detail.png", "/frameworks/detail?framework_id=fw-nis2-it-2026-1", True),
    ("12-mappings.png", f"/mappings?program_id={PID}", True),
    ("13-regulatory.png", "/changes", True),
    ("14-report.png", f"/report?program_id={PID}", True),
    ("15-settings.png", "/settings", True),
    ("16-audit-log.png", "/audit", True),
]

MAIN_FOR_1440 = {
    "02-portfolio.png",
    "04-michele-workspace.png",
    "05-unified-controls.png",
    "10-frameworks.png",
    "12-mappings.png",
}


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(viewport={"width": 1920, "height": 1080})
        page = context.new_page()
        # login page first (anonymous)
        page.goto(f"{BASE}/logout", wait_until="networkidle")
        page.goto(f"{BASE}/login", wait_until="networkidle")
        page.screenshot(path=str(OUT / "01-login.png"), full_page=False)

        page.fill("#username", "admin")
        page.fill("#password", "admin")
        page.click("button[type=submit]")
        page.wait_for_url("**/portfolio**", timeout=15000)

        for name, path, authed in PAGES:
            if name == "01-login.png":
                continue
            page.goto(f"{BASE}{path}", wait_until="networkidle")
            page.screenshot(path=str(OUT / name), full_page=False)
            print("saved", name)

        # 1440x900 variants
        page.set_viewport_size({"width": 1440, "height": 900})
        for name in MAIN_FOR_1440:
            path = dict((n, u) for n, u, _ in PAGES)[name]
            page.goto(f"{BASE}{path}", wait_until="networkidle")
            out = OUT / name.replace(".png", "-1440.png")
            page.screenshot(path=str(out), full_page=False)
            print("saved", out.name)

        browser.close()
    print("OUT", OUT)


if __name__ == "__main__":
    main()
