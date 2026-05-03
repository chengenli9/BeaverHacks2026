from ..integrations.gemini.service import (
    analyze_scenes,
    edit_plan_with_prompt,
    generate_background_assets,
    generate_plan,
    generate_tts_assets,
    precritique_manifest,
    review_render,
)
from ..manifests.service import (
    apply_approved_patches,
    build_manifest,
    delete_plan_beat,
    insert_plan_beat,
    reorder_plan_beats,
)
from ..rendering.service import render_project


def generate_tts(project_path):
    return generate_tts_assets(project_path)
