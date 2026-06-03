from __future__ import annotations

import logging

from playwright.sync_api import sync_playwright, Browser, Page, Error as PwError

from app.config import settings

logger = logging.getLogger(__name__)

CDP_URL = "http://127.0.0.1:9222"
VIEWPORT = {"width": 1280, "height": 900}


class ReportRenderError(Exception):
    """PDF 渲染失败"""


class ReportRenderer:
    def __init__(self, frontend_url: str | None = None):
        self.frontend_url = (frontend_url or settings.frontend_url).rstrip("/")

    def render_pdf(self, month: str, data_key: str, token: str) -> bytes:
        url = f"{self.frontend_url}/reports/monthly/{month}?token={token}&data_key={data_key}"
        logger.info("playwright rendering report url=%s", url)

        with sync_playwright() as p:
            browser, is_cdp = self._get_browser(p)
            page = self._new_page(browser, is_cdp)
            try:
                page.goto(url, wait_until="networkidle", timeout=30_000)
                page.wait_for_selector(".chart-ready", timeout=20_000)
                page.wait_for_timeout(1500)
                return page.pdf(format="A4", print_background=True)
            finally:
                page.close()
                if not is_cdp:
                    browser.close()

    def _get_browser(self, p) -> tuple[Browser, bool]:
        try:
            browser = p.chromium.launch(headless=True)
            logger.info("launched headless chromium")
            return browser, False
        except PwError as e:
            logger.warning("headless launch failed: %s, trying CDP", e)
            try:
                browser = p.chromium.connect_over_cdp(CDP_URL, timeout=3_000)
                logger.info("connected to CDP browser at %s", CDP_URL)
                return browser, True
            except PwError:
                raise ReportRenderError(
                    "无法启动 Chromium 浏览器，请安装 playwright chromium 或启动 Edge 调试模式"
                )

    def _new_page(self, browser: Browser, is_cdp: bool) -> Page:
        if is_cdp:
            ctx = browser.contexts[0] if browser.contexts else browser.new_context()
        else:
            ctx = browser.new_context(viewport=VIEWPORT)
        page = ctx.new_page()
        page.set_viewport_size(VIEWPORT)
        return page
