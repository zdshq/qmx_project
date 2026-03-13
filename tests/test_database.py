from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from study_agent.storage.db import Database
from study_agent.types import Observation, StudyAssessment, SystemContext


def _make_observation(index: int) -> tuple[Observation, StudyAssessment]:
    observed_at = datetime(2026, 3, 12, 20, index, tzinfo=ZoneInfo("Asia/Shanghai"))
    observation = Observation(
        observed_at=observed_at,
        screen_path=Path(f"screen_{index}.jpg"),
        camera_path=Path(f"camera_{index}.jpg"),
        context=SystemContext(
            active_app="VSCode",
            window_title=f"Session {index} - VSCode",
            idle_seconds=0.0,
            app_switch_count_5m=index,
        ),
    )
    assessment = StudyAssessment(
        state="studying" if index % 2 == 0 else "distracted",
        confidence=0.9,
        learning_related=index % 2 == 0,
        is_present=True,
        is_looking_at_screen=True,
        focus_score=0.8 if index % 2 == 0 else 0.3,
        reason="test",
        distraction_signals=[],
        raw_response={"index": index},
    )
    return observation, assessment


def test_database_recent_and_daily_summary(tmp_path) -> None:
    database = Database(tmp_path / "study_agent.db")
    database.init_db()

    for index in range(4):
        observation, assessment = _make_observation(index)
        database.insert_observation(observation, assessment)

    recent = database.summarize_recent(limit=4)
    daily = database.summarize_day(observation.observed_at.date(), "Asia/Shanghai")

    assert recent["recent_samples"] == 4
    assert recent["latest_state"] in {"studying", "distracted"}
    assert daily["sample_count"] == 4
    assert daily["avg_focus_score"] > 0
    assert daily["top_apps"][0][0] == "VSCode"
