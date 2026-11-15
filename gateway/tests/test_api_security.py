"""API write protection, CORS and assistant limits. No database needed: every check here
must refuse the request before it reaches the database. Run from gateway/: python -m pytest tests"""
import importlib
import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "services"))


def load_api(monkeypatch, token="s3cret-token-0123456789", **env):
    monkeypatch.setenv("GOS_API_TOKEN", token)
    monkeypatch.setenv("DATABASE_URL", "postgresql://nobody@127.0.0.1:1/none")
    for k, v in env.items():
        monkeypatch.setenv(k, v)
    import api
    importlib.reload(api)
    return api.app.test_client()


WRITES = [("post", "/api/led", {"node": "ALL", "blue_pct": 100, "red_pct": 100}),
          ("delete", "/api/led/override", None),
          ("post", "/api/event", {"type": "PEST", "description": "x"}),
          ("post", "/api/yield", {"weight": 1}),
          ("post", "/api/assistant", {"text": "aphids", "commit": True})]


@pytest.mark.parametrize("method, path, body", WRITES)
def test_writes_need_the_token(monkeypatch, method, path, body):
    c = load_api(monkeypatch)
    r = getattr(c, method)(path, json=body)
    assert r.status_code == 401
    r = getattr(c, method)(path, json=body, headers={"Authorization": "Bearer wrong"})
    assert r.status_code == 401


def test_writes_are_off_without_a_configured_token(monkeypatch):
    c = load_api(monkeypatch, token="")
    r = c.post("/api/led", json={"blue_pct": 1, "red_pct": 1}, headers={"Authorization": "Bearer "})
    assert r.status_code == 503


def test_valid_token_passes_auth_and_input_is_checked(monkeypatch):
    c = load_api(monkeypatch)
    auth = {"Authorization": "Bearer s3cret-token-0123456789"}
    assert c.post("/api/led", json={"blue_pct": 150, "red_pct": 0}, headers=auth).status_code == 400
    assert c.post("/api/led", json={"blue_pct": 10, "red_pct": 0, "minutes": -1}, headers=auth).status_code == 400
    assert c.post("/api/led", json={"blue_pct": 10, "red_pct": 0, "minutes": 200000}, headers=auth).status_code == 400


def test_short_token_is_refused(monkeypatch):
    c = load_api(monkeypatch, token="short")
    r = c.post("/api/led", json={"blue_pct": 1, "red_pct": 1}, headers={"Authorization": "Bearer short"})
    assert r.status_code == 503


def test_no_cors_by_default_dashboard_uses_same_origin(monkeypatch):
    monkeypatch.delenv("GOS_CORS_ORIGINS", raising=False)
    c = load_api(monkeypatch)
    r = c.get("/health", headers={"Origin": "http://evil.example"})
    assert "Access-Control-Allow-Origin" not in r.headers


def test_cors_wildcard_allows_any_site_without_credentials(monkeypatch):
    c = load_api(monkeypatch, GOS_CORS_ORIGINS="*")
    r = c.get("/health", headers={"Origin": "http://other.example"})
    assert r.headers.get("Access-Control-Allow-Origin") in ("*", "http://other.example")
    assert "Access-Control-Allow-Credentials" not in r.headers
    # a page on that site still cannot change anything without the token
    assert c.post("/api/led", json={"blue_pct": 1, "red_pct": 1}, headers={"Origin": "http://other.example"}).status_code == 401


def test_reads_need_no_token(monkeypatch):
    c = load_api(monkeypatch)
    assert c.get("/health").status_code == 200


def test_cors_only_for_the_dashboard_origin(monkeypatch):
    c = load_api(monkeypatch, GOS_CORS_ORIGINS="http://pi.local:8080")
    ok = c.get("/health", headers={"Origin": "http://pi.local:8080"})
    assert ok.headers.get("Access-Control-Allow-Origin") == "http://pi.local:8080"
    evil = c.get("/health", headers={"Origin": "http://evil.example"})
    assert "Access-Control-Allow-Origin" not in evil.headers
    assert "Access-Control-Allow-Credentials" not in ok.headers


def test_assistant_length_cap_and_rate_limit(monkeypatch):
    monkeypatch.delenv("OLLAMA_URL", raising=False)
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    c = load_api(monkeypatch, ASSISTANT_RATE="3", ASSISTANT_MAX_CHARS="50")
    auth = {"Authorization": "Bearer s3cret-token-0123456789"}
    assert c.post("/api/assistant", json={"text": "x" * 51}, headers=auth).status_code == 413
    codes = [c.post("/api/assistant", json={"text": "aphids on row 2"}, headers=auth).status_code for _ in range(4)]
    assert codes == [200, 200, 200, 429]
