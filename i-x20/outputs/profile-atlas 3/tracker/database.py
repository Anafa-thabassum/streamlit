from __future__ import annotations

import json
import sqlite3
import threading
from contextlib import contextmanager
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Iterable, Iterator

from .models import FetchError, ProfileResult, utc_now_iso


SCHEMA = """
PRAGMA journal_mode=WAL;
PRAGMA foreign_keys=ON;

CREATE TABLE IF NOT EXISTS profiles (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    student_register_no TEXT COLLATE NOCASE,
    student_name TEXT NOT NULL COLLATE NOCASE,
    platform TEXT NOT NULL,
    username TEXT NOT NULL COLLATE NOCASE,
    profile_url TEXT NOT NULL,
    active INTEGER NOT NULL DEFAULT 1 CHECK(active IN (0, 1)),
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    last_fetched TEXT,
    fetch_status TEXT NOT NULL DEFAULT 'Never fetched',
    last_error TEXT,
    UNIQUE(student_name, platform, username)
);

CREATE TABLE IF NOT EXISTS profile_snapshots (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    profile_id INTEGER NOT NULL REFERENCES profiles(id) ON DELETE CASCADE,
    fetched_at TEXT NOT NULL,
    rating REAL,
    max_rating REAL,
    rank TEXT,
    max_rank TEXT,
    global_rank INTEGER,
    country_rank INTEGER,
    problems_solved INTEGER,
    easy INTEGER,
    medium INTEGER,
    hard INTEGER,
    contest_rating REAL,
    contest_rank INTEGER,
    contests_attended INTEGER,
    total_submissions INTEGER,
    acceptance_rate REAL,
    reputation INTEGER,
    followers INTEGER,
    following_count INTEGER,
    repositories INTEGER,
    contributions INTEGER,
    stars_received INTEGER,
    forks INTEGER,
    name TEXT,
    bio TEXT,
    headline TEXT,
    connections INTEGER,
    coding_score INTEGER,
    hackos REAL,
    articles INTEGER,
    account_created TEXT,
    last_activity TEXT,
    stars TEXT,
    badges_json TEXT NOT NULL DEFAULT '[]',
    certificates_json TEXT NOT NULL DEFAULT '[]',
    raw_data_json TEXT NOT NULL DEFAULT '{}'
);

CREATE TABLE IF NOT EXISTS activities (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    profile_id INTEGER NOT NULL REFERENCES profiles(id) ON DELETE CASCADE,
    activity_id TEXT NOT NULL,
    activity_date TEXT,
    activity_type TEXT NOT NULL,
    title TEXT,
    difficulty TEXT,
    status TEXT,
    rating_change REAL,
    url TEXT,
    metadata_json TEXT NOT NULL DEFAULT '{}',
    first_seen_at TEXT NOT NULL,
    UNIQUE(profile_id, activity_id)
);

CREATE TABLE IF NOT EXISTS fetch_logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    profile_id INTEGER NOT NULL REFERENCES profiles(id) ON DELETE CASCADE,
    fetched_at TEXT NOT NULL,
    status TEXT NOT NULL,
    error_type TEXT,
    error_message TEXT
);

CREATE TABLE IF NOT EXISTS reports (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    created_at TEXT NOT NULL,
    path TEXT NOT NULL UNIQUE
);

CREATE TABLE IF NOT EXISTS import_errors (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    student_name TEXT NOT NULL,
    platform TEXT NOT NULL,
    profile_url TEXT,
    error_type TEXT NOT NULL,
    error_message TEXT NOT NULL,
    created_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_profiles_active ON profiles(active);
CREATE INDEX IF NOT EXISTS idx_profiles_last_fetched ON profiles(last_fetched);
CREATE INDEX IF NOT EXISTS idx_snapshots_profile_date ON profile_snapshots(profile_id, fetched_at DESC);
CREATE INDEX IF NOT EXISTS idx_activities_profile_date ON activities(profile_id, activity_date DESC);
CREATE INDEX IF NOT EXISTS idx_fetch_logs_date ON fetch_logs(fetched_at DESC);
"""


