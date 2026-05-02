from app.jobs.store import create_job, get_job


def test_create_job():
    job = create_job("test", {})
    assert job["status"] == "PENDING"
    assert get_job(job["job_id"]) is not None
