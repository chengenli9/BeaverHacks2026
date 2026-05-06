from ..integrations.gemini.service import (
    analyze_scenes,
    apply_proposed_plan,
    edit_plan_preview,
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
    update_plan_beat,
)
from ..rendering.service import render_project


def generate_tts(project_path):
    return generate_tts_assets(project_path)
