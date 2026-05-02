from pathlib import Path
import shutil
import subprocess

import pytest

from backend.app.manifests.models import BlockManifest
from backend.app.rendering.service import (
    probe_render,
    render_project,
    source_has_audio_stream,
    summarize_render,
    write_concat_file,
)


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


def test_write_concat_file_rejects_unsafe_rendered_paths(tmp_path):
    manifest = BlockManifest.model_validate(
        {
            "project_id": "bad_paths",
            "version": 1,
            "render_settings": {},
            "blocks": [
                {
                    "block_id": "001_bad",
                    "type": "title",
                    "background_asset": "assets/backgrounds/bg_001.png",
                    "text": "Bad",
                    "duration": 1.0,
                    "fontfile": "assets/fonts/Inter-Bold.ttf",
                    "rendered_path": "blocks/bad'name.mp4",
                }
            ],
        }
    )

    with pytest.raises(ValueError, match="Unsafe concat path"):
        write_concat_file(tmp_path, manifest)


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
    assert probe["duration"] > 0
    assert probe["size_bytes"] > 0
    assert probe["has_video"] is True
    assert probe["has_audio"] is True
    assert summarize_render("demo_project", final_render)["render_path"].endswith("final_render.mp4")


def test_source_clip_without_audio_stream_still_renders_with_audio_output(tmp_path):
    if shutil.which("ffmpeg") is None or shutil.which("ffprobe") is None:
        pytest.skip("ffmpeg and ffprobe are required for smoke render")

    project = tmp_path
    (project / "source").mkdir()
    (project / "manifests").mkdir()
    (project / "blocks").mkdir()
    (project / "renders").mkdir()
    (project / "logs").mkdir()

    subprocess.run(
        [
            "ffmpeg",
            "-y",
            "-f",
            "lavfi",
            "-i",
            "testsrc=size=320x180:rate=15",
            "-t",
            "0.6",
            "-an",
            "-c:v",
            "libx264",
            "-pix_fmt",
            "yuv420p",
            str(project / "source" / "silent_source.mp4"),
        ],
        check=True,
        capture_output=True,
        text=True,
    )

    manifest = BlockManifest.model_validate(
        {
            "project_id": "silent_source_project",
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
                    "block_id": "001_clip",
                    "type": "source_clip",
                    "source": "source/silent_source.mp4",
                    "source_start": 0.0,
                    "source_end": 0.5,
                    "video_duration": 0.5,
                    "tts_asset": None,
                    "tts_duration": None,
                    "source_audio_volume": 0.15,
                    "tts_fade_seconds": 0.5,
                    "rendered_path": "blocks/001_clip.mp4",
                }
            ],
        }
    )
    (project / "manifests" / "block_manifest.json").write_text(
        manifest.model_dump_json(indent=2),
        encoding="utf-8",
    )

    assert source_has_audio_stream(project / "source" / "silent_source.mp4") is False

    final_render = render_project(project)
    probe = probe_render(final_render)

    assert final_render.is_file()
    assert probe["duration"] > 0
    assert probe["has_video"] is True
    assert probe["has_audio"] is True


def test_probe_render_rejects_video_without_audio(tmp_path):
    if shutil.which("ffmpeg") is None or shutil.which("ffprobe") is None:
        pytest.skip("ffmpeg and ffprobe are required for probe validation")

    video_only = tmp_path / "video_only.mp4"
    subprocess.run(
        [
            "ffmpeg",
            "-y",
            "-f",
            "lavfi",
            "-i",
            "testsrc=size=320x180:rate=15",
            "-t",
            "0.5",
            "-an",
            "-c:v",
            "libx264",
            "-pix_fmt",
            "yuv420p",
            str(video_only),
        ],
        check=True,
        capture_output=True,
        text=True,
    )

    with pytest.raises(RuntimeError, match="audio stream"):
        probe_render(video_only)


def test_render_project_reports_progress_per_block(tmp_path, monkeypatch):
    manifest = BlockManifest.model_validate(
        {
            "project_id": "progress_project",
            "version": 1,
            "render_settings": {},
            "blocks": [
                {
                    "block_id": "001_title",
                    "type": "title",
                    "background_asset": "assets/backgrounds/bg_001.png",
                    "text": "One",
                    "duration": 1.0,
                    "fontfile": "assets/fonts/Inter-Bold.ttf",
                    "rendered_path": "blocks/001_title.mp4",
                },
                {
                    "block_id": "002_end",
                    "type": "end_card",
                    "background_asset": "assets/backgrounds/bg_002.png",
                    "text": "Two",
                    "duration": 1.0,
                    "fontfile": "assets/fonts/Inter-Bold.ttf",
                    "rendered_path": "blocks/002_end.mp4",
                },
            ],
        }
    )
    (tmp_path / "manifests").mkdir()
    (tmp_path / "renders").mkdir()
    (tmp_path / "manifests" / "block_manifest.json").write_text(
        manifest.model_dump_json(indent=2),
        encoding="utf-8",
    )

    import backend.app.rendering.service as service

    monkeypatch.setattr(service, "check_ffmpeg_available", lambda: None)
    monkeypatch.setattr(service, "validate_project_assets", lambda root, manifest: None)
    monkeypatch.setattr(service, "render_block", lambda root, block, settings: tmp_path / block.rendered_path)
    monkeypatch.setattr(service, "_run", lambda command, log_path: None)
    monkeypatch.setattr(
        service,
        "probe_render",
        lambda path: {"duration": 2.0, "size_bytes": 100, "has_video": True, "has_audio": True, "streams": []},
    )
    progress = []

    final_render = render_project(tmp_path, progress_callback=lambda value, message: progress.append((value, message)))

    assert final_render == tmp_path / "renders" / "final_render.mp4"
    assert progress == [
        (0.0, "Rendering block 1 of 2"),
        (0.5, "Rendering block 2 of 2"),
        (1.0, "Render complete"),
    ]


def test_render_project_wraps_block_failures_with_block_id(tmp_path, monkeypatch):
    manifest = BlockManifest.model_validate(
        {
            "project_id": "failure_project",
            "version": 1,
            "render_settings": {},
            "blocks": [
                {
                    "block_id": "001_title",
                    "type": "title",
                    "background_asset": "assets/backgrounds/bg_001.png",
                    "text": "One",
                    "duration": 1.0,
                    "fontfile": "assets/fonts/Inter-Bold.ttf",
                    "rendered_path": "blocks/001_title.mp4",
                }
            ],
        }
    )
    (tmp_path / "manifests").mkdir()
    (tmp_path / "manifests" / "block_manifest.json").write_text(
        manifest.model_dump_json(indent=2),
        encoding="utf-8",
    )

    import backend.app.rendering.service as service

    def fail_render_block(root, block, settings):
        raise RuntimeError("simulated ffmpeg failure")

    monkeypatch.setattr(service, "check_ffmpeg_available", lambda: None)
    monkeypatch.setattr(service, "validate_project_assets", lambda root, manifest: None)
    monkeypatch.setattr(service, "render_block", fail_render_block)

    with pytest.raises(RuntimeError, match="001_title"):
        render_project(tmp_path)
