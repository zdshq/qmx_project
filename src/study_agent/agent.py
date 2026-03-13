"""Agent main loop."""

from __future__ import annotations

import time
from datetime import datetime

from study_agent.capture.screen import ScreenCapturer
from study_agent.cleanup import CaptureCleaner
from study_agent.config import Settings
from study_agent.model.client import LocalMultimodalClient
from study_agent.reporting.reporter import DailyReporter
from study_agent.reporting.scheduler import ReportScheduler
from study_agent.screen_history import ScreenHistoryAnalyzer
from study_agent.storage.db import Database
from study_agent.system.context import SystemContextCollector
from study_agent.types import Observation, StudyAssessment


class StudyAgent:
    """Coordinate capture, inference, storage, and report generation."""

    def __init__(self, settings: Settings, *, debug: bool | None = None) -> None:
        """Initialize all components required by the agent."""
        # Runtime settings for the current agent instance.
        self.settings = settings
        # Effective debug flag for verbose diagnostics.
        self.debug = settings.debug if debug is None else debug
        # SQLite-backed persistence layer.
        self.database = Database(settings.db_path)
        self.database.init_db()
        # Screen capture component.
        self.screen = ScreenCapturer(settings.capture_dir)
        # Screenshot retention cleaner.
        self.cleaner = CaptureCleaner(settings)
        # Recent screenshot comparison helper.
        self.screen_history = ScreenHistoryAnalyzer()
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
        try:
            while True:
                self.run_once()
                time.sleep(self.settings.loop_interval_sec)
        except KeyboardInterrupt:
            print("Study Agent stopped by user.")

    def run_once(self) -> None:
        """Execute one complete agent cycle."""
        # Current timezone-aware sampling timestamp.
        now = datetime.now(self.settings.tzinfo)
        # Observation collected for this cycle.
        observation = self._observe(now)
        # Short-term summary built from recent database records.
        recent_summary = self.database.summarize_recent()
        self._debug(
            "recent_history",
            recent_samples=recent_summary.get("recent_samples", 0),
            recent_states=[
                record.get("state")
                for record in recent_summary.get("recent_records", [])[-5:]
                if isinstance(record, dict)
            ],
        )
        # Inferred study-state assessment for the current observation.
        assessment = self._assess(observation, recent_summary)
        self.database.insert_observation(observation, assessment)
        print(
            f"[{now.isoformat()}] state={assessment.state} focus={assessment.focus_score} "
            f"app={observation.context.active_app} reason={assessment.reason}"
        )
        self._cleanup_captures(now)
        self._maybe_generate_report(now)

    def _observe(self, now: datetime) -> Observation:
        """Collect system context and one screen capture."""
        # Current system context snapshot.
        context = self.context_collector.collect(now)
        # Saved path of the current screen image.
        screen_path = self.screen.capture(now)
        return Observation(
            observed_at=now,
            screen_path=screen_path,
            camera_path=None,
            context=context,
        )

    def _assess(
        self,
        observation: Observation,
        recent_summary: dict[str, object],
    ) -> StudyAssessment:
        """Assess the current observation with strict static-frame fallback."""
        recent_paths = self.database.recent_screen_paths(limit=2)
        history_result = self.screen_history.analyze(
            [*recent_paths, observation.screen_path],
            static_threshold=self.settings.static_diff_threshold,
        )
        idle_seconds = observation.context.idle_seconds
        should_force_away = (
            history_result.has_triplet
            and history_result.all_static
            and idle_seconds is not None
            and idle_seconds >= self.settings.idle_away_seconds
        )
        self._debug(
            "static_rule",
            idle_seconds=idle_seconds,
            idle_away_seconds=self.settings.idle_away_seconds,
            static_threshold=self.settings.static_diff_threshold,
            signatures=history_result.signatures,
            pairwise_mean_diffs=history_result.pairwise_mean_diffs,
            triggered=should_force_away,
        )
        if should_force_away:
            return StudyAssessment(
                state="away",
                confidence=0.99,
                learning_related=False,
                is_present=False,
                is_looking_at_screen=False,
                focus_score=0.0,
                reason="idle + three-frame static rule triggered",
                distraction_signals=["three_consecutive_static_frames"],
                raw_response={
                    "mode": "idle_static_rule",
                    "signatures": history_result.signatures,
                    "pairwise_mean_diffs": history_result.pairwise_mean_diffs,
                    "idle_seconds": idle_seconds,
                },
            )
        recent_frames = self.database.recent_screen_frames(limit=2)
        recent_frames.append(
            {
                "observed_at": observation.observed_at.isoformat(),
                "screen_path": observation.screen_path,
            }
        )
        return self.model.assess(observation, recent_summary, recent_frames)

    def _debug(self, label: str, **payload: object) -> None:
        """Print structured debug information when debug mode is enabled."""
        if not self.debug:
            return
        parts = ", ".join(f"{key}={value}" for key, value in payload.items())
        print(f"[DEBUG] {label}: {parts}")

    def _cleanup_captures(self, now: datetime) -> None:
        """Delete expired screenshots after a cycle."""
        cleanup_result = self.cleaner.cleanup(now)
        if cleanup_result.deleted_files == 0:
            return
        print(
            "Cleanup completed: "
            f"deleted={cleanup_result.deleted_files} "
            f"freed_bytes={cleanup_result.freed_bytes}"
        )

    def _maybe_generate_report(self, now: datetime) -> None:
        """Generate the daily report when the scheduled time is reached."""
        if not self.scheduler.should_generate(now):
            return
        # Day that should receive the generated report.
        target_day = self.scheduler.report_target_day(now)
        # Path to the generated report file.
        report_path = self.reporter.generate(target_day)
        self._cleanup_captures(now)
        self.scheduler.mark_generated(target_day)
        print(f"Daily report generated: {report_path}")
