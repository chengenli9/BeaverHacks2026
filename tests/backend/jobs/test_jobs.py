from app.jobs.store import create_job, mark_running, mark_succeeded, mark_failed, get_job


def test_job_lifecycle():
    job = create_job("demo", "test", "start")

    mark_running(job["job_id"], "running")
    assert get_job(job["job_id"])["status"] == "running"

    mark_succeeded(job["job_id"], "done")
    assert get_job(job["job_id"])["status"] == "succeeded"


def test_job_failure():
    job = create_job("demo", "test", "start")
    mark_failed(job["job_id"], "error")
    assert get_job(job["job_id"])["status"] == "failed"
