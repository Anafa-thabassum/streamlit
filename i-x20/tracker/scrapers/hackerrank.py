from __future__ import annotations

import json
from urllib.parse import unquote

from bs4 import BeautifulSoup

from tracker.models import FetchException, ProfileResult

from .base import BaseScraper, int_or_none


class HackerRankScraper(BaseScraper):
    platform = "HackerRank"
    api = "https://www.hackerrank.com/rest/hackers"

    def _public_page_profile(self, username: str, profile_url: str) -> dict:
        response = self.client.request(
            "GET", profile_url, platform=self.platform, headers={"Accept": "text/html"}
        )
        soup = BeautifulSoup(response.text, "html.parser")
        for script in soup.find_all("script"):
            content = (script.string or script.get_text() or "").strip()
            if "%22viewProfiles%22" not in content:
                continue
            try:
                state = json.loads(unquote(content))
                profile = state.get("community", {}).get("viewProfiles", {}).get(username)
            except (json.JSONDecodeError, TypeError, AttributeError):
                continue
            if isinstance(profile, dict):
                return profile
        raise FetchException("Profile not found", "HackerRank public profile data was not found")

    def fetch(self, username: str, profile_url: str) -> ProfileResult:
        try:
            payload = self.get_json(f"{self.api}/{username}/profile")
            model = payload.get("model") or payload
        except FetchException as exc:
            if exc.error.error_type != "Profile not found":
                raise
            # HackerRank retired the older JSON profile route for some accounts,
            # while the same public data remains embedded in the public page.
            model = self._public_page_profile(username, profile_url)
        embedded_badges = model.get("badges") or []
        if embedded_badges:
            badge_models = embedded_badges
        else:
            badges_payload = self.get_json(f"{self.api}/{username}/badges")
            badge_models = badges_payload.get("models", []) if isinstance(badges_payload, dict) else []
        badges = []
        for badge in badge_models:
            name = badge.get("badge_name") or badge.get("track_name")
            stars = badge.get("stars")
            if name:
                badges.append(f"{name} ({stars}★)" if stars is not None else name)
        solved_values = [int_or_none(badge.get("solved")) for badge in badge_models]
        solved_values = [value for value in solved_values if value is not None]
        return ProfileResult(
            platform=self.platform,
            username=username,
            profile_url=profile_url,
            name=model.get("name"),
            bio=model.get("bio"),
            rank=model.get("rank"),
            problems_solved=int_or_none(model.get("solved_challenges_count")) if model.get("solved_challenges_count") is not None else (sum(solved_values) if solved_values else None),
            followers=int_or_none(model.get("followers_count")),
            account_created=model.get("created_at"),
            stars=sum((int_or_none(badge.get("stars")) or 0) for badge in badge_models) if badge_models else None,
            badges=badges,
            certificates=[c.get("name") for c in model.get("certificates", []) if isinstance(c, dict) and c.get("name")],
            last_activity=model.get("last_activity_time"),
            raw_data={
                "country": model.get("country"),
                "school": model.get("school"),
                "company": model.get("company"),
                "badge_details": badge_models,
            },
        )
