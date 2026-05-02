from ..integrations.gemini.service import (
    analyze_scenes,
    generate_background_assets,
    generate_plan,
    generate_tts_assets,
    precritique_manifest,
)
from ..manifests.service import apply_approved_patches, build_manifest
from ..rendering.service import render_project


def generate_tts(project_path):
    return generate_tts_assets(project_path)
