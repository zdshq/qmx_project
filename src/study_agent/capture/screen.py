"""Screen capture collection."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path

from mss import mss
from mss.exception import ScreenShotError
from PIL import Image


class ScreenCapturer:
    """Capture screenshots from the primary display."""

    def __init__(self, capture_dir: Path) -> None:
        """Initialize the output directory for screen captures."""
        # Directory that stores captured screen images.
        self.capture_dir = capture_dir / "screen"
        self.capture_dir.mkdir(parents=True, exist_ok=True)

    def capture(self, timestamp: datetime) -> Path | None:
        """Capture one screenshot and return its path, or `None` on failure."""
        # Output file path for the current screenshot.
        output_path = self.capture_dir / f"screen_{timestamp.strftime('%Y%m%d_%H%M%S')}.jpg"
        try:
            with mss() as screen_session:
                # `monitors[1]` is the primary monitor; `monitors[0]` is the virtual full area.
                if len(screen_session.monitors) < 2:
                    return None
                # Selected monitor region.
                monitor = screen_session.monitors[1]
                # Raw screenshot buffer.
                screenshot = screen_session.grab(monitor)
                # Pillow image converted from the raw RGB buffer.
                image = Image.frombytes("RGB", screenshot.size, screenshot.rgb)
                image.save(output_path, quality=88)
            return output_path
        except ScreenShotError:
            return None
