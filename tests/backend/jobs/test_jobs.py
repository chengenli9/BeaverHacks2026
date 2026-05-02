from app.jobs.runner import run_job
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


def test_runner_wires_optional_progress_callback():
    job = create_job("demo", "rendering", "queued")

    def task(project_path, progress_callback=None):
        assert project_path.name == "demo_project"
        assert progress_callback is not None
        progress_callback(0.5, "Halfway")

    run_job(job["job_id"], task, "demo_project")

    saved = get_job(job["job_id"])
    assert saved["status"] == "succeeded"
    assert saved["progress"] == 1.0
    assert saved["message"] == "Job completed"
