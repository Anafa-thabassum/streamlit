from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parent.parent
load_dotenv(PROJECT_ROOT / ".env")


def _path_from_env(name: str, default: str) -> Path:
    value = Path(os.getenv(name, default)).expanduser()
    return value if value.is_absolute() else PROJECT_ROOT / value


@dataclass(frozen=True)
class Settings:
    database_path: Path = _path_from_env("DATABASE_PATH", "data/profiles.db")
    reports_dir: Path = _path_from_env("REPORTS_DIR", "reports")
    fetch_interval_days: int = int(os.getenv("FETCH_INTERVAL_DAYS", "7"))
    request_timeout_seconds: float = float(os.getenv("REQUEST_TIMEOUT_SECONDS", "15"))
    max_workers: int = max(1, min(12, int(os.getenv("MAX_WORKERS", "6"))))
    github_token: str | None = os.getenv("GITHUB_TOKEN") or None
    user_agent: str = os.getenv(
        "USER_AGENT", "ProfileTracker/1.0 (public-profile analytics)"
    )

    def ensure_directories(self) -> None:
        self.database_path.parent.mkdir(parents=True, exist_ok=True)
        self.reports_dir.mkdir(parents=True, exist_ok=True)
        (PROJECT_ROOT / "logs").mkdir(parents=True, exist_ok=True)


settings = Settings()

