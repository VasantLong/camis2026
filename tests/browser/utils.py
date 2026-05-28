from playwright.sync_api import Browser, Page

CDP = "http://127.0.0.1:9222"
BASE = "http://localhost:5173"


def create_page(browser: Browser, viewport: dict | None = None) -> Page:
    vp = viewport or {"width": 1280, "height": 800}
    context = browser.new_context(viewport=vp, device_scale_factor=2)
    return context.new_page()
