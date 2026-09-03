from __future__ import annotations

from dataclasses import dataclass, field
from io import BytesIO
from pathlib import Path
from typing import BinaryIO

import pandas as pd

from .url_parser import PLATFORMS, InvalidProfileUrl, normalize_platform, parse_profile_url


@dataclass
class ImportIssue:
    name: str
    platform: str
    profile_url: str
    error_type: str
    error_message: str


@dataclass
class ImportResult:
    profiles: list[dict] = field(default_factory=list)
    issues: list[ImportIssue] = field(default_factory=list)
    detected_platforms: list[str] = field(default_factory=list)
    student_count: int = 0


def read_profiles_excel(source: str | Path | bytes | BinaryIO) -> ImportResult:
    if isinstance(source, (str, Path)):
        path = Path(source)
        if path.suffix.lower() != ".xlsx":
            raise ValueError("Only .xlsx files are supported")
        frame = pd.read_excel(path, dtype=str)
    else:
        if isinstance(source, bytes):
            source = BytesIO(source)
        frame = pd.read_excel(source, dtype=str, engine="openpyxl")
    frame.columns = [str(column).strip() for column in frame.columns]
    name_column = next((column for column in frame.columns if column.lower() == "name"), None)
    if not name_column:
        raise ValueError("The workbook must contain a 'Name' column")
    register_column = next(
        (column for column in frame.columns if column.lower().replace("_", " ").strip() in {"register no", "register number", "registration no", "student id"}),
        None,
    )
    if not register_column:
        raise ValueError("The workbook must contain a 'Register No' column")
    platform_columns = {
        column: normalize_platform(column)
        for column in frame.columns
        if normalize_platform(column) in PLATFORMS
    }
    result = ImportResult(
        detected_platforms=list(dict.fromkeys(platform_columns.values())),
        student_count=int(frame[name_column].dropna().astype(str).str.strip().ne("").sum()),
    )
    seen: set[tuple[str, str, str]] = set()
    for _, row in frame.iterrows():
        name = str(row.get(name_column, "")).strip()
        if not name or name.lower() == "nan":
            continue
        register_no = None
        if not pd.isna(row.get(register_column)):
            candidate = str(row.get(register_column)).strip()
            register_no = candidate if candidate and candidate.lower() != "nan" else None
        for column, platform in platform_columns.items():
            value = row.get(column)
            if pd.isna(value) or str(value).strip().lower() in {"", "n/a", "na", "none", "-"}:
                continue
            url = str(value).strip()
            try:
                parsed = parse_profile_url(platform, url)
            except InvalidProfileUrl as exc:
                result.issues.append(ImportIssue(name, platform, url, "Invalid URL", str(exc)))
                continue
            key = ((register_no or name).casefold(), parsed.platform, parsed.username.casefold())
            if key in seen:
                continue
            seen.add(key)
            result.profiles.append({
                "student_register_no": register_no,
                "student_name": name,
                "platform": parsed.platform,
                "username": parsed.username,
                "profile_url": parsed.url,
            })
    return result
