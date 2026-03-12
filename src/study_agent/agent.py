"""Agent main loop."""

from __future__ import annotations

import time
from datetime import datetime

from study_agent.capture.camera import CameraCapturer
from study_agent.capture.screen import ScreenCapturer
from study_agent.config import Settings
from study_agent.model.client import LocalMultimodalClient
from study_agent.reporting.reporter import DailyReporter
from study_agent.reporting.scheduler import ReportScheduler
from study_agent.storage.db import Database
from study_agent.system.context import SystemContextCollector
from study_agent.types import Observation


class StudyAgent:
    """Coordinate capture, inference, storage, and report generation."""

    def __init__(self, settings: Settings) -> None:
        """Initialize all components required by the agent."""
        # Runtime settings for the current agent instance.
        self.settings = settings
        # SQLite-backed persistence layer.
        self.database = Database(settings.db_path)
        self.database.init_db()
        # Screen capture component.
        self.screen = ScreenCapturer(settings.capture_dir)
        # Camera capture component.
        self.camera = CameraCapturer(settings.capture_dir, settings.camera_index)
        # System context collector.
        self.context_collector = SystemContextCollector()
        # Local multimodal model client.
        self.model = LocalMultimodalClient(settings)
        # Daily report renderer.
        self.reporter = DailyReporter(settings, self.database)
        # Daily report trigger scheduler.
        self.scheduler = ReportScheduler(settings)

    def run_forever(self) -> None:
        """Run the observe-assess-store loop continuously."""
        print("Study Agent started.")
        while True:
            self.run_once()
            time.sleep(self.settings.loop_interval_sec)

    def run_once(self) -> None:
        """Execute one complete agent cycle."""
        # Current timezone-aware sampling timestamp.
        now = datetime.now(self.settings.tzinfo)
        # Observation collected for this cycle.
        observation = self._observe(now)
        # Short-term summary built from recent database records.
        recent_summary = self.database.summarize_recent()
        # Inferred study-state assessment for the current observation.
        assessment = self.model.assess(observation, recent_summary)
        self.database.insert_observation(observation, assessment)
        print(
            f"[{now.isoformat()}] state={assessment.state} focus={assessment.focus_score} "
            f"app={observation.context.active_app} reason={assessment.reason}"
        )
        self._maybe_generate_report(now)

    def _observe(self, now: datetime) -> Observation:
        """Collect system context, screen capture, and camera capture once."""
        # Current system context snapshot.
        context = self.context_collector.collect(now)
        # Saved path of the current screen image.
        screen_path = self.screen.capture(now)
        # Saved path of the current camera image.
        camera_path = self.camera.capture(now)
        return Observation(
            observed_at=now,
            screen_path=screen_path,
            camera_path=camera_path,
            context=context,
        )

    def _maybe_generate_report(self, now: datetime) -> None:
        """Generate the daily report when the scheduled time is reached."""
        if not self.scheduler.should_generate(now):
            return
        # Day that should receive the generated report.
        target_day = self.scheduler.report_target_day(now)
        # Path to the generated report file.
        report_path = self.reporter.generate(target_day)
        self.scheduler.mark_generated(target_day)
        print(f"Daily report generated: {report_path}")
