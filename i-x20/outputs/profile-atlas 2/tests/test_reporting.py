from openpyxl import load_workbook

from tracker.database import Database
from tracker.models import ProfileResult
from tracker.reporting import ExcelReportWriter, SUMMARY_HEADERS, verify_report, weekly_progress_rows


def test_report_has_all_sheets_headers_and_na(tmp_path):
    db = Database(tmp_path / "profiles.db")
    profile_id, _ = db.upsert_profile("Ana", "LeetCode", "ana", "https://leetcode.com/u/ana", "R001")
    db.save_success(profile_id, ProfileResult(
        platform="LeetCode", username="ana", profile_url="https://leetcode.com/u/ana",
        problems_solved=100, easy=50, medium=40, hard=10, rating=1700,
    ))
    path = ExcelReportWriter(db, tmp_path).generate(tmp_path / "report.xlsx")
    assert verify_report(path)["valid"]
    wb = load_workbook(path)
    assert [cell.value for cell in wb["Summary"][1]] == SUMMARY_HEADERS
    assert wb["Summary"]["A2"].value == "R001"
    assert wb["Summary"]["B2"].value == "Ana"
    assert wb["Summary"]["C2"].value == "N/A"
    assert wb["LeetCode"].freeze_panes == "A2"


def test_weekly_progress_compares_two_latest_snapshots(tmp_path):
    db = Database(tmp_path / "profiles.db")
    profile_id, _ = db.upsert_profile("Ana", "Codeforces", "ana", "https://codeforces.com/profile/ana")
    db.save_success(profile_id, ProfileResult(platform="Codeforces", username="ana", profile_url="x", problems_solved=10, rating=1200))
    db.save_success(profile_id, ProfileResult(platform="Codeforces", username="ana", profile_url="x", problems_solved=14, rating=1255))
    row = weekly_progress_rows(db)[0]
    assert row["Problems Added"] == 4
    assert row["Rating Change"] == 55
