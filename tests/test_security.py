import pytest
from fastapi.testclient import TestClient
from pydantic import SecretStr

from app.main import create_app

PASSWORD = "synthetic-password-only-for-tests"


def secured(settings):
    settings.mad_auth_mode = "basic"
    settings.mad_auth_password = SecretStr(PASSWORD)
    return create_app(settings)


def test_secure_default_fails_closed(settings):
    settings.mad_auth_mode = "basic"
    settings.mad_auth_password = None
    with pytest.raises(ValueError, match="MAD_AUTH_PASSWORD"):
        with TestClient(create_app(settings)):
            pass


@pytest.mark.parametrize("path", ["/", "/static/app.js", "/docs", "/openapi.json", "/api/contents", "/api/usage", "/api/artifacts/00000000-0000-0000-0000-000000000000"])
def test_all_surfaces_require_auth(settings, path):
    with TestClient(secured(settings)) as client:
        response = client.get(path)
        assert response.status_code == 401
        assert "Basic" in response.headers["www-authenticate"]
        assert response.headers["cache-control"] == "no-store"


def test_auth_success_wrong_password_and_csrf(settings):
    with TestClient(secured(settings)) as client:
        assert client.get("/", auth=("editor", "wrong")).status_code == 401
        assert client.get("/", auth=("editor", PASSWORD)).status_code == 200
        assert client.post("/api/generate", auth=("editor", PASSWORD), json={}, headers={"Origin": "https://evil.example"}).status_code == 403
        assert client.post("/api/generate", auth=("editor", PASSWORD), content="{}", headers={"Content-Type": "text/plain"}).status_code == 415
        assert client.post("/api/generate", auth=("editor", PASSWORD), json={}).status_code == 201


def test_local_mode_cannot_be_spoofed_by_forwarded_header(settings):
    with TestClient(create_app(settings), client=("203.0.113.1", 1234)) as client:
        assert client.get("/", headers={"X-Forwarded-For": "127.0.0.1"}).status_code == 403


def test_rate_limits_survive_restart(settings):
    settings.mad_generate_per_minute = 1
    for expected in (201, 429):
        with TestClient(create_app(settings), client=("127.0.0.1", 1234)) as client:
            result = client.post("/api/generate", json={})
            assert result.status_code == expected
            if expected == 429:
                assert result.headers["retry-after"] == "60"


def test_export_download_requires_credentials(settings):
    with TestClient(secured(settings)) as client:
        credentials = ("editor", PASSWORD)
        content = client.post("/api/generate", json={}, auth=credentials).json()[0]
        artifact = client.post(f'/api/contents/{content["id"]}/exports', json={"kind": "carousel"}, auth=credentials).json()
        assert client.get(artifact["download_url"]).status_code == 401
        assert client.get(artifact["download_url"], auth=credentials).status_code == 200


def test_large_body_and_malformed_credentials(settings):
    with TestClient(secured(settings)) as client:
        assert client.get("/", headers={"Authorization": "Basic !!!"}).status_code == 401
        response = client.post("/api/generate", json={"topic": "a" * 40_000}, auth=("editor", PASSWORD))
        assert response.status_code == 413


def test_login_bruteforce_is_limited(settings):
    with TestClient(secured(settings)) as client:
        for _ in range(20):
            assert client.get("/", auth=("editor", "wrong")).status_code == 401
        assert client.get("/", auth=("editor", "wrong")).status_code == 429
        # A valid editor is not locked out by someone else's failed attempts.
        assert client.get("/", auth=("editor", PASSWORD)).status_code == 200
