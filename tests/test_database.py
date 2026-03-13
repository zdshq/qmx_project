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
    daily = database.summarize_day(
        observation.observed_at.date(),
        "Asia/Shanghai",
        sample_interval_seconds=480,
    )

    assert recent["recent_samples"] == 4
    assert len(recent["recent_records"]) == 4
    assert recent["recent_records"][0]["observed_at"].startswith("2026-03-12T20:00")
    assert recent["recent_records"][-1]["state"] in {"studying", "distracted"}
    assert daily["sample_count"] == 4
    assert daily["avg_focus_score"] > 0
    assert daily["top_apps"][0][0] == "VSCode"
    assert daily["focused_study_minutes"] == 16
    assert daily["distracted_minutes"] == 16


def test_recent_screen_paths_returns_old_to_new_order(tmp_path) -> None:
    database = Database(tmp_path / "study_agent.db")
    database.init_db()

    for index in range(3):
        observation, assessment = _make_observation(index)
        database.insert_observation(observation, assessment)

    screen_paths = database.recent_screen_paths(limit=2)

    assert len(screen_paths) == 2
    assert screen_paths[0].name == "screen_1.jpg"
    assert screen_paths[1].name == "screen_2.jpg"


def test_recent_screen_frames_returns_time_and_path(tmp_path) -> None:
    database = Database(tmp_path / "study_agent.db")
    database.init_db()

    for index in range(3):
        observation, assessment = _make_observation(index)
        database.insert_observation(observation, assessment)

    frames = database.recent_screen_frames(limit=2)

    assert len(frames) == 2
    assert frames[0]["observed_at"].startswith("2026-03-12T20:01")
    assert frames[1]["screen_path"].name == "screen_2.jpg"