class Database:
    def __init__(self, path: Path | str):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._write_lock = threading.Lock()
        self.initialize()

    def connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.path, timeout=30)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys=ON")
        connection.execute("PRAGMA busy_timeout=30000")
        return connection

    @contextmanager
    def transaction(self) -> Iterator[sqlite3.Connection]:
        with self._write_lock, self.connect() as connection:
            try:
                yield connection
                connection.commit()
            except Exception:
                connection.rollback()
                raise

    def initialize(self) -> None:
        with self.connect() as connection:
            connection.executescript(SCHEMA)
            columns = {row["name"] for row in connection.execute("PRAGMA table_info(profiles)")}
            if "student_register_no" not in columns:
                connection.execute("ALTER TABLE profiles ADD COLUMN student_register_no TEXT COLLATE NOCASE")
            snapshot_columns = {row["name"] for row in connection.execute("PRAGMA table_info(profile_snapshots)")}
            if "hackos" not in snapshot_columns:
                connection.execute("ALTER TABLE profile_snapshots ADD COLUMN hackos REAL")
            connection.execute("""CREATE UNIQUE INDEX IF NOT EXISTS idx_profiles_register_platform_username
                ON profiles(student_register_no, platform, username)
                WHERE student_register_no IS NOT NULL AND student_register_no != ''""")

    def upsert_profile(
        self,
        student_name: str,
        platform: str,
        username: str,
        profile_url: str,
        student_register_no: str | None = None,
    ) -> tuple[int, bool]:
        now = utc_now_iso()
        register_no = (student_register_no or "").strip() or None
        with self.transaction() as connection:
            if register_no:
                row = connection.execute(
                    "SELECT id, profile_url, active FROM profiles WHERE student_register_no=? AND platform=? AND username=?",
                    (register_no, platform, username),
                ).fetchone()
                if not row:
                    row = connection.execute(
                        "SELECT id, profile_url, active FROM profiles WHERE student_name=? AND platform=? AND username=?",
                        (student_name.strip(), platform, username),
                    ).fetchone()
            else:
                row = connection.execute(
                    "SELECT id, profile_url, active FROM profiles WHERE student_name=? AND platform=? AND username=?",
                    (student_name.strip(), platform, username),
                ).fetchone()
            if row:
                connection.execute(
                    "UPDATE profiles SET student_register_no=?, student_name=?, profile_url=?, active=1, updated_at=? WHERE id=?",
                    (register_no, student_name.strip(), profile_url, now, row["id"]),
                )
                return int(row["id"]), False
            cursor = connection.execute(
                """INSERT INTO profiles
                   (student_register_no, student_name, platform, username, profile_url, created_at, updated_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?)""",
                (register_no, student_name.strip(), platform, username, profile_url, now, now),
            )
            return int(cursor.lastrowid), True

    def list_profiles(
        self,
        *,
        active_only: bool = False,
        platform: str | None = None,
        search: str | None = None,
        due_days: int | None = None,
        ids: Iterable[int] | None = None,
    ) -> list[dict[str, Any]]:
        clauses: list[str] = []
        params: list[Any] = []
        if active_only:
            clauses.append("active=1")
        if platform and platform != "All":
            clauses.append("platform=?")
            params.append(platform)
        if search:
            clauses.append("(student_register_no LIKE ? OR student_name LIKE ? OR username LIKE ? OR profile_url LIKE ?)")
            pattern = f"%{search.strip()}%"
            params.extend([pattern, pattern, pattern, pattern])
        if due_days is not None:
            cutoff = (datetime.now(timezone.utc) - timedelta(days=due_days)).replace(microsecond=0).isoformat()
            clauses.append("(fetch_status='Failed' OR last_fetched IS NULL OR last_fetched <= ?)")
            params.append(cutoff)
        if ids is not None:
            selected = [int(item) for item in ids]
            if not selected:
                return []
            clauses.append(f"id IN ({','.join('?' for _ in selected)})")
            params.extend(selected)
        where = " WHERE " + " AND ".join(clauses) if clauses else ""
        with self.connect() as connection:
            rows = connection.execute(
                f"SELECT * FROM profiles{where} ORDER BY student_name COLLATE NOCASE, platform",
                params,
            ).fetchall()
        return [dict(row) for row in rows]

    def update_profile_url(self, profile_id: int, username: str, profile_url: str) -> None:
        with self.transaction() as connection:
            connection.execute(
                "UPDATE profiles SET username=?, profile_url=?, updated_at=? WHERE id=?",
                (username, profile_url, utc_now_iso(), profile_id),
            )

    def update_student_details(
        self, profile_ids: Iterable[int], student_register_no: str | None, student_name: str
    ) -> None:
        selected = [int(profile_id) for profile_id in profile_ids]
        clean_name = student_name.strip()
        if not selected:
            raise ValueError("No student profiles were selected")
        if not clean_name:
            raise ValueError("Student name is required")
        register_no = (student_register_no or "").strip() or None
        placeholders = ",".join("?" for _ in selected)
        with self.transaction() as connection:
            connection.execute(
                f"UPDATE profiles SET student_register_no=?, student_name=?, updated_at=? WHERE id IN ({placeholders})",
                (register_no, clean_name, utc_now_iso(), *selected),
            )

    def set_profile_active(self, profile_id: int, active: bool) -> None:
        with self.transaction() as connection:
            connection.execute(
                "UPDATE profiles SET active=?, updated_at=? WHERE id=?",
                (1 if active else 0, utc_now_iso(), profile_id),
            )

    def save_success(self, profile_id: int, result: ProfileResult) -> None:
        metric_columns = [
            "rating", "max_rating", "rank", "max_rank", "global_rank", "country_rank",
            "problems_solved", "easy", "medium", "hard", "contest_rating", "contest_rank",
            "contests_attended", "total_submissions", "acceptance_rate", "reputation",
            "followers", "repositories", "contributions", "stars_received", "forks", "name",
            "bio", "headline", "connections", "coding_score", "hackos", "articles", "account_created",
            "last_activity", "stars",
        ]
        values = [getattr(result, column) for column in metric_columns]
        with self.transaction() as connection:
            placeholders = ",".join("?" for _ in range(1 + len(metric_columns) + 5))
            connection.execute(
                f"""INSERT INTO profile_snapshots
                (profile_id, {','.join(metric_columns)}, following_count, badges_json,
                 certificates_json, raw_data_json, fetched_at)
                VALUES ({placeholders})""",
                [profile_id, *values, result.following, json.dumps(result.badges),
                 json.dumps(result.certificates), json.dumps(result.raw_data, default=str), result.fetched_at],
            )
            for activity in result.activities:
                connection.execute(
                    """INSERT OR IGNORE INTO activities
                    (profile_id, activity_id, activity_date, activity_type, title, difficulty,
                     status, rating_change, url, metadata_json, first_seen_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                    (profile_id, activity.activity_id, activity.date, activity.activity_type,
                     activity.title, activity.difficulty, activity.status, activity.rating_change,
                     activity.url, json.dumps(activity.metadata, default=str), result.fetched_at),
                )
            connection.execute(
                "UPDATE profiles SET last_fetched=?, fetch_status='Success', last_error=NULL, updated_at=? WHERE id=?",
                (result.fetched_at, result.fetched_at, profile_id),
            )
            connection.execute(
                "INSERT INTO fetch_logs(profile_id, fetched_at, status) VALUES (?, ?, 'Success')",
                (profile_id, result.fetched_at),
            )

    def save_failure(self, profile_id: int, error: FetchError) -> None:
        now = utc_now_iso()
        with self.transaction() as connection:
            connection.execute(
                "UPDATE profiles SET last_fetched=?, fetch_status='Failed', last_error=?, updated_at=? WHERE id=?",
                (now, error.message, now, profile_id),
            )
            connection.execute(
                """INSERT INTO fetch_logs(profile_id, fetched_at, status, error_type, error_message)
                   VALUES (?, ?, 'Failed', ?, ?)""",
                (profile_id, now, error.error_type, error.message),
            )

    def query(self, sql: str, params: Iterable[Any] = ()) -> list[dict[str, Any]]:
        with self.connect() as connection:
            return [dict(row) for row in connection.execute(sql, tuple(params)).fetchall()]

    def record_report(self, path: Path) -> None:
        with self.transaction() as connection:
            connection.execute(
                "INSERT OR IGNORE INTO reports(created_at, path) VALUES (?, ?)",
                (utc_now_iso(), str(path)),
            )

    def save_import_errors(self, issues: Iterable[Any]) -> None:
        now = utc_now_iso()
        with self.transaction() as connection:
            connection.executemany(
                """INSERT INTO import_errors
                   (student_name, platform, profile_url, error_type, error_message, created_at)
                   VALUES (?, ?, ?, ?, ?, ?)""",
                [(item.name, item.platform, item.profile_url, item.error_type, item.error_message, now) for item in issues],
            )

    def latest_report(self) -> Path | None:
        rows = self.query("SELECT path FROM reports ORDER BY created_at DESC LIMIT 1")
        if not rows:
            return None
        path = Path(rows[0]["path"])
        return path if path.exists() else None
