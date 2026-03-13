from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from PIL import Image

from study_agent.config import Settings
from study_agent.model.client import LocalMultimodalClient
from study_agent.types import Observation, SystemContext


def _make_image(path: Path, color: tuple[int, int, int]) -> None:
    Image.new("RGB", (24, 24), color=color).save(path)


def test_payload_contains_three_images_and_timestamp_texts(tmp_path) -> None:
    client = LocalMultimodalClient(Settings(model_enabled=True))
    frames = []
    for index, color in enumerate([(255, 255, 255), (120, 120, 120), (0, 0, 0)]):
        image_path = tmp_path / f"screen_{index}.jpg"
        _make_image(image_path, color)
        frames.append(
            {
                "observed_at": datetime(
                    2026,
                    3,
                    13,
                    20,
                    index,
                    tzinfo=ZoneInfo("Asia/Shanghai"),
                ).isoformat(),
                "screen_path": image_path,
            }
        )

    observation = Observation(
        observed_at=datetime(2026, 3, 13, 20, 2, tzinfo=ZoneInfo("Asia/Shanghai")),
        screen_path=frames[-1]["screen_path"],
        camera_path=None,
        context=SystemContext(active_app="VSCode", window_title="main.py - VSCode"),
    )
    recent_summary = {
        "recent_samples": 2,
        "recent_records": [
            {"observed_at": frames[0]["observed_at"], "state": "studying"},
            {"observed_at": frames[1]["observed_at"], "state": "studying"},
        ],
    }

    payload = client._build_payload(
        observation,
        recent_summary,
        frames,
        include_images=True,
        enforce_json_response=True,
    )
    content = payload["messages"][1]["content"]
    image_items = [item for item in content if item["type"] == "image_url"]
    text_items = [item for item in content if item["type"] == "text"]

    assert len(image_items) == 3
    assert any("截图1 抓取时间" in item["text"] for item in text_items)
    assert any("最近10条历史记录(JSON)" in item["text"] for item in text_items)
