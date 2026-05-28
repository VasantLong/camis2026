import base64
import os
import subprocess
import threading
from pathlib import Path

from playwright.sync_api import Browser, Page

CDP = "http://127.0.0.1:9222"
BASE = "http://localhost:5173"
RECORDINGS = Path(__file__).parent / "recordings"


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
