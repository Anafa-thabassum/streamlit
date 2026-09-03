import logging

from tracker.config import Settings
from tracker.database import Database
from tracker.models import FetchException, ProfileResult
from tracker.profile_service import ProfileService


class SuccessfulScraper:
    def __init__(self, client): pass
    def fetch(self, username, profile_url):
        return ProfileResult(platform="GitHub", username=username, profile_url=profile_url, followers=5)


class TimeoutScraper:
    def __init__(self, client): pass
    def fetch(self, username, profile_url):
        raise FetchException("Timeout", "Timed out")


def settings_for(tmp_path):
    return Settings(database_path=tmp_path / "profiles.db", reports_dir=tmp_path / "reports", max_workers=2)


def test_duplicate_accounts_are_fetched_once(monkeypatch, tmp_path):
    db = Database(tmp_path / "profiles.db")
    for name in ["Ana", "Ben"]:
        db.upsert_profile(name, "GitHub", "octocat", "https://github.com/octocat")
    calls = {"n": 0}
    class CountingScraper(SuccessfulScraper):
        def fetch(self, username, profile_url):
            calls["n"] += 1
            return super().fetch(username, profile_url)
    monkeypatch.setitem(__import__("tracker.profile_service", fromlist=["SCRAPER_CLASSES"]).SCRAPER_CLASSES, "GitHub", CountingScraper)
    summary = ProfileService(db, settings_for(tmp_path), logging.getLogger("test")).fetch_profiles(db.list_profiles())
    assert calls["n"] == 1
    assert summary.succeeded == 2
    assert db.query("SELECT COUNT(*) n FROM profile_snapshots")[0]["n"] == 2


def test_api_timeout_does_not_crash_batch(monkeypatch, tmp_path):
    db = Database(tmp_path / "profiles.db")
    db.upsert_profile("Ana", "GitHub", "octocat", "https://github.com/octocat")
    monkeypatch.setitem(__import__("tracker.profile_service", fromlist=["SCRAPER_CLASSES"]).SCRAPER_CLASSES, "GitHub", TimeoutScraper)
    summary = ProfileService(db, settings_for(tmp_path), logging.getLogger("test")).fetch_profiles(db.list_profiles())
    assert summary.failed == 1
    assert db.list_profiles()[0]["fetch_status"] == "Failed"
