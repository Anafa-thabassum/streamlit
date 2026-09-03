from __future__ import annotations

from tracker.models import Activity, FetchException, ProfileResult

from .base import BaseScraper, float_or_none, int_or_none, iso_from_epoch


class LeetCodeScraper(BaseScraper):
    platform = "LeetCode"
    endpoint = "https://leetcode.com/graphql"

    query = """
    query profile($username: String!) {
      matchedUser(username: $username) {
        username profile { realName ranking reputation starRating }
        submitStatsGlobal {
          acSubmissionNum { difficulty count submissions }
          totalSubmissionNum { difficulty count submissions }
        }
        badges { displayName creationDate }
      }
      userContestRanking(username: $username) {
        attendedContestsCount rating globalRanking topPercentage
      }
      recentSubmissionList(username: $username, limit: 30) {
        title titleSlug timestamp statusDisplay lang
      }
    }
    """

    def fetch(self, username: str, profile_url: str) -> ProfileResult:
        response = self.client.request(
            "POST",
            self.endpoint,
            platform=self.platform,
            json={"query": self.query, "variables": {"username": username}},
            headers={"Content-Type": "application/json", "Referer": profile_url},
        )
        try:
            payload = response.json()
        except ValueError as exc:
            raise FetchException("Parsing error", "LeetCode returned invalid JSON") from exc
        if payload.get("errors") and not payload.get("data"):
            raise FetchException("API unavailable", payload["errors"][0].get("message", "LeetCode GraphQL error"))
        data = payload.get("data") or {}
        user = data.get("matchedUser")
        if not user:
            raise FetchException("Profile not found", "LeetCode profile was not found or is private")
        profile = user.get("profile") or {}
        contest = data.get("userContestRanking") or {}
        counts = {item.get("difficulty"): item for item in (user.get("submitStatsGlobal") or {}).get("acSubmissionNum", [])}
        total = counts.get("All", {})
        total_counts = {item.get("difficulty"): item for item in (user.get("submitStatsGlobal") or {}).get("totalSubmissionNum", [])}
        all_submissions = total_counts.get("All", {})
        activities: list[Activity] = []
        for item in data.get("recentSubmissionList") or []:
            activities.append(Activity(
                activity_id=f"submission-{item.get('titleSlug')}-{item.get('timestamp')}-{item.get('lang')}",
                date=iso_from_epoch(int_or_none(item.get("timestamp"))),
                activity_type="Submission",
                title=item.get("title"),
                status=item.get("statusDisplay"),
                url=f"https://leetcode.com/problems/{item.get('titleSlug')}/",
                metadata={"language": item.get("lang")},
            ))
        submissions = int_or_none(all_submissions.get("submissions"))
        solved = int_or_none(total.get("count"))
        acceptance = round((solved / submissions) * 100, 2) if solved is not None and submissions else None
        return ProfileResult(
            platform=self.platform,
            username=username,
            profile_url=profile_url,
            name=profile.get("realName"),
            global_rank=int_or_none(profile.get("ranking")),
            rank=int_or_none(profile.get("ranking")),
            reputation=int_or_none(profile.get("reputation")),
            stars=float_or_none(profile.get("starRating")),
            problems_solved=solved,
            easy=int_or_none(counts.get("Easy", {}).get("count")),
            medium=int_or_none(counts.get("Medium", {}).get("count")),
            hard=int_or_none(counts.get("Hard", {}).get("count")),
            total_submissions=submissions,
            acceptance_rate=acceptance,
            contest_rating=float_or_none(contest.get("rating")),
            rating=float_or_none(contest.get("rating")),
            contest_rank=int_or_none(contest.get("globalRanking")),
            contests_attended=int_or_none(contest.get("attendedContestsCount")),
            badges=[b.get("displayName") for b in user.get("badges") or [] if b.get("displayName")],
            last_activity=max((a.date for a in activities if a.date), default=None),
            raw_data={"contest_top_percentage": contest.get("topPercentage")},
            activities=activities,
        )
