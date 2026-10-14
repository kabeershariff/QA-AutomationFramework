"""Regenerate the screenshots referenced by the bug reports in ``reports/bugs/``.

The DOM tables in each report are the primary evidence and are reproducible by reading
the source; these screenshots are the visual half. Running this script rebuilds them
from the current ``mock_site/dist`` so a reviewer can confirm the reports without
trusting a checked-in binary.

Usage
-----
    python tools/capture_bug_evidence.py

Writes PNGs to ``reports/bugs/evidence/`` and prints the probe values it measured, so the
numbers quoted in the reports can be re-verified rather than taken on faith.
"""

from __future__ import annotations

import http.server
import json
import socketserver
import sys
import threading
from pathlib import Path

from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parent.parent
DIST = ROOT / "mock_site" / "dist"
#: Bug evidence lives outside ``reports/artifacts/`` because that directory is
#: gitignored â€” it holds transient per-run failure output, while these screenshots are
#: cited by the bug reports and must survive a clean checkout.
EVIDENCE = ROOT / "reports" / "bugs" / "evidence"
PORT = 8799

RESUME = ROOT / ".pytest_tmp" / "evidence-resume.pdf"
EXE = ROOT / ".pytest_tmp" / "evidence-resume.exe"
EMPTY_PDF = ROOT / ".pytest_tmp" / "evidence-empty.pdf"


def serve() -> http.server.ThreadingHTTPServer:
    """Serve ``mock_site/dist`` with the SPA fallback the app needs."""

    class Handler(http.server.SimpleHTTPRequestHandler):
        def __init__(self, *args, **kwargs):
            super().__init__(*args, directory=str(DIST), **kwargs)

        def send_head(self):
            target = self.translate_path(self.path)
            if not Path(target).exists() and not Path(target).suffix:
                self.path = "/index.html"
            return super().send_head()

        def log_message(self, *args):
            pass

    socketserver.TCPServer.allow_reuse_address = True
    httpd = http.server.ThreadingHTTPServer(("127.0.0.1", PORT), Handler)
    threading.Thread(target=httpd.serve_forever, daemon=True).start()
    return httpd


def write_fixtures() -> None:
    for path in (RESUME, EXE, EMPTY_PDF):
        path.parent.mkdir(parents=True, exist_ok=True)
    RESUME.write_bytes(b"%PDF-1.4\n% evidence fixture, not a real document\n%%EOF\n")
    EXE.write_bytes(b"MZ\x90\x00\x03\x00\x00\x00\x04\x00\x00\x00\xff\xff\x00\x00")
    EMPTY_PDF.write_bytes(b"")


def fill_valid(form_page, resume: Path = RESUME) -> None:
    form_page.get_by_label("Full name").fill("QA Evidence Probe")
    form_page.get_by_label("Email").fill("qa.probe@example.com")
    form_page.get_by_label("Current location").fill("Remote")
    form_page.locator("#field-resume").set_input_files(str(resume))
    form_page.check("#field-workAuthorization-yes")


def capture_bug_002(page, base: str, out: dict) -> None:
    """An unknown job id still serves a working application form."""
    page.goto(f"{base}/jd?scenarios=simple-company-form&id=9999&dataset=big_company_cs_1000")
    page.wait_for_selector("[data-section='jd'][data-state='not-found']", timeout=20000)
    out["BUG-002"] = {
        "not_found_sections": page.locator("[data-section='jd'][data-state='not-found']").count(),
        "article_h1": page.locator("article h1").count(),
        "scenario_form_sections": page.locator("[data-section='scenario-form']").count(),
        "submit_buttons": page.locator("button[data-action='submit-application']").count(),
        "url_before_submit": page.url,
    }
    page.screenshot(path=str(EVIDENCE / "BUG-002-unknown-job-id.png"), full_page=True)

    fill_valid(page)
    page.click("button[data-action='submit-application']")
    page.wait_for_selector("[data-inline-submission]", timeout=20000)
    payload = json.loads(page.locator("[data-inline-submission] > pre").first.text_content())
    out["BUG-002"].update(
        submission_accepted=payload["validation"]["passed"],
        submitted_url=page.url,
    )


