"""System context collection."""

from __future__ import annotations

import ctypes
import platform
import shutil
import subprocess
from collections import deque
from dataclasses import dataclass
from datetime import datetime, timedelta

from study_agent.types import SystemContext


@dataclass(slots=True)
class WindowSnapshot:
    """Store one historical window-title record."""

    # Timestamp when the snapshot was recorded.
    taken_at: datetime
    # Window title recorded at that time.
    window_title: str | None


class SystemContextCollector:
    """Collect window metadata and derive lightweight context features."""

    def __init__(self) -> None:
        """Initialize the rolling window-title history."""
        # Recent window-title history used to estimate switch frequency.
        self.window_history: deque[WindowSnapshot] = deque(maxlen=600)

    def collect(self, timestamp: datetime) -> SystemContext:
        """Collect the current system context."""
        # Title of the current active window.
        window_title = self._get_active_window_title()
        self.window_history.append(WindowSnapshot(taken_at=timestamp, window_title=window_title))
        return SystemContext(
            active_app=self._guess_active_app(window_title),
            window_title=window_title,
            idle_seconds=self._get_idle_seconds(),
            app_switch_count_5m=self._count_switches(timestamp),
        )

    def _get_active_window_title(self) -> str | None:
        """Get the current active window title on the current platform."""
        if platform.system() == "Windows":
            return self._get_active_window_title_windows()
        return self._get_active_window_title_linux()

    def _get_active_window_title_linux(self) -> str | None:
        """Get the current active window title via `xdotool` on Linux."""
        if shutil.which("xdotool") is None:
            return None
        try:
            # Active window identifier.
            window_id = subprocess.check_output(["xdotool", "getactivewindow"], text=True).strip()
            # Active window title string.
            title = subprocess.check_output(
                ["xdotool", "getwindowname", window_id], text=True
            ).strip()
            return title or None
        except (subprocess.SubprocessError, FileNotFoundError):
            return None

    def _get_active_window_title_windows(self) -> str | None:
        """Get the current active window title via Win32 API on Windows."""
        user32 = getattr(ctypes, "windll", None)
        if user32 is None:
            return None
        try:
            handle = ctypes.windll.user32.GetForegroundWindow()
            if handle == 0:
                return None
            length = ctypes.windll.user32.GetWindowTextLengthW(handle)
            if length <= 0:
                return None
            buffer = ctypes.create_unicode_buffer(length + 1)
            ctypes.windll.user32.GetWindowTextW(handle, buffer, length + 1)
            title = buffer.value.strip()
            return title or None
        except AttributeError:
            return None

    def _guess_active_app(self, window_title: str | None) -> str | None:
        """Infer an application name from the current window title."""
        if not window_title:
            return None
        for separator in (" - ", " — ", " | "):
            if separator in window_title:
                return window_title.split(separator)[-1].strip() or None
        return window_title[:60]

    def _count_switches(self, now: datetime) -> int:
        """Count window-title changes during the last 5 minutes."""
        # Lower time bound for the recent switch window.
        cutoff = now - timedelta(minutes=5)
        # Window-title sequence collected within the recent window.
        relevant = [item.window_title for item in self.window_history if item.taken_at >= cutoff]
        # Total number of detected title changes.
        switches = 0
        # Last non-empty title seen in the sequence.
        last_title = None
        for title in relevant:
            if last_title is not None and title and title != last_title:
                switches += 1
            if title:
                last_title = title
        return switches

    def _get_idle_seconds(self) -> float | None:
        """Return desktop idle seconds on the current platform."""
        if platform.system() == "Windows":
            return self._get_idle_seconds_windows()
        return self._get_idle_seconds_linux()

    def _get_idle_seconds_linux(self) -> float | None:
        """Return desktop idle seconds via `xprintidle` on Linux."""
        if shutil.which("xprintidle") is None:
            return None
        try:
            idle_ms = subprocess.check_output(["xprintidle"], text=True).strip()
            return round(float(idle_ms) / 1000.0, 3)
        except (subprocess.SubprocessError, ValueError):
            return None

    def _get_idle_seconds_windows(self) -> float | None:
        """Return desktop idle seconds via Win32 `GetLastInputInfo` on Windows."""
        if not hasattr(ctypes, "windll"):
            return None

        class LASTINPUTINFO(ctypes.Structure):
            _fields_ = [("cbSize", ctypes.c_uint), ("dwTime", ctypes.c_uint)]

        try:
            user32 = ctypes.windll.user32
            kernel32 = ctypes.windll.kernel32
            last_input_info = LASTINPUTINFO()
            last_input_info.cbSize = ctypes.sizeof(LASTINPUTINFO)
            if user32.GetLastInputInfo(ctypes.byref(last_input_info)) == 0:
                return None
            elapsed_ms = kernel32.GetTickCount() - last_input_info.dwTime
            return round(float(elapsed_ms) / 1000.0, 3)
        except AttributeError:
            return None
