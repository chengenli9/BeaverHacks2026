from pathlib import Path
import shutil
import subprocess

import pytest

from backend.app.manifests.models import BlockManifest
from backend.app.rendering.service import probe_render, render_project, write_concat_file


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


def test_render_project_creates_probeable_final_mp4(tmp_path):
    if shutil.which("ffmpeg") is None or shutil.which("ffprobe") is None:
        pytest.skip("ffmpeg and ffprobe are required for smoke render")

    font_source = Path("C:/Windows/Fonts/arial.ttf")
    if not font_source.is_file():
        pytest.skip("Windows Arial font is required to seed the project font fixture")

    project = tmp_path
    (project / "assets" / "backgrounds").mkdir(parents=True)
    (project / "assets" / "fonts").mkdir(parents=True)
    (project / "manifests").mkdir()
    (project / "blocks").mkdir()
    (project / "renders").mkdir()
    (project / "logs").mkdir()
    shutil.copyfile(font_source, project / "assets" / "fonts" / "Inter-Bold.ttf")

    subprocess.run(
        [
            "ffmpeg",
            "-y",
            "-f",
            "lavfi",
            "-i",
            "color=c=0x182026:s=320x180",
            "-frames:v",
            "1",
            str(project / "assets" / "backgrounds" / "bg_001.png"),
        ],
        check=True,
        capture_output=True,
        text=True,
    )
    shutil.copyfile(
        project / "assets" / "backgrounds" / "bg_001.png",
        project / "assets" / "backgrounds" / "bg_002.png",
    )

    manifest = BlockManifest.model_validate(
        {
            "project_id": "smoke_project",
            "version": 1,
            "render_settings": {
                "width": 320,
                "height": 180,
                "fps": 15,
                "video_codec": "libx264",
                "audio_codec": "aac",
                "sample_rate": 48000,
                "pixel_format": "yuv420p",
            },
            "blocks": [
                {
                    "block_id": "001_title",
                    "type": "title",
                    "background_asset": "assets/backgrounds/bg_001.png",
                    "text": "DirectorLoop",
                    "duration": 0.5,
                    "fontfile": "assets/fonts/Inter-Bold.ttf",
                    "rendered_path": "blocks/001_title.mp4",
                },
                {
                    "block_id": "002_end",
                    "type": "end_card",
                    "background_asset": "assets/backgrounds/bg_002.png",
                    "text": "Rendered",
                    "duration": 0.5,
                    "fontfile": "assets/fonts/Inter-Bold.ttf",
                    "rendered_path": "blocks/002_end.mp4",
                },
            ],
        }
    )
    (project / "manifests" / "block_manifest.json").write_text(
        manifest.model_dump_json(indent=2),
        encoding="utf-8",
    )

    final_render = render_project(project)
    probe = probe_render(final_render)

    assert final_render.is_file()
    assert float(probe["format"]["duration"]) > 0
