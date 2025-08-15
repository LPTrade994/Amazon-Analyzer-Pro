import subprocess
import time
import hashlib
from pathlib import Path

import requests
from playwright.sync_api import sync_playwright


def _wait_for_server(url: str, timeout: float = 60.0) -> None:
    """Wait until Streamlit server at *url* responds."""
    start = time.time()
    while time.time() - start < timeout:
        try:
            if requests.get(url).ok:
                return
        except Exception:
            pass
        time.sleep(1)
    raise RuntimeError(f"Server at {url} did not become ready in {timeout} seconds")


def test_streamlit_expand_and_df_ess(tmp_path):
    # Ensure playwright browser is available
    subprocess.run(["playwright", "install", "chromium"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    sample_file = Path(__file__).resolve().parents[1] / "sample_data" / "keepa_sample.xlsx"

    proc = subprocess.Popen(
        ["streamlit", "run", "app.py", "--server.headless=true", "--server.port=8501"],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    try:
        _wait_for_server("http://localhost:8501/healthz")

        with sync_playwright() as p:
            browser = p.chromium.launch()
            page = browser.new_page()
            page.goto("http://localhost:8501")
            # upload required files
            page.locator("input[type='file']").nth(0).set_input_files(str(sample_file))
            page.locator("input[type='file']").nth(1).set_input_files(str(sample_file))
            page.wait_for_selector("table")

            html_before = page.locator("table").inner_html()
            col_before = page.eval_on_selector("table tr", "el => el.children.length")

            page.get_by_label("Dettaglio ASIN").click()
            page.get_by_role("option").first.click()

            exp_checks = {
                "Price Regime": "Media 30g",
                "Competition Map": "Total Offer Count",
                "Amazon Risk & Events": "%Amazon Buy Box 30g",
                "Quality & Returns": "Return Rate",
            }
            for label, snippet in exp_checks.items():
                page.get_by_text(label, exact=True).click()
                page.wait_for_selector(f"text={snippet}")

            html_after = page.locator("table").inner_html()
            col_after = page.eval_on_selector("table tr", "el => el.children.length")

            assert col_before == col_after
            assert hashlib.md5(html_before.encode()).hexdigest() == hashlib.md5(html_after.encode()).hexdigest()
            browser.close()
    finally:
        proc.terminate()
        try:
            proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            proc.kill()
