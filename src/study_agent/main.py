"""Command-line entry point."""

from __future__ import annotations

import argparse
from datetime import datetime

from study_agent.agent import StudyAgent
from study_agent.config import load_settings
from study_agent.doctor import EnvironmentDoctor
from study_agent.reporting.reporter import DailyReporter
from study_agent.storage.db import Database


def build_parser() -> argparse.ArgumentParser:
    """Build the command-line argument parser."""
    # Top-level command-line parser.
    parser = argparse.ArgumentParser(description="Study Agent MVP")
    # Collection of supported subcommands.
    subparsers = parser.add_subparsers(dest="command", required=True)

    subparsers.add_parser("init-db", help="Initialize SQLite database")
    run_parser = subparsers.add_parser("run", help="Run the agent loop")
    run_parser.add_argument("--debug", action="store_true", help="Enable verbose debug logs")
    run_once_parser = subparsers.add_parser("run-once", help="Run one observe-assess-persist cycle")
    run_once_parser.add_argument("--debug", action="store_true", help="Enable verbose debug logs")
    subparsers.add_parser("doctor", help="Run environment diagnostics")

    # Parser for the `report` subcommand.
    report_parser = subparsers.add_parser("report", help="Generate report for a specific day")
    report_parser.add_argument("--date", dest="target_date", help="Target date in YYYY-MM-DD")
    return parser


def main() -> None:
    """Execute database initialization, one-shot runs, full runs, or report generation."""
    # Parser used for command-line argument resolution.
    parser = build_parser()
    # Parsed command-line arguments.
    args = parser.parse_args()
    # Runtime settings loaded from environment.
    settings = load_settings()

    if args.command == "init-db":
        # Database access layer.
        database = Database(settings.db_path)
        database.init_db()
        print(f"Database initialized at {settings.db_path}")
        return

    if args.command == "report":
        # Database access layer.
        database = Database(settings.db_path)
        database.init_db()
        # Report renderer.
        reporter = DailyReporter(settings, database)
        # Target report date.
        target_day = (
            datetime.strptime(args.target_date, "%Y-%m-%d").date()
            if args.target_date
            else datetime.now(settings.tzinfo).date()
        )
        report_path = reporter.generate(target_day)
        print(f"Report generated: {report_path}")
        return

    if args.command == "run":
        StudyAgent(settings, debug=args.debug).run_forever()
        return

    if args.command == "run-once":
        StudyAgent(settings, debug=args.debug).run_once()
        return

    if args.command == "doctor":
        doctor = EnvironmentDoctor(settings)
        print(doctor.render_text(doctor.run()))
        return

    parser.error("Unknown command")


if __name__ == "__main__":
    main()
