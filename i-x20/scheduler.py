from __future__ import annotations

import sys

from tracker.config import PROJECT_ROOT, settings
from tracker.database import Database
from tracker.logging_config import configure_logging
from tracker.profile_service import ProfileService
from tracker.reporting import ExcelReportWriter, verify_report


def main() -> int:
    settings.ensure_directories()
    logger = configure_logging(PROJECT_ROOT / "logs")
    database = Database(settings.database_path)
    due = database.list_profiles(active_only=True, due_days=settings.fetch_interval_days)
    if not due:
        logger.info("No active profiles are due for refresh")
        return 0
    logger.info("Refreshing %d profile(s)", len(due))
    summary = ProfileService(database, settings, logger).fetch_profiles(due)
    report = ExcelReportWriter(database, settings.reports_dir).generate()
    verification = verify_report(report)
    logger.info(
        "Weekly refresh complete: %d succeeded, %d failed, report=%s",
        summary.succeeded,
        summary.failed,
        report,
    )
    return 0 if verification["valid"] else 1


if __name__ == "__main__":
    sys.exit(main())

