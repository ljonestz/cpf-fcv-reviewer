"""Browser QA: synthetic smoke by default; --cpf runs a real configured assessment."""

from __future__ import annotations

import argparse
import json
import re
import tempfile
import uuid
from pathlib import Path
from zipfile import ZipFile

from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[1]


def main(
    base_url: str, output: Path, *, cpf: Path | None = None,
    context_document: Path | None = None, country: str = "Benin",
) -> None:
    output.mkdir(parents=True, exist_ok=False)
    mode = "quality" if cpf else "smoke"
    console_errors: list[str] = []
    page_errors: list[str] = []

    def capture(page, number: int, label: str) -> None:
        filename = f"{number:02d}-{label.replace('smoke', mode)}-full.png"
        page.screenshot(path=output / filename, full_page=True)

    def wait_for_results(page) -> None:
        page.wait_for_function(
            "!document.querySelector('#results').hidden || "
            "!document.querySelector('#return-to-intake').hidden || "
            "!document.querySelector('#research-recovery').hidden",
            timeout=900_000 if cpf else 30_000,
        )
        if not page.locator("#results:not([hidden])").is_visible():
            capture(page, 99, "smoke-failure")
            raise RuntimeError("Review stopped; inspect failure screenshot and safe server codes.")
        page.locator("#assistant-send:not([disabled])").wait_for(timeout=10_000)

    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True)
        context = browser.new_context(
            viewport={"width": 1440, "height": 1000}, accept_downloads=True
        )
        health = context.request.get(base_url + "health").json()
        if not cpf and health.get("release") != "deterministic-smoke":
            raise RuntimeError("Synthetic preflight requires the provider-free smoke service.")
        if cpf and health.get("release") == "deterministic-smoke":
            raise RuntimeError("Quality validation requires the actual candidate service.")
        page = context.new_page()
        page.set_default_timeout(120_000 if cpf else 30_000)
        page.on(
            "console",
            lambda message: console_errors.append(message.text)
            if message.type == "error"
            else None,
        )
        page.on("pageerror", lambda error: page_errors.append(str(error)))
        if not cpf:
            def require_country_confirmation(route):
                response = route.fetch()
                payload = response.json()
                payload["requires_confirmation"] = True
                route.fulfill(response=response, json=payload)
            page.route("**/api/detect-country", require_country_confirmation)
        page.goto(base_url, wait_until="networkidle")
        capture(page, 1, "smoke-intake-desktop")

        if cpf:
            page.locator("#cpf").set_input_files(str(cpf))
            if context_document:
                page.locator("#context-documents").set_input_files(str(context_document))
        else:
            primary = (
                b"Country Partnership Framework for the Republic of Benin for FY26-FY30\n"
                + (ROOT / "tests" / "fixtures" / "synthetic_en.txt").read_bytes()
            )
            page.locator("#cpf").set_input_files(
                {
                    "name": "Benin-synthetic-CPF.txt",
                    "mimeType": "text/plain",
                    "buffer": primary,
                }
            )
            page.locator("#context-documents").set_input_files(
                {
                    "name": "Benin-Risk-and-Resilience-Assessment-March-2025.txt",
                    "mimeType": "text/plain",
                    "buffer": b"Benin Risk and Resilience Assessment. March 2025. "
                    b"[SYNTHETIC SMOKE] Full diagnostic context for local QA.",
                }
            )
        page.wait_for_function(
            "document.querySelector('#country-detection input') || "
            "!document.querySelector('#submit-review').disabled"
        )
        correction = page.locator("#country-detection input")
        if correction.count():
            correction.fill(country)
        page.wait_for_function(
            "document.querySelector('#country').value === " + json.dumps(country) + " && "
            "!document.querySelector('#submit-review').disabled"
        )
        page.locator("#review-stage").select_option("decision_review")
        with page.expect_response(
            lambda response: response.request.method == "POST"
            and response.url.rstrip("/").endswith("/api/reviews"),
            timeout=60_000,
        ) as submitted:
            page.locator("#submit-review").click()
        created = submitted.value.json()
        handoff = Path(tempfile.gettempdir()) / f"cpf-review-{uuid.uuid4().hex}.json"
        handoff.write_text(json.dumps({
            "assessment_id": created["assessment_id"], "base_url": base_url, "mode": mode,
        }), encoding="utf-8")
        print(f"REVIEW_SUBMITTED mode={mode} handoff={handoff}", flush=True)
        page.locator("#progress:not([hidden])").wait_for(timeout=5_000)
        capture(page, 2, "smoke-holding-desktop")
        wait_for_results(page)

        assert page.locator("#summary-panel:not([hidden])").is_visible()
        capture(page, 3, "smoke-summary-desktop")
        page.locator("#result-tab-detailed").click()
        assert page.locator("#detailed-panel:not([hidden])").is_visible()
        capture(page, 4, "smoke-detailed-desktop")

        page.get_by_role("button", name="Summarise for management").click()
        page.locator("#assistant-send").click()
        page.wait_for_function(
            "document.querySelectorAll('#assistant-conversation article').length === 2 && "
            "!document.querySelector('#assistant-send').disabled"
        )
        capture(page, 5, "smoke-assistant-streamed-desktop")

        page.reload(wait_until="networkidle")
        wait_for_results(page)
        page.wait_for_function(
            "document.querySelectorAll('#assistant-conversation article').length === 2"
        )
        title = page.locator("#result-title").inner_text().strip()
        assert re.fullmatch(rf"{re.escape(country)} (?:CPF|CEN|CPF / CEN) FCV review", title), title
        capture(page, 6, "smoke-assistant-restored-desktop")

        page.locator("#corrections summary").click()
        capture(page, 7, "smoke-secondary-correction-desktop")
        docx = output / f"08-{mode}-full-detailed-note.docx"
        with page.expect_download(timeout=30_000) as download_info:
            page.locator("#export-docx").click()
        download_info.value.save_as(docx)
        with ZipFile(docx) as archive:
            assert archive.testzip() is None
            assert {"[Content_Types].xml", "word/document.xml"} <= set(
                archive.namelist()
            )

        with page.expect_download(timeout=30_000) as download_info:
            page.locator("#export-readout-docx").click()
        summary_docx = output / f"08-{mode}-five-minute-readout.docx"
        download_info.value.save_as(summary_docx)
        with ZipFile(summary_docx) as archive:
            assert archive.testzip() is None
            assert "word/document.xml" in archive.namelist()

        page.set_viewport_size({"width": 390, "height": 844})
        page.locator("#corrections summary").click()
        page.locator("#result-tab-summary").click()
        assert page.evaluate("document.documentElement.scrollWidth <= innerWidth")
        capture(page, 9, "smoke-summary-mobile")

        assert not console_errors, console_errors
        assert not page_errors, page_errors
        context.close()
        browser.close()

    print(f"BROWSER_QA_PASS mode={mode} screenshots=8 assistant_messages_restored=2 docx=2")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-url", default="http://127.0.0.1:58422")
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--cpf", type=Path)
    parser.add_argument("--context-document", type=Path)
    parser.add_argument("--country", default="Benin")
    args = parser.parse_args()
    main(args.base_url.rstrip("/") + "/", args.output.resolve(),
         cpf=args.cpf, context_document=args.context_document, country=args.country)
