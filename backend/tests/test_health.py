from unittest.mock import MagicMock, patch

from fastapi.testclient import TestClient
from sqlalchemy.exc import OperationalError

from app.main import app

client = TestClient(app)


def test_health_when_database_is_up() -> None:
    response = client.get("/api/health")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert body["services"] == {"database": "up"}


def test_health_when_database_is_down() -> None:
    with patch("app.routers.health.engine.connect") as mock_connect:
        mock_connect.side_effect = OperationalError("SELECT 1", {}, MagicMock())
        response = client.get("/api/health")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "degraded"
    assert body["services"] == {"database": "down"}
