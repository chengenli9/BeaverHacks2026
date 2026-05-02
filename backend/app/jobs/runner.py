from app.jobs.store import mark_running, mark_succeeded, mark_failed


def run_job(job_id: str, fn, project_id: str, *args):
    try:
        mark_running(job_id, "Job started")

        fn(project_id, *args)

        mark_succeeded(job_id, "Job completed")

    except Exception as e:
        mark_failed(job_id, str(e))