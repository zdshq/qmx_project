"""Daily report generation."""

from __future__ import annotations

from datetime import date
from pathlib import Path

from study_agent.config import Settings
from study_agent.storage.db import Database


class DailyReporter:
    """Render daily summary data into a Markdown report."""

    def __init__(self, settings: Settings, database: Database) -> None:
        """Initialize report output dependencies and directories."""
        # Runtime settings for report generation.
        self.settings = settings
        # Database access layer used to query summaries.
        self.database = database
        self.settings.report_dir.mkdir(parents=True, exist_ok=True)

    def generate(self, target_day: date) -> Path:
        """Generate a Markdown report for the given date."""
        # Aggregated summary for the target day.
        summary = self.database.summarize_day(target_day, self.settings.timezone)
        # Output path of the generated report.
        report_path = self.settings.report_dir / f"study_report_{target_day.isoformat()}.md"
        report_path.write_text(self._render(summary), encoding="utf-8")
        return report_path

    def _render(self, summary: dict[str, object]) -> str:
        """Render the daily summary into Markdown text."""
        # Most frequent active applications.
        top_apps = summary["top_apps"]
        # Per-state count distribution.
        state_breakdown = summary["state_breakdown"]
        # High-confidence observation highlights.
        highlights = summary["highlights"]
        # Line buffer used to build the Markdown document.
        lines = [
            f"# 学习日报 - {summary['date']}",
            "",
            f"- 时区: {summary['timezone']}",
            f"- 采样数: {summary['sample_count']}",
            f"- 学习相关占比: {summary['study_ratio']}",
            f"- 在位占比: {summary['presence_ratio']}",
            f"- 平均专注分: {summary['avg_focus_score']}",
            "",
            "## 状态分布",
        ]
        if state_breakdown:
            for state, count in state_breakdown.items():
                lines.append(f"- {state}: {count}")
        else:
            lines.append("- 无数据")

        lines.extend(["", "## 高活跃应用"])
        if top_apps:
            for app_name, count in top_apps:
                lines.append(f"- {app_name}: {count}")
        else:
            lines.append("- 无数据")

        lines.extend(["", "## 高置信片段"])
        if highlights:
            for item in highlights:
                lines.append(f"- {item}")
        else:
            lines.append("- 无高置信片段")

        lines.extend(["", "## 总结", self._narrative(summary)])
        return "\n".join(lines) + "\n"

    def _narrative(self, summary: dict[str, object]) -> str:
        """Generate a short narrative conclusion for the daily report."""
        # Number of samples collected during the day.
        sample_count = int(summary["sample_count"])
        if sample_count == 0:
            return "今天没有采集到有效学习数据。"

        # Fraction of samples classified as learning-related.
        study_ratio = float(summary["study_ratio"])
        # Average daily focus score.
        focus_score = float(summary["avg_focus_score"])
        if study_ratio >= 0.75 and focus_score >= 0.7:
            return "今天整体处于较稳定的学习状态，学习相关活动占比较高，专注度表现良好。"
        if study_ratio >= 0.5:
            return "今天存在较明显的学习时段，但仍有一部分时间处于分心或状态不确定区间。"
        return "今天学习相关活动占比偏低，建议复盘高频应用和分心时段。"
