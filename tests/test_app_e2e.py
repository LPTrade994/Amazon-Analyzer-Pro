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
    # Ensure playwright browser and dependencies are available
    subprocess.run(["playwright", "install", "chromium"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    subprocess.run(["playwright", "install-deps"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

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

            # ensure uploaded data persists when switching presets
            for preset in ["Flip veloce", "Margine alto", "Volume/Rotazione"]:
                page.get_by_role("button", name=preset).click()
                page.wait_for_selector("table")
                assert page.locator("table").is_visible()
            browser.close()
    finally:
        proc.terminate()
        try:
            proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            proc.kill()


def test_preset_save_and_load(tmp_path):
    subprocess.run(["playwright", "install", "chromium"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    subprocess.run(["playwright", "install-deps"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    repo_root = Path(__file__).resolve().parents[1]
    sample_file = repo_root / "sample_data" / "keepa_sample.xlsx"
    app_path = repo_root / "app.py"

    proc = subprocess.Popen(
        ["streamlit", "run", str(app_path), "--server.headless=true", "--server.port=8502"],
        cwd=tmp_path,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    try:
        _wait_for_server("http://localhost:8502/healthz")

        with sync_playwright() as p:
            browser = p.chromium.launch()
            page = browser.new_page()
            page.goto("http://localhost:8502")

            # upload deterministic sample files
            page.locator("input[type='file']").nth(0).set_input_files(str(sample_file))
            page.locator("input[type='file']").nth(1).set_input_files(str(sample_file))

            # change a couple of sliders and number inputs
            profit_slider = page.get_by_label("Profit", exact=True)
            profit_slider.evaluate(
                "el => {el.value = 55; el.dispatchEvent(new Event('input', {bubbles: true})); el.dispatchEvent(new Event('change', {bubbles: true}));}"
            )
            epsilon_slider = page.get_by_label("Margine % (ε)", exact=True)
            epsilon_slider.evaluate(
                "el => {el.value = 4.4; el.dispatchEvent(new Event('input', {bubbles: true})); el.dispatchEvent(new Event('change', {bubbles: true}));}"
            )
            min_profit_input = page.get_by_label("Min Profit Amazon €", exact=True)
            min_profit_input.fill("7")

            saved_profit = float(profit_slider.get_attribute("aria-valuenow"))
            saved_epsilon = float(epsilon_slider.get_attribute("aria-valuenow"))
            saved_min_profit = float(min_profit_input.input_value())

            page.get_by_label("Preset name").fill("e2e_tmp")
            page.get_by_role("button", name="Save").click()

            preset_file = tmp_path / ".streamlit" / "score_presets" / "e2e_tmp.json"
            for _ in range(20):
                if preset_file.exists():
                    break
                time.sleep(0.5)
            else:
                raise AssertionError("preset file was not created")

            # new session to ensure defaults
            page2 = browser.new_page()
            page2.goto("http://localhost:8502")
            page2.locator("input[type='file']").nth(0).set_input_files(str(sample_file))
            page2.locator("input[type='file']").nth(1).set_input_files(str(sample_file))
            page2.locator("input[type='file']").nth(2).set_input_files(str(preset_file))
            page2.wait_for_timeout(1000)

            assert float(page2.get_by_label("Profit", exact=True).get_attribute("aria-valuenow")) == saved_profit
            assert float(page2.get_by_label("Margine % (ε)", exact=True).get_attribute("aria-valuenow")) == saved_epsilon
            assert float(page2.get_by_label("Min Profit Amazon €", exact=True).input_value()) == saved_min_profit

            browser.close()
    finally:
        proc.terminate()
        try:
            proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            proc.kill()
