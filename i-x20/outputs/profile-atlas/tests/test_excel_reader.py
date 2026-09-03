from io import BytesIO

import pandas as pd
import pytest

from tracker.excel_reader import read_profiles_excel


def workbook_bytes(frame: pd.DataFrame) -> bytes:
    output = BytesIO()
    frame.to_excel(output, index=False, engine="openpyxl")
    return output.getvalue()


def test_reads_missing_urls_and_deduplicates():
    data = workbook_bytes(pd.DataFrame([
        {"Register No": "R001", "Name": "Ana", "GitHub": "https://github.com/octocat", "LeetCode": None},
        {"Register No": "R001", "Name": "Ana", "GitHub": "https://github.com/octocat", "LeetCode": "N/A"},
    ]))
    result = read_profiles_excel(data)
    assert result.student_count == 2
    assert len(result.profiles) == 1
    assert result.profiles[0]["username"] == "octocat"
    assert result.issues == []


def test_invalid_url_is_an_issue_not_a_crash():
    data = workbook_bytes(pd.DataFrame([{"Register No": "R001", "Name": "Ana", "GitHub": "https://example.com/nope"}]))
    result = read_profiles_excel(data)
    assert result.profiles == []
    assert result.issues[0].error_type == "Invalid URL"


def test_name_column_is_required():
    data = workbook_bytes(pd.DataFrame([{"Register No": "R001", "Student": "Ana", "GitHub": "https://github.com/octocat"}]))
    with pytest.raises(ValueError, match="Name"):
        read_profiles_excel(data)


def test_register_number_column_is_required():
    data = workbook_bytes(pd.DataFrame([{"Name": "Ana", "GitHub": "https://github.com/octocat"}]))
    with pytest.raises(ValueError, match="Register No"):
        read_profiles_excel(data)
