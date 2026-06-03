"""Playwright PDF rendering microservice.

POST /render  { "url": "http://frontend/reports/monthly/..." }
→ PDF bytes (application/pdf)
"""
import logging

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from playwright.sync_api import sync_playwright

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("playwright-svc")

app = FastAPI(title="Playwright Render Service")

VIEWPORT = {"width": 1280, "height": 900}


class RenderRequest(BaseModel):
    url: str


@app.post("/render")
def render_pdf(req: RenderRequest):
    logger.info("rendering url=%s", req.url)
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        try:
            page = browser.new_page(viewport=VIEWPORT)
            page.goto(req.url, wait_until="networkidle", timeout=30_000)
            page.wait_for_selector(".chart-ready", timeout=20_000)
            page.wait_for_timeout(1500)
            pdf_bytes = page.pdf(format="A4", print_background=True)
            return _pdf_response(pdf_bytes)
        except Exception as e:
            logger.exception("render failed")
            raise HTTPException(500, f"PDF rendering failed: {e}")
        finally:
            browser.close()


def _pdf_response(data: bytes):
    from fastapi.responses import Response
    return Response(content=data, media_type="application/pdf")
