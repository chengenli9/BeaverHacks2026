from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def test_health():
    assert client.get("/health").status_code == 200


def test_open_demo():
    res = client.post("/projects/open-demo")
    assert res.status_code == 200
    assert "project_id" in res.json()


def test_unknown_job():
    res = client.get("/jobs/does-not-exist")
    assert res.status_code == 404


def test_job_creation_returns_immediately():
    res = client.post("/jobs/analyze-scenes", params={"project_id": "demo_project"})
    assert res.status_code == 200
    assert "job_id" in res.json()