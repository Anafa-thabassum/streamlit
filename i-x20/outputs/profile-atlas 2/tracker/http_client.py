from __future__ import annotations

import random
import threading
import time
from collections import defaultdict
from typing import Any

import requests

from .models import FetchException


class PublicHttpClient:
    """Small requests wrapper with bounded retries and per-platform pacing."""

    # Scrapers create separate client instances. Rate limits must therefore be
    # coordinated across the whole process rather than per client instance.
    _shared_locks: dict[str, threading.Lock] = defaultdict(threading.Lock)
    _shared_last_request: dict[str, float] = defaultdict(float)

    def __init__(self, timeout: float, user_agent: str, github_token: str | None = None):
        self.timeout = timeout
        self.session = requests.Session()
        self.session.headers.update({"User-Agent": user_agent, "Accept": "application/json"})
        self.github_token = github_token
        self.minimum_intervals = {
            "CodeChef": 2.25,
            "LeetCode": 0.35,
            "HackerRank": 0.6,
            "Codeforces": 0.45,
            "GFG": 1.0,
            "LinkedIn": 2.0,
            "GitHub": 0.15,
        }

    def _pace(self, platform: str) -> None:
        with self._shared_locks[platform]:
            wait = self.minimum_intervals.get(platform, 0.2) - (
                time.monotonic() - self._shared_last_request[platform]
            )
            if wait > 0:
                time.sleep(wait)
            self._shared_last_request[platform] = time.monotonic()

    def request(
        self,
        method: str,
        url: str,
        *,
        platform: str,
        retries: int = 2,
        **kwargs: Any,
    ) -> requests.Response:
        headers = dict(kwargs.pop("headers", {}))
        if platform == "GitHub" and self.github_token:
            headers["Authorization"] = f"Bearer {self.github_token}"
            headers["X-GitHub-Api-Version"] = "2022-11-28"
        for attempt in range(retries + 1):
            self._pace(platform)
            try:
                response = self.session.request(
                    method, url, timeout=self.timeout, headers=headers, **kwargs
                )
            except requests.Timeout as exc:
                if attempt == retries:
                    raise FetchException("Timeout", f"{platform} did not respond in time") from exc
            except requests.RequestException as exc:
                if attempt == retries:
                    raise FetchException("API unavailable", str(exc)) from exc
            else:
                if response.status_code == 404:
                    raise FetchException("Profile not found", f"{platform} profile was not found", 404)
                if response.status_code in {401, 403}:
                    kind = "Rate limited" if response.headers.get("X-RateLimit-Remaining") == "0" else "Authentication required"
                    raise FetchException(kind, f"{platform} returned HTTP {response.status_code}", response.status_code)
                if response.status_code == 429:
                    if attempt == retries:
                        raise FetchException("Rate limited", f"{platform} rate limit reached", 429)
                    retry_after = response.headers.get("Retry-After")
                    try:
                        retry_delay = min(60.0, max(0.0, float(retry_after)))
                    except (TypeError, ValueError):
                        retry_delay = 2**attempt
                    time.sleep(retry_delay)
                elif response.status_code >= 500:
                    if attempt == retries:
                        raise FetchException("API unavailable", f"{platform} returned HTTP {response.status_code}", response.status_code)
                elif response.status_code >= 400:
                    raise FetchException("API unavailable", f"{platform} returned HTTP {response.status_code}", response.status_code)
                else:
                    return response
            if attempt < retries:
                time.sleep((2**attempt) + random.uniform(0, 0.25))
        raise FetchException("API unavailable", f"Could not reach {platform}")
