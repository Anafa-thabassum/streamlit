from __future__ import annotations

from tracker.models import Activity, ProfileResult

from .base import BaseScraper


class GitHubScraper(BaseScraper):
    platform = "GitHub"
    api = "https://api.github.com"

    def fetch(self, username: str, profile_url: str) -> ProfileResult:
        user = self.get_json(f"{self.api}/users/{username}")
        repos = []
        page_number = 1
        while True:
            page = self.get_json(
                f"{self.api}/users/{username}/repos",
                params={"per_page": 100, "sort": "updated", "page": page_number},
            )
            repos.extend(page)
            if len(page) < 100:
                break
            page_number += 1
        events = self.get_json(
            f"{self.api}/users/{username}/events/public", params={"per_page": 100}
        )
        stars = sum(repo.get("stargazers_count", 0) or 0 for repo in repos)
        forks = sum(repo.get("forks_count", 0) or 0 for repo in repos)
        activities: list[Activity] = []
        for event in events:
            repo = event.get("repo", {}).get("name")
            event_type = event.get("type", "GitHub event").removesuffix("Event")
            payload = event.get("payload", {})
            title = repo
            status = event_type
            if event.get("type") == "PushEvent":
                commits = payload.get("commits", [])
                commit_count = payload.get("size") if payload.get("size") is not None else len(commits)
                title = f"{repo} ({commit_count} commit{'s' if commit_count != 1 else ''})"
            elif event.get("type") == "PullRequestEvent":
                title = payload.get("pull_request", {}).get("title") or repo
                status = payload.get("action") or event_type
            elif event.get("type") == "IssuesEvent":
                title = payload.get("issue", {}).get("title") or repo
                status = payload.get("action") or event_type
            activities.append(Activity(
                activity_id=f"event-{event.get('id')}",
                date=event.get("created_at"),
                activity_type=event_type,
                title=title,
                status=status,
                url=f"https://github.com/{repo}" if repo else profile_url,
                metadata={
                    "repository": repo,
                    "commit_count": (
                        payload.get("size") if payload.get("size") is not None
                        else len(payload.get("commits", []))
                    ) if event.get("type") == "PushEvent" else 0,
                },
            ))
        return ProfileResult(
            platform=self.platform,
            username=username,
            profile_url=profile_url,
            name=user.get("name"),
            bio=user.get("bio"),
            followers=user.get("followers"),
            following=user.get("following"),
            repositories=user.get("public_repos"),
            stars_received=stars,
            forks=forks,
            account_created=user.get("created_at"),
            last_activity=max((e.get("created_at") for e in events), default=None),
            contributions=None,
            raw_data={"company": user.get("company"), "location": user.get("location"), "blog": user.get("blog"), "contributions_note": "Not exposed by GitHub REST API"},
            activities=activities,
        )
