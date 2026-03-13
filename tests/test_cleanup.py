from datetime import datetime, timedelta

from study_agent.cleanup import CaptureCleaner
from study_agent.config import Settings


def test_cleanup_deletes_expired_screenshots(tmp_path) -> None:
    settings = Settings(
        capture_dir=tmp_path / "captures",
        capture_retention_hours=24,
    )
    screen_dir = settings.capture_dir / "screen"
    screen_dir.mkdir(parents=True, exist_ok=True)

    expired = screen_dir / "old.jpg"
    fresh = screen_dir / "fresh.jpg"
    expired.write_bytes(b"old")
    fresh.write_bytes(b"fresh")

    now = datetime.now(settings.tzinfo)
    old_timestamp = (now - timedelta(hours=30)).timestamp()
    fresh_timestamp = (now - timedelta(hours=1)).timestamp()

    import os

    os.utime(expired, (old_timestamp, old_timestamp))
    os.utime(fresh, (fresh_timestamp, fresh_timestamp))

    result = CaptureCleaner(settings).cleanup(now)

    assert result.deleted_files == 1
    assert expired.exists() is False
    assert fresh.exists() is True
