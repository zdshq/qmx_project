from study_agent.config import Settings
from study_agent.doctor import EnvironmentDoctor


def test_doctor_renders_summary(tmp_path) -> None:
    settings = Settings(
        db_path=tmp_path / "study_agent.db",
        report_dir=tmp_path / "reports",
        capture_dir=tmp_path / "captures",
        model_enabled=False,
    )
    doctor = EnvironmentDoctor(settings)

    results = doctor.run()
    text = doctor.render_text(results)

    assert len(results) == 6
    assert "Study Agent Doctor" in text
    assert "Summary:" in text
