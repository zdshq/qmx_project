from study_agent.config import Settings, load_settings


def test_settings_timezone_property() -> None:
    settings = Settings(timezone="Asia/Shanghai")

    assert settings.tzinfo.key == "Asia/Shanghai"


def test_load_settings_reads_environment(monkeypatch) -> None:
    monkeypatch.setenv("STUDY_AGENT_LOOP_INTERVAL_SEC", "9")
    monkeypatch.setenv("STUDY_AGENT_MODEL_ENABLED", "true")

    settings = load_settings()

    assert settings.loop_interval_sec == 9
    assert settings.model_enabled is True
