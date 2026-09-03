from __future__ import annotations

import json
import re

from bs4 import BeautifulSoup

from tracker.models import Activity, FetchException, ProfileResult

from .base import BaseScraper, int_or_none


class CodeChefScraper(BaseScraper):
    platform = "CodeChef"

    @staticmethod
    def _number(text: str, *patterns: str) -> int | None:
        for pattern in patterns:
            match = re.search(pattern, text, re.I | re.S)
            if match:
                return int_or_none(match.group(1).replace(",", ""))
        return None

    @classmethod
    def _labelled_number(cls, soup: BeautifulSoup, label: str) -> int | None:
        """Read a statistic from CodeChef's rank cards or their text fallback."""
        label_pattern = re.compile(rf"\b{re.escape(label)}\b", re.I)
        for node in soup.find_all(string=label_pattern):
            parent = node.parent
            for candidate in (parent, parent.parent if parent else None):
                if candidate:
                    value = cls._number(candidate.get_text(" ", strip=True), r"([\d,]+)")
                    if value is not None:
                        return value
        return None

    @classmethod
    def _current_rank(cls, soup: BeautifulSoup, *, country: bool = False) -> int | None:
        """Read the current CodeChef rating-card rank, excluding contest history and DSA rank."""
        for item in soup.select("ul.inline-list li"):
            item_text = item.get_text(" ", strip=True)
            expected_label = "Country Rank" if country else "Global Rank"
            if expected_label.lower() not in item_text.lower():
                continue
            link = item.select_one("a[href]")
            href = (link.get("href") or "") if link else ""
            is_overall = href.startswith("/ratings/all")
            is_country = "filterBy=" in href or "filterby=" in href.lower()
            if is_overall and is_country == country:
                strong = item.select_one("strong")
                return cls._number(strong.get_text(" ", strip=True) if strong else item_text, r"([\d,]+)")
        return None

    def fetch(self, username: str, profile_url: str) -> ProfileResult:
        response = self.client.request(
            "GET", profile_url, platform=self.platform, headers={"Accept": "text/html"}
        )
        soup = BeautifulSoup(response.text, "html.parser")
        text = soup.get_text(" ", strip=True)
        if "user does not exist" in text.lower() or "profile not found" in text.lower():
            raise FetchException("Profile not found", "CodeChef profile was not found")
        rating_node = soup.select_one(".rating-number")
        rating = int_or_none(rating_node.get_text(strip=True).split("?")[0].replace(",", "")) if rating_node else self._number(text, r"Current Rating\s*[:\-]?\s*([\d,]+)")
        highest = self._number(text, r"Highest Rating\s*[:\-]?\s*([\d,]+)", r"Highest\s*([\d,]+)")
        global_rank = self._current_rank(soup) or self._labelled_number(soup, "Global Rank") or self._number(text, r"Global Rank\s*[:\-]?\s*([\d,]+)")
        country_rank = self._current_rank(soup, country=True) or self._labelled_number(soup, "Country Rank") or self._number(text, r"Country Rank\s*[:\-]?\s*([\d,]+)")
        solved = self._number(text, r"Fully Solved\s*\(([\d,]+)\)", r"Problems Solved\s*[:\-]?\s*([\d,]+)")
        contests = self._number(
            text,
            r"No\.?\s*of\s*Contests\s*Participated\s*[:\-]?\s*([\d,]+)",
            r"Contests\s*Participated\s*[:\-]?\s*([\d,]+)",
            r"Contests\s*\(([\d,]+)\)",
        )
        submissions = self._number(
            text,
            r"Total\s*Submissions\s*[:\-]?\s*([\d,]+)",
            r"Submissions\s*[:\-]?\s*([\d,]+)",
        )
        stars = None
        star_node = soup.select_one(".rating-star")
        if star_node:
            stars = star_node.get_text(strip=True)
        activities: list[Activity] = []
        for row in soup.select("table.rating-table tr")[-25:]:
            cells = [cell.get_text(" ", strip=True) for cell in row.select("td")]
            link = row.select_one("a[href]")
            if len(cells) >= 4 and link:
                contest_url = link.get("href")
                if contest_url and contest_url.startswith("/"):
                    contest_url = "https://www.codechef.com" + contest_url
                change = None
                change_match = re.search(r"([+-]?\d+)", cells[-1])
                if change_match:
                    change = int_or_none(change_match.group(1))
                activities.append(Activity(
                    activity_id=f"contest-{contest_url or cells[0]}",
                    date=cells[1] if len(cells) > 1 else None,
                    activity_type="Contest",
                    title=cells[0],
                    status="Participated",
                    rating_change=change,
                    url=contest_url,
                    metadata={"rank": cells[2] if len(cells) > 2 else None},
                ))
        raw: dict = {}
        next_data = soup.select_one("script#__NEXT_DATA__")
        if next_data and next_data.string:
            try:
                raw["page_data"] = json.loads(next_data.string)
            except json.JSONDecodeError:
                pass
        if rating is None and solved is None and not soup.title:
            raise FetchException("Parsing error", "CodeChef public profile format was not recognized")
        return ProfileResult(
            platform=self.platform,
            username=username,
            profile_url=profile_url,
            rating=rating,
            max_rating=highest,
            global_rank=global_rank,
            rank=global_rank,
            country_rank=country_rank,
            problems_solved=solved,
            # The history table can be truncated, so only use its length as a
            # fallback when the public summary does not expose a contest total.
            contests_attended=contests if contests is not None else (len(activities) or None),
            total_submissions=submissions,
            stars=stars,
            last_activity=max((a.date for a in activities if a.date), default=None),
            raw_data=raw,
            activities=activities,
        )
