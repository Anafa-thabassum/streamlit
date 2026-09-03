import json
from urllib.parse import quote

from tracker.models import FetchException
from tracker.scrapers.hackerrank import HackerRankScraper


class FakeResponse:
    def __init__(self, *, text="", payload=None):
        self.text = text
        self._payload = payload

    def json(self):
        return self._payload


class FakeClient:
    def request(self, method, url, **kwargs):
        if "/rest/hackers/" in url:
            raise FetchException("Profile not found", "retired route", 404)
        state = {
            "community": {
                "viewProfiles": {
                    "ana": {
                        "username": "ana",
                        "name": "Ana",
                        "short_bio": "Developer",
                        "followers_count": 3,
                        "created_at": "2025-01-01T00:00:00.000Z",
                        "badges": [
                            {"badge_name": "Python", "stars": 2, "solved": 7},
                            {"badge_name": "SQL", "stars": 1, "solved": 4},
                        ],
                    }
                }
            }
        }
        html = f"<html><script>{quote(json.dumps(state))}</script></html>"
        return FakeResponse(text=html)


def test_public_page_fallback_when_legacy_profile_route_is_missing():
    result = HackerRankScraper(FakeClient()).fetch("ana", "https://www.hackerrank.com/profile/ana")
    assert result.name == "Ana"
    assert result.problems_solved == 11
    assert result.followers == 3
    assert result.stars == 3
    assert result.badges == ["Python (2★)", "SQL (1★)"]
