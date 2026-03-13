from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from PIL import Image

from study_agent.agent import StudyAgent
from study_agent.config import Settings
from study_agent.types import Observation, SystemContext


def _save_image(path: Path, color: tuple[int, int, int]) -> None:
    Image.new("RGB", (32, 32), color=color).save(path)


def test_agent_marks_away_for_three_static_frames(tmp_path) -> None:
    settings = Settings(
        db_path=tmp_path / "study_agent.db",
        report_dir=tmp_path / "reports",
        capture_dir=tmp_path / "captures",
        idle_away_seconds=600,
        model_enabled=False,
    )
    agent = StudyAgent(settings)
    screen_dir = settings.capture_dir / "screen"
    screen_dir.mkdir(parents=True, exist_ok=True)

    old_one = screen_dir / "screen_old_1.jpg"
    old_two = screen_dir / "screen_old_2.jpg"
    current = screen_dir / "screen_current.jpg"
    _save_image(old_one, (255, 255, 255))
    _save_image(old_two, (255, 255, 255))
    _save_image(current, (255, 255, 255))

    timestamp = datetime(2026, 3, 13, 20, 0, tzinfo=ZoneInfo("Asia/Shanghai"))
    context = SystemContext(
        active_app="VSCode",
        window_title="Static - VSCode",
        idle_seconds=1200.0,
    )
    recent_observation = Observation(
        observed_at=timestamp,
        screen_path=old_one,
        camera_path=None,
        context=context,
    )
    agent.database.insert_observation(
        recent_observation,
        agent.model._heuristic_assessment(recent_observation),
    )
    recent_observation = Observation(
        observed_at=timestamp,
        screen_path=old_two,
        camera_path=None,
        context=context,
    )
    agent.database.insert_observation(
        recent_observation,
        agent.model._heuristic_assessment(recent_observation),
    )

    current_observation = Observation(
        observed_at=timestamp,
        screen_path=current,
        camera_path=None,
        context=context,
    )
    assessment = agent._assess(current_observation, agent.database.summarize_recent())

    assert assessment.state == "away"
    assert assessment.reason == "idle + three-frame static rule triggered"
