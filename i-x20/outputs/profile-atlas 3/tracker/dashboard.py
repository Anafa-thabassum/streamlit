from __future__ import annotations

from typing import Any

from .database import Database
from .reporting import weekly_progress_rows


def dashboard_metrics(database: Database) -> dict[str, Any]:
    profiles = database.query("SELECT * FROM profiles WHERE active=1")
    latest = database.query("""
      WITH ranked AS (
        SELECT s.*, ROW_NUMBER() OVER(PARTITION BY profile_id ORDER BY fetched_at DESC, id DESC) rn
        FROM profile_snapshots s
      )
      SELECT p.platform, r.* FROM profiles p LEFT JOIN ranked r ON r.profile_id=p.id AND r.rn=1 WHERE p.active=1
    """)
    progress = weekly_progress_rows(database)
    successful = sum(1 for p in profiles if p["fetch_status"] == "Success")
    failed = sum(1 for p in profiles if p["fetch_status"] == "Failed")
    ratings: dict[str, list[float]] = {"LeetCode": [], "CodeChef": [], "Codeforces": []}
    for row in latest:
        if row["platform"] in ratings and row.get("rating") is not None:
            ratings[row["platform"]].append(float(row["rating"]))
    leetcode_problems = [row.get("problems_solved") for row in latest if row["platform"] == "LeetCode" and row.get("problems_solved") is not None]
    github_contributions = [row.get("contributions") for row in latest if row["platform"] == "GitHub" and row.get("contributions") is not None]
    weekly_commits = database.query("""
      SELECT COALESCE(SUM(CAST(json_extract(a.metadata_json, '$.commit_count') AS INTEGER)), 0) AS total
      FROM activities a JOIN profiles p ON p.id=a.profile_id
      WHERE p.platform='GitHub' AND a.activity_type='Push'
        AND datetime(a.activity_date) >= datetime('now', '-7 days')
    """)[0]["total"]
    return {
        "total_students": len({(p.get("student_register_no") or p["student_name"]).casefold() for p in profiles}),
        "total_profiles": len(profiles),
        "successful": successful,
        "failed": failed,
        "last_fetch": max((p["last_fetched"] for p in profiles if p["last_fetched"]), default=None),
        "total_problems": sum(row.get("problems_solved") or 0 for row in latest if row["platform"] in ratings),
        "problems_this_week": sum(row.get("Problems Added") or 0 for row in progress if (row.get("Problems Added") or 0) > 0),
        "average_leetcode_problems": (sum(leetcode_problems) / len(leetcode_problems)) if leetcode_problems else None,
        "average_ratings": {platform: (sum(values) / len(values) if values else None) for platform, values in ratings.items()},
        "contest_participation": sum(row.get("contests_attended") or 0 for row in latest),
        "github_repositories": sum(row.get("repositories") or 0 for row in latest if row["platform"] == "GitHub"),
        "github_followers": sum(row.get("followers") or 0 for row in latest if row["platform"] == "GitHub"),
        "github_contributions": sum(github_contributions) if github_contributions else None,
        "github_weekly_commits": weekly_commits,
    }
