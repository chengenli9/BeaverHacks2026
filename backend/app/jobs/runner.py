from app.jobs.store import update_job


def run_job(job_id: str, fn, *args, **kwargs):
    try:
        update_job(job_id, status="RUNNING", progress=0.05)

        result = fn(job_id, *args, **kwargs)

        update_job(
            job_id,
            status="SUCCESS",
            progress=1.0,
            result=result,
        )

    except Exception as e:
        update_job(
            job_id,
            status="FAILED",
            error=str(e),
        )
