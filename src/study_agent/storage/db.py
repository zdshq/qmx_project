"""SQLite persistence and aggregation helpers."""

from __future__ import annotations

import json
import sqlite3
from collections.abc import Iterator
from contextlib import contextmanager
from datetime import date, datetime, time, timedelta
from pathlib import Path

from study_agent.types import Observation, StudyAssessment


class Database:
    """Persist observations and query aggregated summaries."""

    def __init__(self, db_path: Path) -> None:
        """Initialize the database path and ensure its parent directory exists."""
        # Path to the SQLite database file.
        self.db_path = db_path
        self.db_path.parent.mkdir(parents=True, exist_ok=True)

    @contextmanager
    def connect(self) -> Iterator[sqlite3.Connection]:
        """Create a database connection context with auto-commit."""
        # Active SQLite connection.
        connection = sqlite3.connect(self.db_path)
        connection.row_factory = sqlite3.Row
        try:
            yield connection
            connection.commit()
        finally:
            connection.close()

    def init_db(self) -> None:
        """Create the observations table if it does not already exist."""
        with self.connect() as connection:
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS observations (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    observed_at TEXT NOT NULL,
                    screen_path TEXT,
                    camera_path TEXT,
                    active_app TEXT,
                    window_title TEXT,
                    idle_seconds REAL,
                    app_switch_count_5m INTEGER,
                    state TEXT NOT NULL,
                    confidence REAL NOT NULL,
                    learning_related INTEGER NOT NULL,
                    is_present INTEGER NOT NULL,
                    is_looking_at_screen INTEGER,
                    focus_score REAL NOT NULL,
                    reason TEXT NOT NULL,
                    distraction_signals TEXT,
                    raw_response TEXT
                )
                """
            )

    def insert_observation(self, observation: Observation, assessment: StudyAssessment) -> None:
        """Insert one observation and its assessment into the database."""
        with self.connect() as connection:
            connection.execute(
                """
                INSERT INTO observations (
                    observed_at, screen_path, camera_path, active_app, window_title, idle_seconds,
                    app_switch_count_5m, state, confidence, learning_related, is_present,
                    is_looking_at_screen, focus_score, reason, distraction_signals, raw_response
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    observation.observed_at.isoformat(),
                    str(observation.screen_path) if observation.screen_path else None,
                    str(observation.camera_path) if observation.camera_path else None,
                    observation.context.active_app,
                    observation.context.window_title,
                    observation.context.idle_seconds,
                    observation.context.app_switch_count_5m,
                    assessment.state,
                    assessment.confidence,
                    int(assessment.learning_related),
                    int(assessment.is_present),
                    None
                    if assessment.is_looking_at_screen is None
                    else int(assessment.is_looking_at_screen),
                    assessment.focus_score,
                    assessment.reason,
                    json.dumps(assessment.distraction_signals, ensure_ascii=False),
                    json.dumps(assessment.raw_response, ensure_ascii=False),
                ),
            )

    def summarize_recent(self, limit: int = 10) -> dict[str, object]:
        """Return recent raw records for use as short-term model memory."""
        with self.connect() as connection:
            rows = connection.execute(
                (
                    "SELECT observed_at, state, confidence, learning_related, "
                    "is_present, focus_score, active_app, window_title, reason, "
                    "distraction_signals "
                    "FROM observations ORDER BY id DESC LIMIT ?"
                ),
                (limit,),
            ).fetchall()
        if not rows:
            return {"recent_samples": 0, "recent_records": []}

        recent_records: list[dict[str, object]] = []
        for row in reversed(rows):
            distraction_signals = json.loads(row["distraction_signals"] or "[]")
            recent_records.append(
                {
                    "observed_at": row["observed_at"],
                    "state": row["state"],
                    "confidence": row["confidence"],
                    "learning_related": bool(row["learning_related"]),
                    "is_present": bool(row["is_present"]),
                    "focus_score": row["focus_score"],
                    "active_app": row["active_app"],
                    "window_title": row["window_title"],
                    "reason": row["reason"],
                    "distraction_signals": distraction_signals,
                }
            )

        return {
            "recent_samples": len(recent_records),
            "recent_records": recent_records,
        }

    def recent_screen_paths(self, limit: int = 2) -> list[Path]:
        """Return recent non-empty screen paths ordered from old to new."""
        with self.connect() as connection:
            rows = connection.execute(
                (
                    "SELECT screen_path FROM observations "
                    "WHERE screen_path IS NOT NULL ORDER BY id DESC LIMIT ?"
                ),
                (limit,),
            ).fetchall()
        return [Path(row["screen_path"]) for row in reversed(rows) if row["screen_path"]]

    def recent_screen_frames(self, limit: int = 2) -> list[dict[str, object]]:
        """Return recent non-empty screen frames ordered from old to new."""
        with self.connect() as connection:
            rows = connection.execute(
                (
                    "SELECT observed_at, screen_path FROM observations "
                    "WHERE screen_path IS NOT NULL ORDER BY id DESC LIMIT ?"
                ),
                (limit,),
            ).fetchall()
        frames: list[dict[str, object]] = []
        for row in reversed(rows):
            if not row["screen_path"]:
                continue
            frames.append(
                {
                    "observed_at": row["observed_at"],
                    "screen_path": Path(row["screen_path"]),
                }
            )
        return frames

    def summarize_day(
        self,
        target_day: date,
        timezone_name: str,
        sample_interval_seconds: int,
    ) -> dict[str, object]:
        """Summarize one calendar day for report generation."""
        # Inclusive lower bound for the target day.
        day_start = datetime.combine(target_day, time.min).isoformat()
        # Exclusive upper bound for the target day.
        day_end = datetime.combine(target_day + timedelta(days=1), time.min).isoformat()
        with self.connect() as connection:
            rows = connection.execute(
                """
                SELECT observed_at, state, confidence, learning_related, is_present, focus_score,
                       active_app, window_title, reason
                FROM observations
                WHERE observed_at >= ? AND observed_at < ?
                ORDER BY observed_at ASC
                """,
                (day_start, day_end),
            ).fetchall()
        # Total number of samples collected for the day.
        sample_count = len(rows)
        if sample_count == 0:
            return {
                "date": str(target_day),
                "timezone": timezone_name,
                "sample_count": 0,
                "study_ratio": 0.0,
                "avg_focus_score": 0.0,
                "focused_study_minutes": 0,
                "distracted_minutes": 0,
                "uncertain_minutes": 0,
                "top_apps": [],
                "state_breakdown": {},
                "highlights": [],
                "focus_blocks": [],
                "distraction_blocks": [],
            }

        # Counts for each inferred state.
        state_breakdown: dict[str, int] = {}
        # Frequency counts for active applications.
        app_counts: dict[str, int] = {}
        # Short list of high-confidence highlights.
        highlights: list[str] = []
        focus_blocks = self._build_time_blocks(
            rows,
            sample_interval_seconds=sample_interval_seconds,
            matcher=lambda row: bool(row["learning_related"]) and float(row["focus_score"]) >= 0.6,
        )
        distraction_blocks = self._build_time_blocks(
            rows,
            sample_interval_seconds=sample_interval_seconds,
            matcher=lambda row: row["state"] == "distracted",
        )
        for row in rows:
            state_breakdown[row["state"]] = state_breakdown.get(row["state"], 0) + 1
            if row["active_app"]:
                app_counts[row["active_app"]] = app_counts.get(row["active_app"], 0) + 1
            if row["confidence"] >= 0.8 and len(highlights) < 5:
                title = row["window_title"] or row["active_app"] or row["state"]
                highlights.append(f"{row['observed_at']} - {row['state']} - {title}")

        # Float copy used to avoid repeated conversions in ratio calculations.
        sample_count_float = float(sample_count)
        focused_sample_count = sum(
            1 for row in rows if bool(row["learning_related"]) and float(row["focus_score"]) >= 0.6
        )
        distracted_sample_count = sum(1 for row in rows if row["state"] == "distracted")
        uncertain_sample_count = sum(1 for row in rows if row["state"] == "uncertain")
        minutes_per_sample = sample_interval_seconds / 60
        return {
            "date": str(target_day),
            "timezone": timezone_name,
            "sample_count": sample_count,
            "study_ratio": round(
                sum(row["learning_related"] for row in rows) / sample_count_float, 3
            ),
            "avg_focus_score": round(
                sum(row["focus_score"] for row in rows) / sample_count_float, 3
            ),
            "focused_study_minutes": round(focused_sample_count * minutes_per_sample),
            "distracted_minutes": round(distracted_sample_count * minutes_per_sample),
            "uncertain_minutes": round(uncertain_sample_count * minutes_per_sample),
            "top_apps": sorted(app_counts.items(), key=lambda item: item[1], reverse=True)[:5],
            "state_breakdown": state_breakdown,
            "highlights": highlights,
            "focus_blocks": focus_blocks,
            "distraction_blocks": distraction_blocks,
        }

    def _build_time_blocks(
        self,
        rows: list[sqlite3.Row],
        *,
        sample_interval_seconds: int,
        matcher,
    ) -> list[dict[str, object]]:
        """Build contiguous time blocks for a given match condition."""
        blocks: list[dict[str, object]] = []
        current_block: dict[str, object] | None = None
        max_gap_seconds = int(sample_interval_seconds * 1.5)

        for row in rows:
            if not matcher(row):
                current_block = None
                continue

            observed_at = datetime.fromisoformat(row["observed_at"])
            if current_block is None:
                current_block = {
                    "start": observed_at,
                    "end": observed_at + timedelta(seconds=sample_interval_seconds),
                    "samples": 1,
                }
                blocks.append(current_block)
                continue

            previous_end = current_block["end"]
            if isinstance(previous_end, datetime):
                gap_seconds = int((observed_at - previous_end).total_seconds())
                if gap_seconds <= max_gap_seconds:
                    current_block["end"] = observed_at + timedelta(seconds=sample_interval_seconds)
                    current_block["samples"] = int(current_block["samples"]) + 1
                    continue

            current_block = {
                "start": observed_at,
                "end": observed_at + timedelta(seconds=sample_interval_seconds),
                "samples": 1,
            }
            blocks.append(current_block)

        rendered_blocks: list[dict[str, object]] = []
        for block in blocks:
            start = block["start"]
            end = block["end"]
            if not isinstance(start, datetime) or not isinstance(end, datetime):
                continue
            rendered_blocks.append(
                {
                    "start": start.strftime("%H:%M"),
                    "end": end.strftime("%H:%M"),
                    "minutes": round((end - start).total_seconds() / 60),
                    "samples": int(block["samples"]),
                }
            )
        return rendered_blocks
