"""System context collection."""

from __future__ import annotations

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
            idle_seconds=None,
            app_switch_count_5m=self._count_switches(timestamp),
        )

    def _get_active_window_title(self) -> str | None:
        """Get the current active window title via `xdotool`."""
        if shutil.which("xdotool") is None:
            return None
        try:
            # Active window identifier.
            window_id = subprocess.check_output(["xdotool", "getactivewindow"], text=True).strip()
            # Active window title string.
            title = subprocess.check_output(["xdotool", "getwindowname", window_id], text=True).strip()
            return title or None
        except (subprocess.SubprocessError, FileNotFoundError):
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
