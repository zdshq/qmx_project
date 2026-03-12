"""SQLite persistence and aggregation helpers."""

from __future__ import annotations

import json
import sqlite3
from contextlib import contextmanager
from datetime import date, datetime, time, timedelta
from pathlib import Path
from typing import Iterator

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
                    None if assessment.is_looking_at_screen is None else int(assessment.is_looking_at_screen),
                    assessment.focus_score,
                    assessment.reason,
                    json.dumps(assessment.distraction_signals, ensure_ascii=False),
                    json.dumps(assessment.raw_response, ensure_ascii=False),
                ),
            )

    def summarize_recent(self, limit: int = 20) -> dict[str, object]:
        """Summarize recent records for use as short-term model memory."""
        with self.connect() as connection:
            rows = connection.execute(
                "SELECT state, focus_score, learning_related, is_present FROM observations ORDER BY id DESC LIMIT ?",
                (limit,),
            ).fetchall()
        if not rows:
            return {"recent_samples": 0}
        # Sequence of recent state labels.
        states = [row["state"] for row in rows]
        # Average focus score over recent samples.
        focus_avg = sum(row["focus_score"] for row in rows) / len(rows)
        # Ratio of recent samples marked as learning-related.
        learning_ratio = sum(row["learning_related"] for row in rows) / len(rows)
        # Ratio of recent samples marked as present.
        presence_ratio = sum(row["is_present"] for row in rows) / len(rows)
        return {
            "recent_samples": len(rows),
            "focus_avg": round(focus_avg, 3),
            "learning_ratio": round(learning_ratio, 3),
            "presence_ratio": round(presence_ratio, 3),
            "latest_state": states[0],
        }

    def summarize_day(self, target_day: date, timezone_name: str) -> dict[str, object]:
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
                "presence_ratio": 0.0,
                "avg_focus_score": 0.0,
                "top_apps": [],
                "state_breakdown": {},
                "highlights": [],
            }

        # Counts for each inferred state.
        state_breakdown: dict[str, int] = {}
        # Frequency counts for active applications.
        app_counts: dict[str, int] = {}
        # Short list of high-confidence highlights.
        highlights: list[str] = []
        for row in rows:
            state_breakdown[row["state"]] = state_breakdown.get(row["state"], 0) + 1
            if row["active_app"]:
                app_counts[row["active_app"]] = app_counts.get(row["active_app"], 0) + 1
            if row["confidence"] >= 0.8 and len(highlights) < 5:
                title = row["window_title"] or row["active_app"] or row["state"]
                highlights.append(f"{row['observed_at']} - {row['state']} - {title}")

        # Float copy used to avoid repeated conversions in ratio calculations.
        sample_count_float = float(sample_count)
        return {
            "date": str(target_day),
            "timezone": timezone_name,
            "sample_count": sample_count,
            "study_ratio": round(sum(row["learning_related"] for row in rows) / sample_count_float, 3),
            "presence_ratio": round(sum(row["is_present"] for row in rows) / sample_count_float, 3),
            "avg_focus_score": round(sum(row["focus_score"] for row in rows) / sample_count_float, 3),
            "top_apps": sorted(app_counts.items(), key=lambda item: item[1], reverse=True)[:5],
            "state_breakdown": state_breakdown,
            "highlights": highlights,
        }
