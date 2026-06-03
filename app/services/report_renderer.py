from __future__ import annotations

import logging

import httpx

from app.config import settings

logger = logging.getLogger(__name__)


class ReportRenderError(Exception):
    """PDF 渲染失败"""


class ReportRenderer:
    def __init__(self, svc_url: str | None = None):
        self.svc_url = (svc_url or settings.playwright_svc_url).rstrip("/")

    async def render_pdf(self, month: str, data_key: str, token: str) -> bytes:
        logger.info("rendering report via playwright-svc month=%s data_key=%s", month, data_key)

        async with httpx.AsyncClient(timeout=60) as client:
            resp = await client.post(
                f"{self.svc_url}/render",
                json={"month": month, "data_key": data_key, "token": token},
            )
            if resp.status_code != 200:
                detail = resp.text
                logger.error("playwright-svc error status=%s body=%s", resp.status_code, detail)
                raise ReportRenderError(f"PDF 渲染失败: {detail}")
            return resp.content
