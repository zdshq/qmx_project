"""Screen history comparison utilities."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from PIL import Image, ImageChops, ImageStat


@dataclass(slots=True)
class ScreenHistoryResult:
    """Store the result of a recent screen-history comparison."""

    has_triplet: bool
    all_static: bool
    signatures: list[str]
    pairwise_mean_diffs: list[float]


class ScreenHistoryAnalyzer:
    """Analyze whether recent screenshots remain unchanged."""

    def compute_signature(self, path: Path) -> str:
        """Compute a compact signature for debug display."""
        with Image.open(path) as image:
            resized = image.convert("L").resize((32, 32))
            histogram = resized.histogram()
        return "-".join(str(value) for value in histogram[:8])

    def mean_difference(self, left: Path, right: Path) -> float:
        """Compute the mean grayscale difference between two screenshots."""
        with Image.open(left) as left_image, Image.open(right) as right_image:
            left_gray = left_image.convert("L").resize((32, 32))
            right_gray = right_image.convert("L").resize((32, 32))
            diff = ImageChops.difference(left_gray, right_gray)
            return float(ImageStat.Stat(diff).mean[0])

    def analyze(self, paths: list[Path | None], *, static_threshold: float) -> ScreenHistoryResult:
        """Check whether the latest three screenshots are visually unchanged."""
        valid_paths = [path for path in paths if path is not None]
        if len(valid_paths) < 3:
            return ScreenHistoryResult(
                has_triplet=False,
                all_static=False,
                signatures=[],
                pairwise_mean_diffs=[],
            )

        latest_paths = valid_paths[-3:]
        signatures = [self.compute_signature(path) for path in latest_paths]
        pairwise_mean_diffs = [
            self.mean_difference(latest_paths[0], latest_paths[1]),
            self.mean_difference(latest_paths[1], latest_paths[2]),
        ]
        return ScreenHistoryResult(
            has_triplet=True,
            all_static=all(diff <= static_threshold for diff in pairwise_mean_diffs),
            signatures=signatures,
            pairwise_mean_diffs=pairwise_mean_diffs,
        )
