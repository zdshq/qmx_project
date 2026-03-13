"""Captured screenshot retention cleanup."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta

from study_agent.config import Settings


@dataclass(slots=True)
class CleanupResult:
    """Store one cleanup execution result."""

    deleted_files: int
    freed_bytes: int


class CaptureCleaner:
    """Delete expired screenshots from disk."""

    def __init__(self, settings: Settings) -> None:
        """Store settings required for cleanup."""
        self.settings = settings

    def cleanup(self, now: datetime) -> CleanupResult:
        """Delete screenshots older than the retention window."""
        capture_root = self.settings.capture_dir / "screen"
        if not capture_root.exists():
            return CleanupResult(deleted_files=0, freed_bytes=0)

        cutoff = now - timedelta(hours=self.settings.capture_retention_hours)
        deleted_files = 0
        freed_bytes = 0

        for file_path in capture_root.glob("*.jpg"):
            stat = file_path.stat()
            modified_at = datetime.fromtimestamp(stat.st_mtime, tz=now.tzinfo)
            if modified_at >= cutoff:
                continue
            file_path.unlink(missing_ok=True)
            deleted_files += 1
            freed_bytes += stat.st_size

        return CleanupResult(deleted_files=deleted_files, freed_bytes=freed_bytes)
