from tracker.database import Database
from tracker.models import Activity, FetchError, ProfileResult


def test_upsert_snapshot_history_and_activity_deduplication(tmp_path):
    db = Database(tmp_path / "profiles.db")
    profile_id, created = db.upsert_profile("Ana", "GitHub", "octocat", "https://github.com/octocat")
    assert created
    same_id, created = db.upsert_profile("Ana", "GitHub", "octocat", "https://github.com/octocat/")
    assert not created and same_id == profile_id
    first = ProfileResult(
        platform="GitHub", username="octocat", profile_url="https://github.com/octocat",
        repositories=8, followers=10,
        activities=[Activity("event-1", "2026-09-01T00:00:00+00:00", "Push", "repo")],
    )
    second = ProfileResult(
        platform="GitHub", username="octocat", profile_url="https://github.com/octocat",
        repositories=9, followers=12,
        activities=[Activity("event-1", "2026-09-01T00:00:00+00:00", "Push", "repo")],
    )
    db.save_success(profile_id, first)
    db.save_success(profile_id, second)
    assert db.query("SELECT COUNT(*) AS n FROM profile_snapshots")[0]["n"] == 2
    assert db.query("SELECT COUNT(*) AS n FROM activities")[0]["n"] == 1
    assert db.list_profiles()[0]["fetch_status"] == "Success"


def test_failure_is_recorded(tmp_path):
    db = Database(tmp_path / "profiles.db")
    profile_id, _ = db.upsert_profile("Ana", "GitHub", "missing", "https://github.com/missing")
    db.save_failure(profile_id, FetchError("Profile not found", "No such profile"))
    assert db.list_profiles()[0]["fetch_status"] == "Failed"
    assert db.query("SELECT error_type FROM fetch_logs")[0]["error_type"] == "Profile not found"


def test_student_details_update_all_linked_profiles_and_register_search(tmp_path):
    db = Database(tmp_path / "profiles.db")
    first, _ = db.upsert_profile("Old Name", "GitHub", "ana", "https://github.com/ana", "R001")
    second, _ = db.upsert_profile("Old Name", "CodeChef", "ana", "https://codechef.com/users/ana", "R001")
    db.update_student_details([first, second], "R009", "New Name")
    rows = db.list_profiles(search="R009")
    assert len(rows) == 2
    assert {row["student_name"] for row in rows} == {"New Name"}
    assert {row["student_register_no"] for row in rows} == {"R009"}
