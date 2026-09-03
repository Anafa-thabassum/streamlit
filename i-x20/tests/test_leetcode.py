from tracker.scrapers.leetcode import LeetCodeScraper


class FakeResponse:
    def json(self):
        return {
            "data": {
                "matchedUser": {
                    "username": "ana",
                    "profile": {"ranking": 10, "reputation": 0},
                    "submitStatsGlobal": {
                        "acSubmissionNum": [
                            {"difficulty": "All", "count": 1, "submissions": 1},
                            {"difficulty": "Easy", "count": 1, "submissions": 1},
                        ],
                        "totalSubmissionNum": [
                            {"difficulty": "All", "count": 2, "submissions": 2},
                        ],
                    },
                    "badges": [],
                },
                "userContestRanking": None,
                "recentSubmissionList": [
                    {
                        "title": "Two Sum",
                        "titleSlug": "two-sum",
                        "timestamp": "1767225600",
                        "statusDisplay": "Accepted",
                        "lang": "python3",
                    }
                ],
            }
        }


class FakeClient:
    def request(self, *args, **kwargs):
        return FakeResponse()


def test_submission_epoch_is_normalized_to_iso_date():
    result = LeetCodeScraper(FakeClient()).fetch("ana", "https://leetcode.com/u/ana")
    assert result.activities[0].date == "2026-01-01T00:00:00+00:00"
    assert result.total_submissions == 2
    assert result.acceptance_rate == 50.0
