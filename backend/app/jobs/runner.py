from inspect import signature

from .store import mark_running, mark_succeeded, mark_failed, update_progress
from ..projects.service import get_project_path


def run_job(job_id: str, fn, project_id: str, *args):
    try:
        mark_running(job_id, "Job started")

        project_path = get_project_path(project_id)

        if "progress_callback" in signature(fn).parameters:
            fn(project_path, *args, progress_callback=_progress_callback(job_id))
        else:
            fn(project_path, *args)

        mark_succeeded(job_id, "Job completed")

    except Exception as e:
        mark_failed(job_id, str(e))


def _progress_callback(job_id: str):
    def callback(progress: float, message: str):
        update_progress(job_id, progress, message)

    return callback
