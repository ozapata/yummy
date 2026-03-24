from pathlib import Path

import pytest

from exchange_app import create_app


class DummyResponse:
    def __init__(self, payload):
        self.payload = payload

    def raise_for_status(self):
        return None

    def json(self):
        return self.payload


class DummySession:
    def __init__(self):
        self.calls = []

    def get(self, url, params=None, timeout=10):
        self.calls.append((url, params, timeout))
        if "latest" in url:
            return DummyResponse(
                {
                    "date": "2026-03-23",
                    "rates": {
                        "MXN": 16.8123,
                        "CAD": 1.3542,
                    },
                }
            )
        return DummyResponse(
            {
                "rates": {
                    "2026-03-21": {"MXN": 16.7000, "CAD": 1.3500},
                    "2026-03-22": {"MXN": 16.7600, "CAD": 1.3520},
                    "2026-03-23": {"MXN": 16.8123, "CAD": 1.3542},
                }
            }
        )


@pytest.fixture
def app(tmp_path: Path):
    database_path = tmp_path / "test.sqlite"
    session = DummySession()
    app = create_app(
        {
            "TESTING": True,
            "DATABASE": database_path,
            "HTTP_SESSION": session,
            "HISTORY_DAYS": 3,
        }
    )
    app.dummy_session = session
    return app


@pytest.fixture
def client(app):
    return app.test_client()


def test_index_renders_seeded_history(client):
    response = client.get("/")
    html = response.get_data(as_text=True)

    assert response.status_code == 200
    assert "Track USD against MXN and CAD" in html
    assert "16.8123" in html


def test_refresh_endpoint_updates_latest_rates(client, app):
    response = client.post("/api/refresh")
    payload = response.get_json()

    assert response.status_code == 200
    assert payload["latest"]["usd_to_mxn"] == pytest.approx(16.8123)
    assert payload["latest"]["usd_to_cad"] == pytest.approx(1.3542)
    assert any("latest" in call[0] for call in app.dummy_session.calls)
