from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import datetime, timezone
from typing import Any

from tracker.http_client import PublicHttpClient
from tracker.models import FetchException, ProfileResult


def iso_from_epoch(value: int | float | None) -> str | None:
    if value is None:
        return None
    return datetime.fromtimestamp(value, tz=timezone.utc).replace(microsecond=0).isoformat()


def int_or_none(value: Any) -> int | None:
    try:
        return int(value) if value is not None and value != "" else None
    except (TypeError, ValueError):
        return None


def float_or_none(value: Any) -> float | None:
    try:
        return float(value) if value is not None and value != "" else None
    except (TypeError, ValueError):
        return None


class BaseScraper(ABC):
    platform: str

    def __init__(self, client: PublicHttpClient):
        self.client = client

    def get_json(self, url: str, **kwargs: Any) -> Any:
        response = self.client.request("GET", url, platform=self.platform, **kwargs)
        try:
            return response.json()
        except ValueError as exc:
            raise FetchException("Parsing error", f"{self.platform} returned invalid JSON") from exc

    @abstractmethod
    def fetch(self, username: str, profile_url: str) -> ProfileResult:
        raise NotImplementedError

