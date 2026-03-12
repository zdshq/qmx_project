"""Application configuration loading."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from zoneinfo import ZoneInfo

from dotenv import load_dotenv


@dataclass(slots=True)
class Settings:
    """Store all runtime settings for the agent."""

    # Local timezone used for sampling timestamps and daily report scheduling.
    timezone: str = "Asia/Shanghai"
    # SQLite database file path.
    db_path: Path = Path("data/study_agent.db")
    # Output directory for daily reports.
    report_dir: Path = Path("reports")
    # Storage directory for screenshots and camera captures.
    capture_dir: Path = Path("data/captures")
    # Screen capture interval in seconds.
    screen_interval_sec: int = 5
    # Camera capture interval in seconds.
    camera_interval_sec: int = 5
    # Main loop interval in seconds.
    loop_interval_sec: int = 5
    # Hour of daily report generation in local time.
    report_hour: int = 23
    # Minute of daily report generation in local time.
    report_minute: int = 0
    # Whether the local multimodal model endpoint is enabled.
    model_enabled: bool = False
    # Base URL of the local OpenAI-compatible model endpoint.
    model_base_url: str = "http://127.0.0.1:11434/v1"
    # Model name used for inference.
    model_name: str = "qwen2.5vl:latest"
    # Optional API key for the model endpoint.
    model_api_key: str = ""
    # Default camera device index.
    camera_index: int = 0

    @property
    def tzinfo(self) -> ZoneInfo:
        """Return the timezone object for the current settings."""
        return ZoneInfo(self.timezone)



def _get_bool(name: str, default: bool) -> bool:
    """Read a boolean value from an environment variable."""
    raw_value = os.getenv(name)
    if raw_value is None:
        return default
    return raw_value.lower() in {"1", "true", "yes", "on"}



def load_settings() -> Settings:
    """Load settings from `.env` and process environment variables."""
    load_dotenv()
    return Settings(
        timezone=os.getenv("STUDY_AGENT_TIMEZONE", "Asia/Shanghai"),
        db_path=Path(os.getenv("STUDY_AGENT_DB_PATH", "data/study_agent.db")),
        report_dir=Path(os.getenv("STUDY_AGENT_REPORT_DIR", "reports")),
        capture_dir=Path(os.getenv("STUDY_AGENT_CAPTURE_DIR", "data/captures")),
        screen_interval_sec=int(os.getenv("STUDY_AGENT_SCREEN_INTERVAL_SEC", "1")),
        camera_interval_sec=int(os.getenv("STUDY_AGENT_CAMERA_INTERVAL_SEC", "1")),
        loop_interval_sec=int(os.getenv("STUDY_AGENT_LOOP_INTERVAL_SEC", "5")),
        report_hour=int(os.getenv("STUDY_AGENT_REPORT_HOUR", "23")),
        report_minute=int(os.getenv("STUDY_AGENT_REPORT_MINUTE", "0")),
        model_enabled=_get_bool("STUDY_AGENT_MODEL_ENABLED", False),
        model_base_url=os.getenv("STUDY_AGENT_MODEL_BASE_URL", "http://127.0.0.1:11434/v1"),
        model_name=os.getenv("STUDY_AGENT_MODEL_NAME", "qwen2.5vl:latest"),
        model_api_key=os.getenv("STUDY_AGENT_MODEL_API_KEY", ""),
        camera_index=int(os.getenv("STUDY_AGENT_CAMERA_INDEX", "0")),
    )
