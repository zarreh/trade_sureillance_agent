from fastapi.testclient import TestClient

from surveillance.api.main import app


def test_skeleton_events_stream_reaches_done() -> None:
    client = TestClient(app)
    with client.stream("GET", "/investigations/skeleton/events?message=hi") as response:
        assert response.status_code == 200
        body = "".join(response.iter_text())
    assert '"echo: hi"' in body
    assert '"__end__"' in body
