from __future__ import annotations

from tracker.models import ProfileResult

from .base import BaseScraper


class LinkedInScraper(BaseScraper):
    platform = "LinkedIn"

    def fetch(self, username: str, profile_url: str) -> ProfileResult:
        # LinkedIn profile data generally requires authenticated, contract-approved APIs.
        # Preserve the public URL without scraping or attempting to bypass access controls.
        return ProfileResult(
            platform=self.platform,
            username=username,
            profile_url=profile_url,
            raw_data={"note": "URL recorded; profile metrics require a permitted LinkedIn API integration."},
        )
