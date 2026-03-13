from pathlib import Path

from PIL import Image

from study_agent.screen_history import ScreenHistoryAnalyzer


def _create_image(path: Path, color: tuple[int, int, int]) -> None:
    image = Image.new("RGB", (32, 32), color=color)
    image.save(path)


def test_analyzer_detects_static_triplet(tmp_path) -> None:
    analyzer = ScreenHistoryAnalyzer()
    image_paths = [tmp_path / f"image_{index}.jpg" for index in range(3)]
    for path in image_paths:
        _create_image(path, (255, 255, 255))

    result = analyzer.analyze(image_paths, static_threshold=2.0)

    assert result.has_triplet is True
    assert result.all_static is True
    assert len(result.signatures) == 3
    assert len(result.pairwise_mean_diffs) == 2


def test_analyzer_detects_changed_triplet(tmp_path) -> None:
    analyzer = ScreenHistoryAnalyzer()
    image_paths = [tmp_path / f"image_{index}.jpg" for index in range(3)]
    _create_image(image_paths[0], (255, 255, 255))
    _create_image(image_paths[1], (255, 255, 255))
    _create_image(image_paths[2], (0, 0, 0))

    result = analyzer.analyze(image_paths, static_threshold=2.0)

    assert result.has_triplet is True
    assert result.all_static is False
