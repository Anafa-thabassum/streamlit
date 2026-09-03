import pytest

from tracker.url_parser import InvalidProfileUrl, parse_profile_url


@pytest.mark.parametrize(
    "platform,url,username",
    [
        ("LeetCode", "https://leetcode.com/u/ana_123/", "ana_123"),
        ("LeetCode", "leetcode.com/ana-123", "ana-123"),
        ("CodeChef", "https://www.codechef.com/users/ana123", "ana123"),
        ("Codeforces", "https://codeforces.com/profile/tourist", "tourist"),
        ("HackerRank", "https://www.hackerrank.com/profile/ana.123", "ana.123"),
        ("GFG", "https://www.geeksforgeeks.org/user/ana123/", "ana123"),
        ("LinkedIn", "https://linkedin.com/in/ana-sadiq", "ana-sadiq"),
        ("GitHub", "https://github.com/octocat", "octocat"),
    ],
)
def test_profile_url_parsing(platform, url, username):
    assert parse_profile_url(platform, url).username == username


@pytest.mark.parametrize(
    "platform,url",
    [
        ("GitHub", "https://example.com/octocat"),
        ("GitHub", "https://github.com/settings/profile"),
        ("LeetCode", "not a url"),
        ("Codeforces", ""),
    ],
)
def test_invalid_profile_urls(platform, url):
    with pytest.raises(InvalidProfileUrl):
        parse_profile_url(platform, url)


def test_profile_url_parsing_uses_first_matching_url_from_pasted_text():
    parsed = parse_profile_url(
        "CodeChef",
        "https://codechef.com/users/valve_angel_33http://codechef.com/users/valve_angel_33",
    )
    assert parsed.username == "valve_angel_33"
    assert parsed.url == "https://codechef.com/users/valve_angel_33"
