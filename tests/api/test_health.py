from fastapi.testclient import TestClient

from surveillance.api.main import app


def test_healthz() -> None:
    client = TestClient(app)
    response = client.get("/healthz")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_cors_trusts_localhost_only_in_development() -> None:
    from surveillance.api.main import cors_options
    from surveillance.settings import Settings

    dev = cors_options(Settings(environment="development", frontend_origins=["https://x.example"]))
    prod = cors_options(Settings(environment="production", frontend_origins=["https://x.example"]))

    assert dev["allow_origins"] == prod["allow_origins"] == ["https://x.example"]
    assert "allow_origin_regex" in dev
    assert "allow_origin_regex" not in prod
