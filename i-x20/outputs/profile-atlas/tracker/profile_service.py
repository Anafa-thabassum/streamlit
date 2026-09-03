from __future__ import annotations

import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from typing import Callable, Iterable

from .config import Settings
from .database import Database
from .excel_reader import ImportResult
from .http_client import PublicHttpClient
from .models import FetchError, FetchException, ProfileResult
from .scrapers import SCRAPER_CLASSES


@dataclass
class FetchSummary:
    total: int = 0
    succeeded: int = 0
    failed: int = 0


class ProfileService:
    def __init__(self, database: Database, settings: Settings, logger: logging.Logger):
        self.database = database
        self.settings = settings
        self.logger = logger

    def import_profiles(self, imported: ImportResult) -> tuple[int, int]:
        added = updated = 0
        for profile in imported.profiles:
            _, created = self.database.upsert_profile(**profile)
            if created:
                added += 1
            else:
                updated += 1
        if imported.issues:
            self.database.save_import_errors(imported.issues)
        return added, updated

    def _new_scraper(self, platform: str):
        client = PublicHttpClient(
            timeout=self.settings.request_timeout_seconds,
            user_agent=self.settings.user_agent,
            github_token=self.settings.github_token,
        )
        return SCRAPER_CLASSES[platform](client)

    def fetch_profiles(
        self,
        profiles: Iterable[dict],
        progress: Callable[[int, int, dict, bool], None] | None = None,
    ) -> FetchSummary:
        rows = list(profiles)
        summary = FetchSummary(total=len(rows))
        if not rows:
            return summary

        # Cache by platform + username for this run, while preserving one snapshot per student profile.
        groups: dict[tuple[str, str], list[dict]] = {}
        for row in rows:
            groups.setdefault((row["platform"], row["username"].casefold()), []).append(row)

        def fetch_group(item: tuple[tuple[str, str], list[dict]]):
            (_, _), duplicates = item
            representative = duplicates[0]
            scraper = self._new_scraper(representative["platform"])
            return duplicates, scraper.fetch(representative["username"], representative["profile_url"])

        completed = 0
        workers = min(self.settings.max_workers, len(groups))
        with ThreadPoolExecutor(max_workers=max(1, workers), thread_name_prefix="profile-fetch") as executor:
            futures = {executor.submit(fetch_group, item): item for item in groups.items()}
            for future in as_completed(futures):
                (_, _), duplicates = futures[future]
                try:
                    _, result = future.result()
                except FetchException as exc:
                    for profile in duplicates:
                        self.database.save_failure(profile["id"], exc.error)
                        summary.failed += 1
                        completed += 1
                        self.logger.error("%s %s: %s", profile["platform"], profile["username"], exc)
                        if progress:
                            progress(completed, summary.total, profile, False)
                except Exception as exc:  # a single unexpected adapter failure must not end the batch
                    error = FetchError("Unexpected error", str(exc))
                    for profile in duplicates:
                        self.database.save_failure(profile["id"], error)
                        summary.failed += 1
                        completed += 1
                        self.logger.exception("Unexpected failure for %s %s", profile["platform"], profile["username"])
                        if progress:
                            progress(completed, summary.total, profile, False)
                else:
                    for profile in duplicates:
                        cloned = ProfileResult(**{
                            **result.__dict__,
                            "profile_url": profile["profile_url"],
                        })
                        self.database.save_success(profile["id"], cloned)
                        summary.succeeded += 1
                        completed += 1
                        self.logger.info("Fetched %s profile: %s", profile["platform"], profile["username"])
                        if progress:
                            progress(completed, summary.total, profile, True)
        return summary
