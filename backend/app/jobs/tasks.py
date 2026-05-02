from app.jobs.store import update_job


def scene_index_task(job_id: str, project_id: str):
    update_job(job_id, progress=0.2)
    # TODO: call Gemini analyzer
    update_job(job_id, progress=0.8)
    return {"scene_index": "ok"}


def plan_task(job_id: str, project_id: str):
    update_job(job_id, progress=0.3)
    return {"plan": "ok"}


def asset_task(job_id: str, project_id: str):
    update_job(job_id, progress=0.3)
    return {"assets": "ok"}


def block_manifest_task(job_id: str, project_id: str):
    update_job(job_id, progress=0.5)
    return {"manifest": "ok"}


def render_blocks_task(job_id: str, project_id: str):
    update_job(job_id, progress=0.5)
    return {"blocks_rendered": True}


def render_final_task(job_id: str, project_id: str):
    update_job(job_id, progress=0.7)
    return {"final_render": "ok"}


def critique_task(job_id: str, project_id: str):
    update_job(job_id, progress=0.6)
    return {"patches": []}


def apply_patches_task(job_id: str, project_id: str):
    update_job(job_id, progress=0.6)
    return {"applied": True}
