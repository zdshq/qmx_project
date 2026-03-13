from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from study_agent.config import Settings
from study_agent.reporting.reporter import DailyReporter
from study_agent.storage.db import Database
from study_agent.types import Observation, StudyAssessment, SystemContext


def test_reporter_generates_markdown(tmp_path) -> None:
    settings = Settings(
        db_path=tmp_path / "study_agent.db",
        report_dir=tmp_path / "reports",
        capture_dir=tmp_path / "captures",
    )
    database = Database(settings.db_path)
    database.init_db()

    observation = Observation(
        observed_at=datetime(2026, 3, 12, 20, 0, tzinfo=ZoneInfo("Asia/Shanghai")),
        screen_path=Path("screen.jpg"),
        camera_path=None,
        context=SystemContext(active_app="VSCode", window_title="Study - VSCode"),
    )
    assessment = StudyAssessment(
        state="studying",
        confidence=0.95,
        learning_related=True,
        is_present=True,
        is_looking_at_screen=True,
        focus_score=0.88,
        reason="test",
        distraction_signals=[],
        raw_response={},
    )
    database.insert_observation(observation, assessment)

    report_path = DailyReporter(settings, database).generate(observation.observed_at.date())
    report_text = report_path.read_text(encoding="utf-8")

    assert report_path.exists()
    assert "VSCode" in report_text
    assert str(observation.observed_at.date()) in report_text
    assert "估算专注学习时长" in report_text
