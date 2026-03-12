"""Daily report scheduling."""

from __future__ import annotations

from datetime import date, datetime, timedelta

from study_agent.config import Settings


class ReportScheduler:
    """Decide when a daily report should be generated."""

    def __init__(self, settings: Settings) -> None:
        """Initialize scheduler settings and generation state."""
        # Runtime settings used for report scheduling.
        self.settings = settings
        # Last day for which a report was generated, used to avoid duplicates.
        self.last_generated_for: date | None = None

    def should_generate(self, now: datetime) -> bool:
        """Return whether a report should be generated at the current time."""
        # Current calendar day.
        today = now.date()
        # Scheduled trigger time for the current day.
        scheduled_time = now.replace(
            hour=self.settings.report_hour,
            minute=self.settings.report_minute,
            second=0,
            microsecond=0,
        )
        if now < scheduled_time:
            return False
        if self.last_generated_for == today:
            return False
        return True

    def mark_generated(self, report_day: date) -> None:
        """Mark a specific day as already reported."""
        self.last_generated_for = report_day

    def report_target_day(self, now: datetime) -> date:
        """Compute the day for which the report should be generated."""
        # Scheduled report time for the current calendar day.
        scheduled = now.replace(
            hour=self.settings.report_hour,
            minute=self.settings.report_minute,
            second=0,
            microsecond=0,
        )
        if now >= scheduled:
            return now.date()
        return (now - timedelta(days=1)).date()
