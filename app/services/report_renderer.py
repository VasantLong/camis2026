from __future__ import annotations

import logging

import httpx

from app.config import settings

logger = logging.getLogger(__name__)


class ReportRenderError(Exception):
    """PDF 渲染失败"""


class ReportRenderer:
    def __init__(self, frontend_url: str | None = None, svc_url: str | None = None):
        self.frontend_url = (frontend_url or settings.frontend_url).rstrip("/")
        self.svc_url = (svc_url or settings.playwright_svc_url).rstrip("/")

    async def render_pdf(self, month: str, data_key: str, token: str) -> bytes:
        url = f"{self.frontend_url}/reports/monthly/{month}?token={token}&data_key={data_key}"
        logger.info("rendering report via playwright-svc url=%s", url)

        async with httpx.AsyncClient(timeout=60) as client:
            resp = await client.post(
                f"{self.svc_url}/render",
                json={"url": url},
            )
            if resp.status_code != 200:
                detail = resp.text
                logger.error("playwright-svc error status=%s body=%s", resp.status_code, detail)
                raise ReportRenderError(f"PDF 渲染失败: {detail}")
            return resp.content
