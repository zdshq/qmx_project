"""Environment diagnostics for quick setup and debugging."""

from __future__ import annotations

import platform
import shutil
import sqlite3
from dataclasses import dataclass

from study_agent.config import Settings


@dataclass(slots=True)
class CheckResult:
    """Represent one diagnostic check result."""

    name: str
    ok: bool
    detail: str


class EnvironmentDoctor:
    """Run environment checks for the local study agent project."""

    def __init__(self, settings: Settings) -> None:
        """Store runtime settings for diagnostics."""
        self.settings = settings

    def run(self) -> list[CheckResult]:
        """Run all supported environment checks."""
        system_name = platform.system()
        return [
            self._check_python(),
            self._check_paths(),
            self._check_database_path(),
            self._check_active_window_support(system_name),
            self._check_idle_support(system_name),
            self._check_capture_settings(),
            self._check_model_settings(),
        ]

    def render_text(self, results: list[CheckResult]) -> str:
        """Render diagnostic results as plain text."""
        lines = ["Study Agent Doctor", ""]
        for result in results:
            status = "OK" if result.ok else "WARN"
            lines.append(f"[{status}] {result.name}: {result.detail}")
        warnings = sum(1 for item in results if not item.ok)
        lines.extend(["", f"Summary: {len(results)} checks, {warnings} warning(s)."])
        return "\n".join(lines)

    def _check_python(self) -> CheckResult:
        """Check the current Python runtime information."""
        return CheckResult(
            name="python",
            ok=True,
            detail=f"{platform.python_version()} on {platform.system()}",
        )

    def _check_paths(self) -> CheckResult:
        """Check whether key runtime directories are creatable."""
        paths = [
            self.settings.capture_dir,
            self.settings.report_dir,
            self.settings.db_path.parent,
        ]
        for path in paths:
            path.mkdir(parents=True, exist_ok=True)
        detail = ", ".join(str(path) for path in paths)
        return CheckResult(name="paths", ok=True, detail=detail)

    def _check_database_path(self) -> CheckResult:
        """Check whether the SQLite database path is writable."""
        db_path = self.settings.db_path
        db_path.parent.mkdir(parents=True, exist_ok=True)
        try:
            connection = sqlite3.connect(db_path)
            connection.execute("SELECT 1")
            connection.close()
            return CheckResult(name="database", ok=True, detail=str(db_path))
        except sqlite3.Error as error:
            return CheckResult(name="database", ok=False, detail=str(error))

    def _check_active_window_support(self, system_name: str) -> CheckResult:
        """Check whether active-window lookup is supported on this platform."""
        if system_name == "Windows":
            return CheckResult(
                name="active_window",
                ok=True,
                detail="Win32 foreground window API is available",
            )
        xdotool_path = shutil.which("xdotool")
        if xdotool_path:
            return CheckResult(name="active_window", ok=True, detail=f"xdotool: {xdotool_path}")
        return CheckResult(
            name="active_window",
            ok=False,
            detail="xdotool not installed; active window title may be unavailable",
        )

    def _check_idle_support(self, system_name: str) -> CheckResult:
        """Check whether idle-time lookup is supported on this platform."""
        if system_name == "Windows":
            return CheckResult(
                name="idle_detection",
                ok=True,
                detail="Win32 GetLastInputInfo API is available",
            )
        tool_path = shutil.which("xprintidle")
        if tool_path:
            return CheckResult(name="idle_detection", ok=True, detail=f"xprintidle: {tool_path}")
        return CheckResult(
            name="idle_detection",
            ok=False,
            detail="not installed; idle-based away detection will be unavailable",
        )

    def _check_capture_settings(self) -> CheckResult:
        """Check whether sampling and retention settings look reasonable."""
        interval_seconds = self.settings.loop_interval_sec
        retention_hours = self.settings.capture_retention_hours
        return CheckResult(
            name="capture",
            ok=interval_seconds >= 60 and retention_hours > 0,
            detail=(
                f"screen-only mode, interval={interval_seconds}s, retention={retention_hours}h, "
                f"idle_away={self.settings.idle_away_seconds}s"
            ),
        )

    def _check_model_settings(self) -> CheckResult:
        """Check whether model-related settings look usable."""
        if not self.settings.model_enabled:
            return CheckResult(
                name="model",
                ok=False,
                detail="model integration is disabled; heuristic fallback will be used",
            )
        return CheckResult(
            name="model",
            ok=True,
            detail=f"{self.settings.model_name} @ {self.settings.model_base_url}",
        )
