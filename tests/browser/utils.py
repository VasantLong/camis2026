from playwright.sync_api import Browser, Page

CDP = "http://127.0.0.1:9222"
BASE = "http://localhost:5173"


def create_page(browser: Browser, viewport: dict | None = None) -> Page:
    if len(browser.contexts) > 0:
        context = browser.contexts[0]
    else:
        context = browser.new_context()
    return context.new_page()
