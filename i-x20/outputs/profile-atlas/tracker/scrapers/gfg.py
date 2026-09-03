from __future__ import annotations

import re

from bs4 import BeautifulSoup

from tracker.models import FetchException, ProfileResult

from .base import BaseScraper, int_or_none


class GFGScraper(BaseScraper):
    platform = "GFG"

    @staticmethod
    def _number(text: str, *labels: str) -> int | None:
        for label in labels:
            match = re.search(rf"{label}\s*[:\-]?\s*([\d,]+)", text, re.I)
            if match:
                return int_or_none(match.group(1).replace(",", ""))
        return None

    def fetch(self, username: str, profile_url: str) -> ProfileResult:
        response = self.client.request(
            "GET", profile_url, platform=self.platform, headers={"Accept": "text/html"}
        )
        soup = BeautifulSoup(response.text, "html.parser")
        text = soup.get_text(" ", strip=True)
        if response.status_code == 404 or "user not found" in text.lower():
            raise FetchException("Profile not found", "GFG profile was not found")
        score = self._number(text, "Coding Score", "Overall Coding Score")
        solved = self._number(text, "Problem Solved", "Problems Solved", "Total Problems Solved")
        rank = self._number(text, "Institute Rank", "Overall Rank", "Rank")
        articles = self._number(text, "Articles Published", "Articles")
        if score is None and solved is None and not soup.title:
            raise FetchException("Parsing error", "GFG public profile format was not recognized")
        return ProfileResult(
            platform=self.platform,
            username=username,
            profile_url=profile_url,
            coding_score=score,
            problems_solved=solved,
            rank=rank,
            articles=articles,
            raw_data={"note": "Metrics are parsed only from the publicly accessible profile page."},
        )
