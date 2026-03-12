"""Camera capture collection."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path

import cv2


class CameraCapturer:
    """Capture still images from the default camera device."""

    def __init__(self, capture_dir: Path, camera_index: int) -> None:
        """Initialize the camera output directory and device index."""
        # Directory that stores captured camera images.
        self.capture_dir = capture_dir / "camera"
        self.capture_dir.mkdir(parents=True, exist_ok=True)
        # OpenCV camera device index.
        self.camera_index = camera_index

    def capture(self, timestamp: datetime) -> Path | None:
        """Capture one camera frame and return its path, or `None` on failure."""
        # Output file path for the current camera capture.
        output_path = self.capture_dir / f"camera_{timestamp.strftime('%Y%m%d_%H%M%S')}.jpg"
        # Video device handle for the configured camera index.
        video = cv2.VideoCapture(self.camera_index)
        if not video.isOpened():
            video.release()
            return None
        # Whether frame capture succeeded and the returned frame data.
        success, frame = video.read()
        video.release()
        if not success:
            return None
        cv2.imwrite(str(output_path), frame)
        return output_path
