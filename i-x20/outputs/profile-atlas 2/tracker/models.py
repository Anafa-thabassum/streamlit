from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


@dataclass
class Activity:
    activity_id: str
    date: str | None = None
    activity_type: str = "Activity"
    title: str | None = None
    difficulty: str | None = None
    status: str | None = None
    rating_change: float | None = None
    url: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class ProfileResult:
    platform: str
    username: str
    profile_url: str
    fetched_at: str = field(default_factory=utc_now_iso)
    rating: float | None = None
    max_rating: float | None = None
    rank: str | int | None = None
    max_rank: str | None = None
    global_rank: int | None = None
    country_rank: int | None = None
    problems_solved: int | None = None
    easy: int | None = None
    medium: int | None = None
    hard: int | None = None
    contest_rating: float | None = None
    contest_rank: int | None = None
    contests_attended: int | None = None
    total_submissions: int | None = None
    acceptance_rate: float | None = None
    reputation: int | None = None
    followers: int | None = None
    following: int | None = None
    repositories: int | None = None
    contributions: int | None = None
    stars_received: int | None = None
    forks: int | None = None
    badges: list[str] = field(default_factory=list)
    certificates: list[str] = field(default_factory=list)
    name: str | None = None
    bio: str | None = None
    headline: str | None = None
    connections: int | None = None
    coding_score: int | None = None
    hackos: float | None = None
    articles: int | None = None
    account_created: str | None = None
    last_activity: str | None = None
    stars: str | int | None = None
    raw_data: dict[str, Any] = field(default_factory=dict)
    activities: list[Activity] = field(default_factory=list)

    def snapshot_metrics(self) -> dict[str, Any]:
        data = asdict(self)
        data.pop("activities", None)
        return data


@dataclass
class FetchError:
    error_type: str
    message: str
    status_code: int | None = None


class FetchException(Exception):
    def __init__(self, error_type: str, message: str, status_code: int | None = None):
        super().__init__(message)
        self.error = FetchError(error_type, message, status_code)
