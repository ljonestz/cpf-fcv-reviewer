"""Run the complete provider-free browser QA flow against local smoke mode."""

from __future__ import annotations

import argparse
import re
from pathlib import Path
from zipfile import ZipFile

from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[1]


def main(base_url: str, output: Path) -> None:
    output.mkdir(parents=True, exist_ok=False)
    console_errors: list[str] = []
    page_errors: list[str] = []

    def capture(page, number: int, label: str) -> None:
        page.screenshot(path=output / f"{number:02d}-{label}-full.png", full_page=True)

    def wait_for_results(page) -> None:
        page.locator("#results:not([hidden])").wait_for(timeout=30_000)
        page.locator("#assistant-send:not([disabled])").wait_for(timeout=10_000)

    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True)
        context = browser.new_context(
            viewport={"width": 1440, "height": 1000}, accept_downloads=True
        )
        page = context.new_page()
        page.on(
            "console",
            lambda message: console_errors.append(message.text)
            if message.type == "error"
            else None,
        )
        page.on("pageerror", lambda error: page_errors.append(str(error)))
        page.goto(base_url, wait_until="networkidle")
        capture(page, 1, "smoke-intake-desktop")

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
            "document.querySelector('#country').value === 'Benin' && "
            "!document.querySelector('#submit-review').disabled"
        )
        page.locator("#review-stage").select_option("decision_review")
        page.locator("#submit-review").click()
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
        page.locator("#assistant-input").fill("Expand the priority measure for local QA.")
        page.locator("#assistant-send").click()
        page.wait_for_function(
            "document.querySelectorAll('#assistant-conversation article').length === 4 && "
            "!document.querySelector('#assistant-send').disabled"
        )
        page.reload(wait_until="networkidle")
        wait_for_results(page)
        page.wait_for_function(
            "document.querySelectorAll('#assistant-conversation article').length === 4"
        )
        title = page.locator("#result-title").inner_text().strip()
        assert re.fullmatch(r"Benin (?:CPF|CEN|CPF / CEN) FCV review", title), title
        capture(page, 6, "smoke-assistant-restored-desktop")

        page.locator("#corrections summary").click()
        capture(page, 7, "smoke-secondary-correction-desktop")
        docx = output / "08-smoke-full-detailed-note.docx"
        with page.expect_download(timeout=30_000) as download_info:
            page.locator("#export-docx").click()
        download_info.value.save_as(docx)
        with ZipFile(docx) as archive:
            assert archive.testzip() is None
            assert {"[Content_Types].xml", "word/document.xml"} <= set(
                archive.namelist()
            )

        page.set_viewport_size({"width": 390, "height": 844})
        page.locator("#corrections summary").click()
        page.locator("#result-tab-summary").click()
        assert page.evaluate("document.documentElement.scrollWidth <= innerWidth")
        capture(page, 9, "smoke-summary-mobile")

        assert not console_errors, console_errors
        assert not page_errors, page_errors
        context.close()
        browser.close()

    print("BROWSER_QA_PASS screenshots=8 assistant_messages_restored=4 docx=1")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-url", default="http://127.0.0.1:58422")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    main(args.base_url.rstrip("/") + "/", args.output.resolve())
