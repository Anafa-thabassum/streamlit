from __future__ import annotations

import re
from dataclasses import dataclass
from urllib.parse import unquote, urlparse


PLATFORMS = (
    "CodeChef",
    "LeetCode",
    "HackerRank",
    "Codeforces",
    "GFG",
    "LinkedIn",
    "GitHub",
)

PLATFORM_ALIASES = {
    "codechef": "CodeChef",
    "leetcode": "LeetCode",
    "hackerrank": "HackerRank",
    "codeforces": "Codeforces",
    "gfg": "GFG",
    "geeksforgeeks": "GFG",
    "linkedin": "LinkedIn",
    "github": "GitHub",
}


@dataclass(frozen=True)
class ParsedProfile:
    platform: str
    username: str
    url: str


class InvalidProfileUrl(ValueError):
    pass


def normalize_platform(value: str) -> str | None:
    key = re.sub(r"[^a-z]", "", str(value).lower())
    return PLATFORM_ALIASES.get(key)


def _normalized_url(value: str) -> str:
    value = str(value).strip()
    if not value or value.lower() in {"n/a", "na", "none", "nan", "-"}:
        raise InvalidProfileUrl("Profile URL is empty")
    if not re.match(r"^https?://", value, re.I):
        value = "https://" + value
    parsed = urlparse(value)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        raise InvalidProfileUrl("URL must be a valid http(s) address")
    return value


def _candidate_url(canonical: str, value: str) -> str:
    expected_hosts = {
        "CodeChef": ("codechef.com",),
        "LeetCode": ("leetcode.com",),
        "HackerRank": ("hackerrank.com",),
        "Codeforces": ("codeforces.com",),
        "GFG": ("geeksforgeeks.org",),
        "LinkedIn": ("linkedin.com",),
        "GitHub": ("github.com",),
    }[canonical]
    raw = str(value).strip()
    url_starts = list(re.finditer(r"https?://", raw, re.I))
    for index, match in enumerate(url_starts):
        end = url_starts[index + 1].start() if index + 1 < len(url_starts) else len(raw)
        candidate = raw[match.start():end].strip().split()[0].strip("\"'<>),;")
        parsed = urlparse(candidate)
        host = parsed.netloc.lower().split(":")[0]
        host = host[4:] if host.startswith("www.") else host
        if any(host == item or host.endswith("." + item) for item in expected_hosts):
            return candidate
    return raw


def parse_profile_url(platform: str, value: str) -> ParsedProfile:
    canonical = normalize_platform(platform)
    if not canonical:
        raise InvalidProfileUrl(f"Unsupported platform: {platform}")
    url = _normalized_url(_candidate_url(canonical, value))
    parsed = urlparse(url)
    host = parsed.netloc.lower().split(":")[0]
    host = host[4:] if host.startswith("www.") else host
    parts = [unquote(p).strip() for p in parsed.path.split("/") if p.strip()]

    expected = {
        "CodeChef": ("codechef.com",),
        "LeetCode": ("leetcode.com",),
        "HackerRank": ("hackerrank.com",),
        "Codeforces": ("codeforces.com",),
        "GFG": ("geeksforgeeks.org",),
        "LinkedIn": ("linkedin.com",),
        "GitHub": ("github.com",),
    }[canonical]
    if not any(host == item or host.endswith("." + item) for item in expected):
        raise InvalidProfileUrl(f"URL host does not match {canonical}")

    username: str | None = None
    if canonical == "LeetCode":
        if parts and parts[0].lower() == "u" and len(parts) > 1:
            username = parts[1]
        elif parts:
            username = parts[0]
    elif canonical == "CodeChef":
        if len(parts) > 1 and parts[0].lower() == "users":
            username = parts[1]
    elif canonical == "Codeforces":
        if len(parts) > 1 and parts[0].lower() == "profile":
            username = parts[1]
    elif canonical == "HackerRank":
        if len(parts) > 1 and parts[0].lower() == "profile":
            username = parts[1]
        elif parts:
            username = parts[0]
    elif canonical == "GFG":
        if len(parts) > 1 and parts[0].lower() in {"user", "profile"}:
            username = parts[1]
    elif canonical == "LinkedIn":
        if len(parts) > 1 and parts[0].lower() in {"in", "pub"}:
            username = parts[1]
    elif canonical == "GitHub":
        if parts and parts[0].lower() not in {
            "about", "apps", "collections", "contact", "enterprise", "events",
            "features", "issues", "marketplace", "new", "notifications",
            "orgs", "organizations", "pricing", "pulls", "search", "settings",
            "site", "sponsors", "topics", "trending",
        }:
            username = parts[0]

    if not username or not re.fullmatch(r"[A-Za-z0-9_.-]{1,100}", username):
        raise InvalidProfileUrl(f"Could not extract a valid {canonical} username")
    clean_url = f"{parsed.scheme}://{parsed.netloc}{parsed.path}".rstrip("/")
    return ParsedProfile(canonical, username, clean_url)
