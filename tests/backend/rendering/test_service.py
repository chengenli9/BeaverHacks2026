from pathlib import Path

from backend.app.manifests.models import BlockManifest
from backend.app.rendering.service import write_concat_file


PROJECT_ROOT = Path(__file__).resolve().parents[3]
SAMPLE_PROJECT = PROJECT_ROOT / "samples" / "demo_project"


def test_write_concat_file_has_one_line_per_block(tmp_path):
    manifest = BlockManifest.from_file(SAMPLE_PROJECT / "manifests" / "block_manifest.json")

    concat_file = write_concat_file(tmp_path, manifest)
    lines = concat_file.read_text(encoding="utf-8").splitlines()

    assert lines == [
        "file 'blocks/001_title.mp4'",
        "file 'blocks/002_problem.mp4'",
        "file 'blocks/003_pipeline.mp4'",
        "file 'blocks/004_approval.mp4'",
        "file 'blocks/005_end.mp4'",
    ]