def capture_bug_003(page, base: str, out: dict) -> None:
    """No maxlength on name/location; a 5000-character name round-trips verbatim."""
    page.goto(f"{base}/jd?scenarios=simple-company-form&id=0&dataset=big_company_cs_1000")
    page.wait_for_selector("button[data-action='submit-application']")
    out["BUG-003"] = {
        "fullName_maxlength": page.get_by_label("Full name").get_attribute("maxlength"),
        "location_maxlength": page.get_by_label("Current location").get_attribute("maxlength"),
        "email_maxlength": page.get_by_label("Email").get_attribute("maxlength"),
    }

    page.get_by_label("Full name").fill("A" * 5000)
    page.get_by_label("Email").fill("qa.probe@example.com")
    page.get_by_label("Current location").fill("Remote")
    page.locator("#field-resume").set_input_files(str(RESUME))
    page.check("#field-workAuthorization-yes")
    page.click("button[data-action='submit-application']")
    page.wait_for_selector("[data-inline-submission]", timeout=20000)
    payload = json.loads(page.locator("[data-inline-submission] > pre").first.text_content())
    out["BUG-003"].update(
        accepted_5000_chars=payload["validation"]["passed"],
        round_tripped_length=len(payload["candidate"]["fullName"]),
    )
    page.screenshot(path=str(EVIDENCE / "BUG-003-no-maxlength.png"), full_page=True)


def capture_bug_004(page, base: str, out: dict) -> None:
    """The resume `accept` list is declared but never enforced."""
    out["BUG-004"] = {"accept_attr": None}
    for path in (EXE, EMPTY_PDF):
        page.goto(f"{base}/jd?scenarios=simple-company-form&id=0&dataset=big_company_cs_1000")
        page.wait_for_selector("#field-resume")
        if out["BUG-004"]["accept_attr"] is None:
            out["BUG-004"]["accept_attr"] = page.locator("#field-resume").get_attribute("accept")
        page.locator("#field-resume").set_input_files(str(path))
        page.wait_for_selector("[data-file-list] li", timeout=10000)
        out["BUG-004"][path.suffix.lstrip(".")] = {
            "listed": page.locator("[data-file-list] li").all_inner_texts(),
            "field_errors": page.locator("[data-field-error]").count(),
        }


def capture_bug_005(page, base: str, out: dict) -> None:
    """A malformed email is reported as missing; no field error, no aria-invalid."""
    page.goto(f"{base}/jd?scenarios=simple-company-form&id=0&dataset=big_company_cs_1000")
    page.wait_for_selector("#field-email")
    fill_valid(page)
    page.get_by_label("Email").fill("not-an-email")
    page.click("button[data-action='submit-application']")
    page.wait_for_selector("[data-section='validation-summary']", timeout=20000)
    out["BUG-005"] = {
        "email_input_value": page.get_by_label("Email").input_value(),
        "summary_text": page.locator("[data-section='validation-summary']").inner_text().strip(),
        "field_error_count": page.locator("[data-field-error]").count(),
        "email_aria_invalid": page.get_by_label("Email").get_attribute("aria-invalid"),
    }
    page.screenshot(path=str(EVIDENCE / "BUG-005-invalid-email-as-missing.png"), full_page=True)


def capture_bug_006(page, base: str, out: dict) -> None:
    """Empty 'Salary:' / 'Experience:' pills on a dataset that carries neither."""
    page.goto(f"{base}/")
    page.wait_for_selector("[data-job-row]", timeout=30000)
    out["BUG-006"] = {
        "row_count": page.locator("[data-job-row]").count(),
        "salary_pill_0": page.locator("[data-job-salary]").first.inner_text().strip(),
        "experience_pill_0": page.locator("[data-job-experience]").first.inner_text().strip(),
        "index_status": page.locator("[data-job-index-status]").inner_text().strip(),
        "pagination": page.locator("[data-section='pagination'] span").inner_text().strip(),
    }
    page.screenshot(path=str(EVIDENCE / "BUG-006-empty-salary-pills.png"), full_page=True)

    page.goto(f"{base}/jd?scenarios=simple-company-form&id=0&dataset=big_company_cs_1000")
    page.wait_for_selector("[data-section='jd']", timeout=30000)
    out["BUG-006"]["detail_salary_pill"] = page.locator("[data-jd-salary]").first.inner_text().strip()


def main() -> int:
    if not DIST.is_dir():
        print(f"error: {DIST} not found â€” run `npm run build` in mock_site/ first", file=sys.stderr)
        return 1

    EVIDENCE.mkdir(parents=True, exist_ok=True)
    write_fixtures()
    httpd = serve()
    base = f"http://127.0.0.1:{PORT}"
    out: dict = {}

    try:
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch()
            page = browser.new_page(viewport={"width": 1280, "height": 720})
            page_errors: list[str] = []
            page.on("pageerror", lambda error: page_errors.append(str(error)))
            try:
                for capture in (
                    capture_bug_002,
                    capture_bug_003,
                    capture_bug_004,
                    capture_bug_005,
                    capture_bug_006,
                ):
                    capture(page, base, out)
            finally:
                browser.close()
            out["uncaught_page_errors"] = page_errors
    finally:
        httpd.shutdown()

    print(json.dumps(out, indent=2, ensure_ascii=False))
    print(f"\nscreenshots written to {EVIDENCE}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())