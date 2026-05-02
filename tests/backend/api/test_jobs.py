from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def test_get_missing_job():
    res = client.get("/jobs/does-not-exist")
    assert res.status_code == 404
