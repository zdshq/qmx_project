from datetime import datetime
from zoneinfo import ZoneInfo

from study_agent.config import Settings
from study_agent.reporting.scheduler import ReportScheduler


def test_scheduler_before_deadline_does_not_trigger() -> None:
    settings = Settings(report_hour=23, report_minute=0, timezone="Asia/Shanghai")
    scheduler = ReportScheduler(settings)
    now = datetime(2026, 3, 12, 22, 59, tzinfo=ZoneInfo("Asia/Shanghai"))

    assert scheduler.should_generate(now) is False


def test_scheduler_after_deadline_triggers_once() -> None:
    settings = Settings(report_hour=23, report_minute=0, timezone="Asia/Shanghai")
    scheduler = ReportScheduler(settings)
    now = datetime(2026, 3, 12, 23, 1, tzinfo=ZoneInfo("Asia/Shanghai"))

    assert scheduler.should_generate(now) is True
    scheduler.mark_generated(now.date())
    assert scheduler.should_generate(now) is False
