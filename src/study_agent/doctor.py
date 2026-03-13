"""Environment diagnostics for quick setup and debugging."""

from __future__ import annotations

import platform
import shutil
import sqlite3
from dataclasses import dataclass

import cv2

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
        return [
            self._check_python(),
            self._check_paths(),
            self._check_database_path(),
            self._check_xdotool(),
            self._check_camera(),
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

    def _check_xdotool(self) -> CheckResult:
        """Check whether `xdotool` is available on the system."""
        xdotool_path = shutil.which("xdotool")
        if xdotool_path:
            return CheckResult(name="xdotool", ok=True, detail=xdotool_path)
        return CheckResult(
            name="xdotool", ok=False, detail="not installed; active window title may be unavailable"
        )

    def _check_camera(self) -> CheckResult:
        """Check whether the configured camera can be opened."""
        previous_log_level = None
        if hasattr(cv2, "getLogLevel") and hasattr(cv2, "setLogLevel"):
            previous_log_level = cv2.getLogLevel()
            cv2.setLogLevel(0)
        camera = cv2.VideoCapture(self.settings.camera_index)
        try:
            if camera.isOpened():
                return CheckResult(
                    name="camera",
                    ok=True,
                    detail=f"camera index {self.settings.camera_index} is available",
                )
            return CheckResult(
                name="camera",
                ok=False,
                detail=f"camera index {self.settings.camera_index} cannot be opened",
            )
        finally:
            camera.release()
            if previous_log_level is not None:
                cv2.setLogLevel(previous_log_level)

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
