import base64
import json
import os
import subprocess
import sys
import threading
import urllib.request
from pathlib import Path

from playwright.sync_api import Browser, Page

CDP = "http://127.0.0.1:9222"
BASE = "http://localhost:5173"
API = "http://localhost:8000"
RECORDINGS = Path(__file__).parent / "recordings"
LOGS = Path(__file__).parent / "logs"

# ── shared test helpers ──

_failed = 0


def check(cond: bool, msg: str) -> None:
    global _failed
    if cond:
        print(f"  OK: {msg}")
    else:
        _failed += 1
        print(f"  FAIL: {msg}")


def get_failed() -> int:
    return _failed


def login_as(page: Page, email: str, password: str) -> None:
    page.context.clear_cookies()
    page.goto(f"{BASE}/login")
    page.wait_for_load_state("networkidle")
    page.fill('input[placeholder="邮箱"]', email)
    page.fill('input[type="password"]', password)
    page.click('button[type="submit"]')
    page.wait_for_timeout(3000)
    page.wait_for_load_state("networkidle")


def sidebar_nav(page: Page, text: str, submenu: str = "活动管理") -> None:
    sub = page.locator(f'.ant-menu-submenu-title:has-text("{submenu}")')
    if sub.count() > 0 and sub.first.get_attribute("aria-expanded") != "true":
        sub.first.click()
        page.wait_for_timeout(400)
    it = page.locator(f'.ant-menu-item:has-text("{text}")').first
    if it.count() > 0:
        it.click()
        page.wait_for_timeout(1500)
        page.wait_for_load_state("networkidle")


def navigate_to_activity(page: Page, name: str) -> None:
    """Sidebar → 全部活动 → click activity link by name."""
    sidebar_nav(page, "全部活动")
    page.wait_for_timeout(1000)
    page.wait_for_selector(".ant-table-tbody tr", timeout=5000)
    page.wait_for_timeout(500)
    link = page.locator(f'a:has-text("{name}")').first
    link.click()
    page.wait_for_timeout(2000)
    page.wait_for_load_state("networkidle")


def api_post(path: str, body: dict, token: str | None) -> dict:
    data = json.dumps(body).encode()
    hdrs = {"Content-Type": "application/json"}
    if token:
        hdrs["Authorization"] = f"Bearer {token}"
    req = urllib.request.Request(f"{API}{path}", data=data, headers=hdrs)
    return json.loads(urllib.request.urlopen(req).read())


def api_get(path: str, token: str) -> dict:
    req = urllib.request.Request(f"{API}{path}",
        headers={"Authorization": f"Bearer {token}"})
    return json.loads(urllib.request.urlopen(req).read())


def api_patch(path: str, body: dict, token: str) -> dict:
    data = json.dumps(body).encode()
    req = urllib.request.Request(f"{API}{path}", data=data, method="PATCH",
        headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"})
    return json.loads(urllib.request.urlopen(req).read())


def api_put(path: str, body: dict, token: str) -> dict:
    data = json.dumps(body).encode()
    req = urllib.request.Request(f"{API}{path}", data=data, method="PUT",
        headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"})
    return json.loads(urllib.request.urlopen(req).read())


def login_api(email: str, password: str) -> tuple[str, str]:
    resp = api_post("/auth/login", {"email": email, "password": password}, None)
    token = resp["access_token"]
    user = api_get("/auth/me", token)
    return token, user["id"]


class _TeeWriter:
    def __init__(self, *files):
        self._files = files

    def write(self, text):
        for f in self._files:
            f.write(text)

    def flush(self):
        for f in self._files:
            f.flush()


def setup_logging(name: str) -> None:
    LOGS.mkdir(exist_ok=True)
    log_file = open(LOGS / f"{name}.log", "w")
    sys.stdout = _TeeWriter(sys.__stdout__, log_file)


def capture_console(page: Page, name: str) -> list[str]:
    """Capture browser console messages and page errors, write to logs/{name}_console.log."""
    LOGS.mkdir(exist_ok=True)
    logf = open(LOGS / f"{name}_console.log", "w")
    errors: list[str] = []

    def on_console(msg):
        line = f"[{msg.type}] {msg.text}"
        errors.append(line)
        logf.write(line + "\n")
        logf.flush()

    def on_pageerror(err):
        line = f"PAGE_ERROR: {err}"
        errors.append(line)
        logf.write(line + "\n")
        logf.flush()

    page.on("console", on_console)
    page.on("pageerror", on_pageerror)
    return errors


def create_page(browser: Browser, viewport: dict | None = None) -> Page:
    if len(browser.contexts) > 0:
        context = browser.contexts[0]
    else:
        context = browser.new_context()
    return context.new_page()


class ScreencastRecorder:
    """Record browser tab via CDP Page.startScreencast. Frames saved as JPEG, merged to MP4 on stop."""

    def __init__(self, page: Page, output_dir: Path, fps: int = 10):
        self.page = page
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.fps = fps
        self._frames: list[str] = []
        self._lock = threading.Lock()
        self._cdp = page.context.new_cdp_session(page)

    def _on_frame(self, params: dict) -> None:
        sid = params.get("sessionId")
        data = params.get("data")
        if data:
            with self._lock:
                self._frames.append(data)
        self._cdp.send("Page.screencastFrameAck", {"sessionId": sid})

    def start(self) -> None:
        self._cdp.on("Page.screencastFrame", self._on_frame)
        self._cdp.send("Page.startScreencast", {
            "format": "jpeg",
            "quality": 80,
            "everyNthFrame": 1,
        })

    def stop(self) -> Path | None:
        self._cdp.send("Page.stopScreencast")

        if not self._frames:
            return None

        frames_dir = self.output_dir / "frames"
        frames_dir.mkdir(exist_ok=True)

        for i, data in enumerate(self._frames):
            (frames_dir / f"frame_{i:04d}.jpg").write_bytes(base64.b64decode(data))

        video_path = self.output_dir / "recording.mp4"
        result = subprocess.run([
            "ffmpeg", "-y", "-framerate", str(self.fps),
            "-i", str(frames_dir / "frame_%04d.jpg"),
            "-vf", "pad=ceil(iw/2)*2:ceil(ih/2)*2",
            "-c:v", "libx264", "-pix_fmt", "yuv420p",
            str(video_path),
        ], capture_output=True, text=True, timeout=60)

        if result.returncode != 0:
            print(f"  [video] ffmpeg failed: {result.stderr[-200:]}")
            return None

        print(f"  [video] {video_path} ({video_path.stat().st_size} bytes, {len(self._frames)} frames)")
        return video_path


def start_recording(page: Page, name: str) -> ScreencastRecorder | None:
    """Start CDP screencast if RECORD env var is set. Usage:

        recorder = start_recording(page, "01_auth")
        ...
        if recorder:
            recorder.stop()
    """
    if not os.environ.get("RECORD"):
        return None
    recorder = ScreencastRecorder(page, RECORDINGS / name)
    recorder.start()
    return recorder
