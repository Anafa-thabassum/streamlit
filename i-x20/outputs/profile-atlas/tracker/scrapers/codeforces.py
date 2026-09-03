from __future__ import annotations

from tracker.models import Activity, FetchException, ProfileResult

from .base import BaseScraper, iso_from_epoch


class CodeforcesScraper(BaseScraper):
    platform = "Codeforces"
    api = "https://codeforces.com/api"

    def _call(self, method: str, **params):
        payload = self.get_json(f"{self.api}/{method}", params=params)
        if payload.get("status") != "OK":
            comment = payload.get("comment", "Unknown Codeforces API error")
            kind = "Profile not found" if "not found" in comment.lower() else "API unavailable"
            raise FetchException(kind, comment)
        return payload.get("result", [])

    def fetch(self, username: str, profile_url: str) -> ProfileResult:
        info_rows = self._call("user.info", handles=username)
        if not info_rows:
            raise FetchException("Profile not found", "Codeforces profile was not found")
        info = info_rows[0]
        submissions = []
        offset = 1
        # Codeforces returns submissions in pages. Fetch all available pages so the
        # solved count is not silently based on only the most recent activity.
        while True:
            page = self._call("user.status", handle=username, **{"from": offset, "count": 1000})
            submissions.extend(page)
            if len(page) < 1000:
                break
            offset += 1000
        contests = self._call("user.rating", handle=username)
        solved = {
            f"{s.get('problem', {}).get('contestId', '')}-{s.get('problem', {}).get('index', '')}"
            for s in submissions
            if s.get("verdict") == "OK"
        }
        activities: list[Activity] = []
        for contest in contests[-25:]:
            activities.append(Activity(
                activity_id=f"contest-{contest.get('contestId')}",
                date=iso_from_epoch(contest.get("ratingUpdateTimeSeconds")),
                activity_type="Contest",
                title=contest.get("contestName"),
                status="Participated",
                rating_change=(contest.get("newRating", 0) - contest.get("oldRating", 0)),
                url=f"https://codeforces.com/contest/{contest.get('contestId')}",
                metadata={"rank": contest.get("rank"), "rating_before": contest.get("oldRating"), "rating_after": contest.get("newRating")},
            ))
        for submission in submissions[:50]:
            problem = submission.get("problem", {})
            activities.append(Activity(
                activity_id=f"submission-{submission.get('id')}",
                date=iso_from_epoch(submission.get("creationTimeSeconds")),
                activity_type="Submission",
                title=problem.get("name"),
                difficulty=str(problem.get("rating")) if problem.get("rating") else None,
                status=submission.get("verdict"),
                url=f"https://codeforces.com/contest/{problem.get('contestId')}/submission/{submission.get('id')}",
                metadata={"language": submission.get("programmingLanguage")},
            ))
        return ProfileResult(
            platform=self.platform,
            username=username,
            profile_url=profile_url,
            rating=info.get("rating"),
            max_rating=info.get("maxRating"),
            rank=info.get("rank"),
            max_rank=info.get("maxRank"),
            problems_solved=len(solved),
            contests_attended=len(contests),
            name=" ".join(filter(None, [info.get("firstName"), info.get("lastName")])) or None,
            last_activity=iso_from_epoch(info.get("lastOnlineTimeSeconds")),
            raw_data={"organization": info.get("organization"), "country": info.get("country")},
            activities=activities,
        )
