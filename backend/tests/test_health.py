"""
tests/test_health.py
--------------------
Tests for the /api/health endpoint.
"""


def test_health_returns_200(client):
    resp = client.get("/api/health")
    assert resp.status_code == 200


def test_health_body(client):
    resp = client.get("/api/health")
    data = resp.get_json()
    assert data["status"] == "ok"
    assert "timestamp" in data
