"""Playwright PDF rendering microservice.

POST /render  { "month": "2026-06", "data_key": "uuid", "token": "jwt" }
→ PDF bytes (application/pdf)

Uses FRONTEND_URL env var to construct the report page URL.
"""
import logging
import os

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from playwright.sync_api import sync_playwright

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("playwright-svc")

FRONTEND_URL = os.getenv("FRONTEND_URL", "http://localhost:5173").rstrip("/")

app = FastAPI(title="Playwright Render Service")

VIEWPORT = {"width": 1280, "height": 900}


class RenderRequest(BaseModel):
    month: str
    data_key: str
    token: str


@app.post("/render")
def render_pdf(req: RenderRequest):
    url = f"{FRONTEND_URL}/reports/monthly/{req.month}?token={req.token}&data_key={req.data_key}"
    logger.info("rendering url=%s", url)
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        try:
            page = browser.new_page(viewport=VIEWPORT)
            page.goto(url, wait_until="networkidle", timeout=30_000)
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
