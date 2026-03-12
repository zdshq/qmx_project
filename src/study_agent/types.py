"""Core data structure definitions."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any


@dataclass(slots=True)
class SystemContext:
    """Store system context for a single sample."""

    # Guessed foreground application name.
    active_app: str | None = None
    # Current active window title.
    window_title: str | None = None
    # Input idle duration in seconds; unset when unavailable.
    idle_seconds: float | None = None
    # Number of window switches in the last 5 minutes.
    app_switch_count_5m: int | None = None


@dataclass(slots=True)
class Observation:
    """Store one complete observation."""

    # Timestamp of the observation.
    observed_at: datetime
    # Path to the saved screen capture.
    screen_path: Path | None
    # Path to the saved camera capture.
    camera_path: Path | None
    # System context collected for this observation.
    context: SystemContext


@dataclass(slots=True)
class StudyAssessment:
    """Store the study-state assessment from the model or heuristics."""

    # Overall inferred state.
    state: str
    # Confidence score for the inferred state.
    confidence: float
    # Whether the current activity is learning-related.
    learning_related: bool
    # Whether a person is confirmed to be present.
    is_present: bool
    # Whether the person appears to look at the screen; unset when unknown.
    is_looking_at_screen: bool | None
    # Focus score in the approximate range [0, 1].
    focus_score: float
    # Short reason for the assessment.
    reason: str
    # Detected distraction signals.
    distraction_signals: list[str] = field(default_factory=list)
    # Raw model response for debugging and tracing.
    raw_response: dict[str, Any] | None = None
