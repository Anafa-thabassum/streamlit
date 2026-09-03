import requests
import responses
import pytest

from tracker.http_client import PublicHttpClient
from tracker.models import FetchException


@responses.activate
def test_rate_limit_is_retried(monkeypatch):
    monkeypatch.setattr("tracker.http_client.time.sleep", lambda *_: None)
    client = PublicHttpClient(1, "test")
    responses.add(responses.GET, "https://api.example.test/profile", status=429)
    responses.add(responses.GET, "https://api.example.test/profile", json={"ok": True}, status=200)
    response = client.request("GET", "https://api.example.test/profile", platform="GitHub", retries=1)
    assert response.json() == {"ok": True}
    assert len(responses.calls) == 2


@responses.activate
def test_timeout_becomes_structured_error(monkeypatch):
    monkeypatch.setattr("tracker.http_client.time.sleep", lambda *_: None)
    client = PublicHttpClient(0.01, "test")
    responses.add(responses.GET, "https://api.example.test/profile", body=requests.Timeout())
    with pytest.raises(FetchException) as error:
        client.request("GET", "https://api.example.test/profile", platform="GitHub", retries=0)
    assert error.value.error.error_type == "Timeout"


@responses.activate
def test_api_failure_becomes_structured_error(monkeypatch):
    monkeypatch.setattr("tracker.http_client.time.sleep", lambda *_: None)
    client = PublicHttpClient(1, "test")
    responses.add(responses.GET, "https://api.example.test/profile", status=503)
    with pytest.raises(FetchException) as error:
        client.request("GET", "https://api.example.test/profile", platform="GitHub", retries=0)
    assert error.value.error.error_type == "API unavailable"
