from .codechef import CodeChefScraper
from .codeforces import CodeforcesScraper
from .gfg import GFGScraper
from .github import GitHubScraper
from .hackerrank import HackerRankScraper
from .leetcode import LeetCodeScraper
from .linkedin import LinkedInScraper

SCRAPER_CLASSES = {
    "CodeChef": CodeChefScraper,
    "LeetCode": LeetCodeScraper,
    "HackerRank": HackerRankScraper,
    "Codeforces": CodeforcesScraper,
    "GFG": GFGScraper,
    "LinkedIn": LinkedInScraper,
    "GitHub": GitHubScraper,
}

