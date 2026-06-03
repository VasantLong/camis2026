from __future__ import annotations

import logging

from playwright.sync_api import sync_playwright, Browser, Page

from app.config import settings

logger = logging.getLogger(__name__)

CDP_URL = "http://127.0.0.1:9222"
VIEWPORT = {"width": 1280, "height": 900}


class ReportRenderer:
    def __init__(self, frontend_url: str | None = None):
        self.frontend_url = (frontend_url or settings.frontend_url).rstrip("/")

    def render_pdf(self, month: str, data_key: str, token: str) -> bytes:
        url = f"{self.frontend_url}/reports/monthly/{month}?token={token}&data_key={data_key}"
        logger.info("playwright rendering report url=%s", url)

        with sync_playwright() as p:
            browser = self._connect_or_launch(p)
            page = self._new_page(browser)
            try:
                page.goto(url, wait_until="networkidle", timeout=30_000)
                page.wait_for_selector(".chart-ready", timeout=20_000)
                page.wait_for_timeout(1500)
                return page.pdf(format="A4", print_background=True)
            finally:
                page.close()
                if not self._is_cdp:
                    browser.close()

    def _connect_or_launch(self, p) -> Browser:
        try:
            browser = p.chromium.connect_over_cdp(CDP_URL, timeout=3_000)
            self._is_cdp = True
            logger.info("connected to CDP browser at %s", CDP_URL)
            return browser
        except Exception:
            logger.info("CDP unavailable, launching headless chromium")
            self._is_cdp = False
            return p.chromium.launch(headless=True)

    def _new_page(self, browser: Browser) -> Page:
        if self._is_cdp:
            # use existing context → opens as a tab, not new window
            ctx = browser.contexts[0] if browser.contexts else browser.new_context()
        else:
            # headless launch: fresh isolated context with fixed viewport
            ctx = browser.new_context(viewport=VIEWPORT)
        page = ctx.new_page()
        page.set_viewport_size(VIEWPORT)
        return page
