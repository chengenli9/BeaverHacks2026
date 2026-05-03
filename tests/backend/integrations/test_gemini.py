"""Tests for the Gemini client and service layer.

These tests are unit/offline tests — they mock the google.genai client so no
live API calls are made.  Live integration tests require GEMINI_API_KEY and
should be skipped in default CI per the model policy.
"""

import io
import json
import wave
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_wav_bytes(duration_s: float = 2.0, sample_rate: int = 24000) -> bytes:
    """Return minimal valid WAV bytes for testing."""
    frames = int(duration_s * sample_rate)
    pcm = b"\x00\x00" * frames  # 16-bit silence
    buf = io.BytesIO()
    with wave.open(buf, "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(sample_rate)
        wf.writeframes(pcm)
    return buf.getvalue()


def _make_mock_text_response(payload: dict) -> MagicMock:
    resp = MagicMock()
    resp.text = json.dumps(payload)
    resp.usage_metadata.prompt_token_count = 10
    resp.usage_metadata.candidates_token_count = 20
    return resp


def _make_mock_audio_response(pcm_bytes: bytes) -> MagicMock:
    part = MagicMock()
    part.inline_data.data = pcm_bytes
    part.inline_data.mime_type = "audio/pcm"
    candidate = MagicMock()
    candidate.content.parts = [part]
    resp = MagicMock()
    resp.candidates = [candidate]
    resp.usage_metadata.prompt_token_count = 5
    resp.usage_metadata.candidates_token_count = 0
    return resp


def _make_mock_image_response(png_bytes: bytes) -> MagicMock:
    part = MagicMock()
    part.inline_data.data = png_bytes
    part.inline_data.mime_type = "image/png"
    candidate = MagicMock()
    candidate.content.parts = [part]
    resp = MagicMock()
    resp.candidates = [candidate]
    resp.usage_metadata.prompt_token_count = 5
    resp.usage_metadata.candidates_token_count = 0
    return resp


# ---------------------------------------------------------------------------
# Settings tests
# ---------------------------------------------------------------------------

class TestSettings:
    def test_default_text_model_is_flash_lite(self):
        from backend.app.integrations.gemini.settings import GEMINI_TEXT_MODEL
        assert "flash" in GEMINI_TEXT_MODEL.lower()
        assert "lite" in GEMINI_TEXT_MODEL.lower()

    def test_default_tts_model_is_flash_tts(self):
        from backend.app.integrations.gemini.settings import GEMINI_TTS_MODEL
        assert "flash" in GEMINI_TTS_MODEL.lower()
        assert "tts" in GEMINI_TTS_MODEL.lower()

    def test_default_image_model_is_flash_image(self):
        from backend.app.integrations.gemini.settings import GEMINI_IMAGE_MODEL
        assert "flash" in GEMINI_IMAGE_MODEL.lower()
        assert "image" in GEMINI_IMAGE_MODEL.lower()

    def test_grounding_disabled_by_default(self):
        from backend.app.integrations.gemini.settings import GEMINI_ENABLE_GROUNDING
        assert GEMINI_ENABLE_GROUNDING is False

    def test_pro_model_rejected(self):
        from backend.app.integrations.gemini.settings import assert_not_pro
        with pytest.raises(ValueError, match="Pro model"):
            assert_not_pro("gemini-2.5-pro")

    def test_pro_model_with_prefix_rejected(self):
        from backend.app.integrations.gemini.settings import assert_not_pro
        with pytest.raises(ValueError):
            assert_not_pro("gemini-1.5-pro-latest")

    def test_flash_model_allowed(self):
        from backend.app.integrations.gemini.settings import assert_not_pro
        # Should not raise
        assert_not_pro("gemini-2.5-flash-lite")
        assert_not_pro("gemini-2.5-flash-preview-tts")
        assert_not_pro("gemini-2.5-flash-image")


# ---------------------------------------------------------------------------
# client.py — complete_json
# ---------------------------------------------------------------------------

class TestCompleteJson:
    @patch("backend.app.integrations.gemini.client.get_client")
    def test_returns_parsed_dict(self, mock_get_client):
        payload = {"foo": "bar", "count": 42}
        mock_client = MagicMock()
        mock_client.models.generate_content.return_value = _make_mock_text_response(payload)
        mock_get_client.return_value = mock_client

        from backend.app.integrations.gemini.client import complete_json
        result, usage = complete_json("test prompt")

        assert result == payload

    @patch("backend.app.integrations.gemini.client.get_client")
    def test_usage_fields_present(self, mock_get_client):
        mock_client = MagicMock()
        mock_client.models.generate_content.return_value = _make_mock_text_response({"x": 1})
        mock_get_client.return_value = mock_client

        from backend.app.integrations.gemini.client import complete_json
        _, usage = complete_json("test prompt")

        assert "elapsed_ms" in usage
        assert "model" in usage
        assert "input_token_count" in usage
        assert "output_token_count" in usage

    @patch("backend.app.integrations.gemini.client.get_client")
    def test_invalid_json_raises(self, mock_get_client):
        mock_client = MagicMock()
        resp = MagicMock()
        resp.text = "not valid json %%"
        resp.usage_metadata = None
        mock_client.models.generate_content.return_value = resp
        mock_get_client.return_value = mock_client

        from backend.app.integrations.gemini.client import complete_json
        with pytest.raises(Exception):
            complete_json("bad prompt")

    def test_pro_model_rejected(self):
        from backend.app.integrations.gemini.client import complete_json
        with pytest.raises(ValueError, match="Pro model"):
            complete_json("test", model="gemini-2.5-pro")

    @patch("backend.app.integrations.gemini.client.get_client")
    def test_passes_response_json_schema_when_provided(self, mock_get_client):
        payload = {"foo": "bar"}
        mock_client = MagicMock()
        mock_client.models.generate_content.return_value = _make_mock_text_response(payload)
        mock_get_client.return_value = mock_client

        from backend.app.integrations.gemini.client import complete_json

        schema = {
            "type": "object",
            "properties": {"foo": {"type": "string"}},
            "required": ["foo"],
        }
        complete_json("test prompt", schema=schema)

        config = mock_client.models.generate_content.call_args.kwargs["config"]
        assert getattr(config, "response_json_schema", None) == schema


# ---------------------------------------------------------------------------
# client.py — generate_audio / WAV helpers
# ---------------------------------------------------------------------------

class TestGenerateAudio:
    @patch("backend.app.integrations.gemini.client.get_client")
    def test_returns_valid_wav_bytes(self, mock_get_client):
        pcm = b"\x00\x00" * (24000 * 2)  # 2 s of silence
        mock_client = MagicMock()
        mock_client.models.generate_content.return_value = _make_mock_audio_response(pcm)
        mock_get_client.return_value = mock_client

        from backend.app.integrations.gemini.client import generate_audio
        wav_bytes, usage = generate_audio("hello world")

        # Verify it parses as WAV
        buf = io.BytesIO(wav_bytes)
        with wave.open(buf, "rb") as wf:
            assert wf.getnchannels() == 1
            assert wf.getframerate() == 24000

    def test_pcm_to_wav_round_trip(self):
        from backend.app.integrations.gemini.client import _pcm_to_wav
        pcm = b"\x01\x02" * 100
        wav = _pcm_to_wav(pcm, sample_rate=24000, channels=1, sample_width=2)
        buf = io.BytesIO(wav)
        with wave.open(buf, "rb") as wf:
            assert wf.getnframes() == 100

    def test_measure_wav_duration(self, tmp_path):
        wav_path = tmp_path / "test.wav"
        wav_path.write_bytes(_make_wav_bytes(duration_s=3.0))

        from backend.app.integrations.gemini.client import measure_wav_duration
        dur = measure_wav_duration(wav_path)
        assert abs(dur - 3.0) < 0.01


# ---------------------------------------------------------------------------
# client.py — generate_image fallback
# ---------------------------------------------------------------------------

class TestGenerateImage:
    @patch("backend.app.integrations.gemini.client.get_client")
    def test_fallback_returns_png_on_error(self, mock_get_client):
        mock_client = MagicMock()
        mock_client.models.generate_content.side_effect = RuntimeError("API error")
        mock_get_client.return_value = mock_client

        from backend.app.integrations.gemini.client import generate_image
        png_bytes, usage = generate_image("abstract background")

        assert png_bytes[:4] == b"\x89PNG" or len(png_bytes) > 0
        assert usage.get("error") == "image_generation_fallback"

    def test_placeholder_png_is_valid(self):
        from backend.app.integrations.gemini.client import _placeholder_png
        from PIL import Image
        png = _placeholder_png(width=64, height=64)
        img = Image.open(io.BytesIO(png))
        assert img.size == (64, 64)


# ---------------------------------------------------------------------------
# service.py — analyze_scenes
# ---------------------------------------------------------------------------

class TestAnalyzeScenes:
    def test_merges_multiple_source_files_into_virtual_timeline(self, tmp_path, monkeypatch):
        from backend.app.integrations.gemini import service
        from backend.app.media.models import MediaProbe, ShotIndex

        (tmp_path / "source").mkdir()
        (tmp_path / "cache").mkdir()
        (tmp_path / "logs").mkdir()
        first = tmp_path / "source" / "a.mp4"
        second = tmp_path / "source" / "b.mp4"
        first.write_bytes(b"a")
        second.write_bytes(b"b")

        monkeypatch.setattr(service, "find_source_videos", lambda project_path: [first, second])
        monkeypatch.setattr(
            service,
            "inspect_source_media",
            lambda project_path: MediaProbe.model_validate(
                {
                    "project_id": "demo",
                    "total_duration_seconds": 10.0,
                    "sources": [
                        {
                            "path": "source/a.mp4",
                            "duration_seconds": 4.0,
                            "has_audio": False,
                            "video_stream": {"codec": "h264", "width": 1920, "height": 1080, "fps": 30.0},
                            "audio_stream": None,
                            "start_offset_seconds": 0.0,
                            "end_offset_seconds": 4.0,
                        },
                        {
                            "path": "source/b.mp4",
                            "duration_seconds": 6.0,
                            "has_audio": False,
                            "video_stream": {"codec": "h264", "width": 1920, "height": 1080, "fps": 30.0},
                            "audio_stream": None,
                            "start_offset_seconds": 4.0,
                            "end_offset_seconds": 10.0,
                        },
                    ],
                }
            ),
        )
        monkeypatch.setattr(
            service,
            "detect_shots",
            lambda project_path, media_probe: ShotIndex.model_validate(
                {
                    "project_id": "demo",
                    "total_duration_seconds": 10.0,
                    "sources": [
                        {
                            "path": "source/a.mp4",
                            "duration_seconds": 4.0,
                            "start_offset_seconds": 0.0,
                            "end_offset_seconds": 4.0,
                        },
                        {
                            "path": "source/b.mp4",
                            "duration_seconds": 6.0,
                            "start_offset_seconds": 4.0,
                            "end_offset_seconds": 10.0,
                        },
                    ],
                    "shots": [],
                }
            ),
        )

        responses = iter(
            [
                (
                    {
                        "project_id": "demo",
                        "total_duration_seconds": 4.0,
                        "sources": [
                            {
                                "path": "source/a.mp4",
                                "duration_seconds": 4.0,
                                "start_offset_seconds": 0.0,
                                "end_offset_seconds": 4.0,
                            }
                        ],
                        "scenes": [
                            {
                                "scene_id": "scene_local_001",
                                "source": "source/a.mp4",
                                "start": 0.0,
                                "end": 4.0,
                                "summary": "First clip",
                                "visual_tags": [],
                                "audio_notes": "",
                                "demo_relevance": 0.7,
                            }
                        ],
                    },
                    {"model": "test", "elapsed_ms": 1, "input_token_count": 1, "output_token_count": 1},
                ),
                (
                    {
                        "project_id": "demo",
                        "total_duration_seconds": 6.0,
                        "sources": [
                            {
                                "path": "source/b.mp4",
                                "duration_seconds": 6.0,
                                "start_offset_seconds": 0.0,
                                "end_offset_seconds": 6.0,
                            }
                        ],
                        "scenes": [
                            {
                                "scene_id": "scene_local_001",
                                "source": "source/b.mp4",
                                "start": 0.0,
                                "end": 6.0,
                                "summary": "Second clip",
                                "visual_tags": [],
                                "audio_notes": "",
                                "demo_relevance": 0.8,
                            }
                        ],
                    },
                    {"model": "test", "elapsed_ms": 1, "input_token_count": 1, "output_token_count": 1},
                ),
            ]
        )
        monkeypatch.setattr(service._client, "complete_json_with_file", lambda *args, **kwargs: next(responses))

        result = service.analyze_scenes(tmp_path)

        assert result["total_duration_seconds"] == 10.0
        assert len(result["sources"]) == 2
        assert [scene["source"] for scene in result["scenes"]] == ["source/a.mp4", "source/b.mp4"]
        assert result["scenes"][1]["start"] == pytest.approx(4.0)
        assert result["scenes"][1]["end"] == pytest.approx(10.0)

    @patch("backend.app.integrations.gemini.client.get_client")
    def test_writes_scene_index_json(self, mock_get_client, tmp_path):
        scene_index = {
            "project_id": "test_project",
            "source": "source/demo.mp4",
            "source_duration": 30.0,
            "scenes": [
                {
                    "scene_id": "scene_001",
                    "start": 0.0,
                    "end": 10.0,
                    "summary": "Intro.",
                    "visual_tags": ["intro"],
                    "audio_notes": "Clear",
                    "demo_relevance": 0.9,
                }
            ],
        }
        mock_client = MagicMock()
        mock_client.models.generate_content.return_value = _make_mock_text_response(scene_index)
        mock_get_client.return_value = mock_client

        # Set up project dir
        (tmp_path / "source").mkdir()
        (tmp_path / "cache").mkdir()
        (tmp_path / "logs").mkdir()

        from backend.app.integrations.gemini.service import analyze_scenes
        result = analyze_scenes(tmp_path)

        assert (tmp_path / "cache" / "scene_index.json").exists()
        assert "scenes" in result

    @patch("backend.app.integrations.gemini.client.get_client")
    def test_scene_response_parses_as_json(self, mock_get_client, tmp_path):
        payload = {
            "project_id": "demo",
            "source": "source/v.mp4",
            "source_duration": 10.0,
            "scenes": [],
        }
        mock_client = MagicMock()
        mock_client.models.generate_content.return_value = _make_mock_text_response(payload)
        mock_get_client.return_value = mock_client

        (tmp_path / "source").mkdir()
        (tmp_path / "cache").mkdir()
        (tmp_path / "logs").mkdir()

        from backend.app.integrations.gemini.service import analyze_scenes
        result = analyze_scenes(tmp_path)
        # Confirm the result is a proper dict (i.e. was valid JSON)
        assert isinstance(result, dict)
        assert "scenes" in result

    @patch("backend.app.integrations.gemini.client.get_client")
    def test_clamps_scene_end_to_measured_source_duration(self, mock_get_client, tmp_path, monkeypatch):
        payload = {
            "project_id": "demo",
            "source": "source/v.mp4",
            "source_duration": 99.0,
            "scenes": [
                {
                    "scene_id": "scene_001",
                    "start": 0.0,
                    "end": 5.9,
                    "summary": "Short clip.",
                    "visual_tags": [],
                    "audio_notes": "",
                    "demo_relevance": 0.8,
                }
            ],
        }
        mock_client = MagicMock()
        mock_client.models.generate_content.return_value = _make_mock_text_response(payload)
        mock_get_client.return_value = mock_client

        (tmp_path / "source").mkdir()
        (tmp_path / "cache").mkdir()
        (tmp_path / "logs").mkdir()

        from backend.app.integrations.gemini import service
        from backend.app.media.models import MediaProbe

        monkeypatch.setattr(service, "find_primary_video", lambda project_path: None)
        monkeypatch.setattr(
            service,
            "_fallback_media_probe",
            lambda project_path: MediaProbe.model_validate(
                {
                    "project_id": "demo",
                    "source": "source/v.mp4",
                    "duration_seconds": 5.3867,
                    "has_audio": False,
                    "video_stream": {"codec": "unknown", "width": 1920, "height": 1080, "fps": 30.0},
                    "audio_stream": None,
                }
            ),
        )

        result = service.analyze_scenes(tmp_path)

        assert result["total_duration_seconds"] == pytest.approx(5.3867)
        assert result["sources"][0]["duration_seconds"] == pytest.approx(5.3867)
        assert result["scenes"][0]["end"] == pytest.approx(5.3867)


# ---------------------------------------------------------------------------
# service.py — generate_plan
# ---------------------------------------------------------------------------

class TestGeneratePlan:
    @patch("backend.app.integrations.gemini.client.get_client")
    def test_writes_plan_json(self, mock_get_client, tmp_path):
        scene_index = {
            "project_id": "demo",
            "source": "source/v.mp4",
            "source_duration": 30.0,
            "scenes": [
                {
                    "scene_id": "scene_001",
                    "start": 0.0,
                    "end": 10.0,
                    "summary": "Intro.",
                    "visual_tags": [],
                    "audio_notes": "",
                    "demo_relevance": 0.8,
                }
            ],
        }
        plan = {
            "project_id": "demo",
            "title": "Test Demo",
            "target_duration": 30.0,
            "story_arc": ["intro", "demo", "outro"],
            "beats": [
                {
                    "beat_id": "beat_001",
                    "type": "title",
                    "goal": "Brand",
                    "scene_id": None,
                    "duration": 3.0,
                    "narration": None,
                    "onscreen_text": "Demo",
                }
            ],
        }

        mock_client = MagicMock()
        mock_client.models.generate_content.return_value = _make_mock_text_response(plan)
        mock_get_client.return_value = mock_client

        cache_dir = tmp_path / "cache"
        cache_dir.mkdir()
        (cache_dir / "scene_index.json").write_text(json.dumps(scene_index))

        manifests_dir = tmp_path / "manifests"
        manifests_dir.mkdir()
        (tmp_path / "logs").mkdir()

        from backend.app.integrations.gemini.service import generate_plan
        result = generate_plan(tmp_path)

        assert (tmp_path / "manifests" / "plan.json").exists()
        assert "beats" in result


class TestGenerateVisualAssets:
    def test_generate_assets_writes_remotion_scene_bundle(self, monkeypatch, tmp_path):
        plan = {
            "project_id": "demo",
            "title": "DirectorLoop Demo",
            "target_duration": 12.0,
            "story_arc": ["hook", "demo"],
            "beats": [
                {
                    "beat_id": "beat_001",
                    "type": "title",
                    "goal": "Open strong",
                    "scene_id": None,
                    "duration": 3.0,
                    "narration": None,
                    "onscreen_text": "DirectorLoop",
                    "style": {
                        "font_family": "display-sans",
                        "background_mode": "color",
                        "background_color": "#111827",
                        "text_color": "#FFFFFF",
                        "accent_color": "#5B8CFF",
                        "layout_preset": "centered",
                        "text_alignment": "center",
                    },
                }
            ],
        }

        (tmp_path / "manifests").mkdir()
        (tmp_path / "cache").mkdir()
        (tmp_path / "logs").mkdir()
        (tmp_path / "manifests" / "plan.json").write_text(json.dumps(plan), encoding="utf-8")
        (tmp_path / "cache" / "scene_index.json").write_text(
            json.dumps(
                {
                    "project_id": "demo",
                    "source": "source/demo.mp4",
                    "source_duration": 10.0,
                    "scenes": [],
                }
            ),
            encoding="utf-8",
        )

        captured: dict[str, object] = {}

        def fake_complete_json(prompt, *, system=None, model=None, schema=None):
            captured["prompt"] = prompt
            return (
                {
                    "runtime_template": "hero-reveal",
                    "scene_spec": {
                        "version": 1,
                        "block_type": "title",
                        "text": "DirectorLoop",
                        "duration_seconds": 3.0,
                        "runtime_template": "hero-reveal",
                        "layout_preset": "centered",
                        "text_alignment": "center",
                        "font_family": "display-sans",
                        "font_variant": "bold",
                        "text_color": "#FFFFFF",
                        "accent_color": "#5B8CFF",
                        "background_mode": "color",
                        "background_color": "#111827",
                        "background_image_path": None,
                        "animation_preset": "fade-in",
                        "show_glass_panel": True,
                        "show_accent_bar": True,
                    },
                    "decorator_code": "export default null;\n",
                    "background_requirements": {
                        "mode": "local",
                        "prompt": None,
                    },
                },
                {
                    "elapsed_ms": 1,
                    "model": "gemini-test",
                    "input_token_count": 10,
                    "output_token_count": 20,
                },
            )

        monkeypatch.setattr("backend.app.integrations.gemini.service._client.complete_json", fake_complete_json)
        monkeypatch.setattr(
            "backend.app.integrations.gemini.service.render_remotion_preview",
            lambda project_path, scene_spec_path, decorator_module_path, output_path, settings: output_path.write_bytes(b"\x89PNG\r\n\x1a\n"),
        )

        from backend.app.integrations.gemini.service import generate_background_assets

        result = generate_background_assets(tmp_path)

        assert result[0]["scene_spec_path"] == "assets/remotion/001_title/scene.json"
        assert (tmp_path / "assets" / "remotion" / "001_title" / "scene.json").exists()
        assert (tmp_path / "assets" / "remotion" / "001_title" / "decorator.tsx").exists()
        assert (tmp_path / "assets" / "remotion" / "001_title" / "preview.png").exists()
        assert "Project title: DirectorLoop Demo" in str(captured["prompt"])
        assert "Neighboring beats" in str(captured["prompt"])

    @patch("backend.app.integrations.gemini.client.get_client")
    def test_plan_response_parses_as_json(self, mock_get_client, tmp_path):
        scene_index = {
            "project_id": "demo",
            "source": "source/v.mp4",
            "source_duration": 10.0,
            "scenes": [],
        }
        plan = {
            "project_id": "demo",
            "title": "T",
            "target_duration": 10.0,
            "story_arc": [],
            "beats": [],
        }

        mock_client = MagicMock()
        mock_client.models.generate_content.return_value = _make_mock_text_response(plan)
        mock_get_client.return_value = mock_client

        (tmp_path / "cache").mkdir()
        (tmp_path / "cache" / "scene_index.json").write_text(json.dumps(scene_index))
        (tmp_path / "manifests").mkdir()
        (tmp_path / "logs").mkdir()

        from backend.app.integrations.gemini.service import generate_plan
        result = generate_plan(tmp_path)
        assert isinstance(result, dict)
        assert "beats" in result


# ---------------------------------------------------------------------------
# service.py — precritique_manifest
# ---------------------------------------------------------------------------

class TestPrecritiqueManifest:
    @patch("backend.app.integrations.gemini.client.get_client")
    def test_critic_response_parses_as_json(self, mock_get_client, tmp_path):
        scene_index = {
            "project_id": "demo",
            "source": "source/v.mp4",
            "source_duration": 30.0,
            "scenes": [],
        }
        block_manifest = {
            "project_id": "demo",
            "version": 1,
            "render_settings": {},
            "blocks": [],
        }
        critic = {
            "project_id": "demo",
            "critic_scope": "blind_manifest_only",
            "suggestions": [],
        }

        mock_client = MagicMock()
        mock_client.models.generate_content.return_value = _make_mock_text_response(critic)
        mock_get_client.return_value = mock_client

        (tmp_path / "cache").mkdir()
        (tmp_path / "cache" / "scene_index.json").write_text(json.dumps(scene_index))
        (tmp_path / "manifests").mkdir()
        (tmp_path / "manifests" / "block_manifest.json").write_text(json.dumps(block_manifest))
        (tmp_path / "logs").mkdir()

        from backend.app.integrations.gemini.service import precritique_manifest
        result = precritique_manifest(tmp_path)
        assert isinstance(result, dict)
        assert "suggestions" in result

    @patch("backend.app.integrations.gemini.client.get_client")
    def test_all_suggestions_require_approval(self, mock_get_client, tmp_path):
        scene_index = {"project_id": "demo", "source": "", "source_duration": 30.0, "scenes": []}
        block_manifest = {"project_id": "demo", "version": 1, "render_settings": {}, "blocks": [
            {"block_id": "001", "type": "source_clip", "source": "", "source_start": 0.0,
             "source_end": 10.0, "video_duration": 10.0, "rendered_path": "blocks/001.mp4"}
        ]}
        critic = {
            "project_id": "demo",
            "critic_scope": "blind_manifest_only",
            "suggestions": [
                {
                    "suggestion_id": "s001",
                    "block_id": "001",
                    "action": "trim_end",
                    "amount_seconds": 1.0,
                    "max_allowed_trim_seconds": 3.0,
                    "reason": "Too long.",
                    "requires_approval": False,  # service must override to True
                }
            ],
        }

        mock_client = MagicMock()
        mock_client.models.generate_content.return_value = _make_mock_text_response(critic)
        mock_get_client.return_value = mock_client

        (tmp_path / "cache").mkdir()
        (tmp_path / "cache" / "scene_index.json").write_text(json.dumps(scene_index))
        (tmp_path / "manifests").mkdir()
        (tmp_path / "manifests" / "block_manifest.json").write_text(json.dumps(block_manifest))
        (tmp_path / "logs").mkdir()

        from backend.app.integrations.gemini.service import precritique_manifest
        result = precritique_manifest(tmp_path)
        for s in result["suggestions"]:
            assert s["requires_approval"] is True


# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------

class TestLogging:
    def test_log_does_not_contain_api_key(self, tmp_path):
        """Verify the logger never writes the API key to the log file."""
        import os
        fake_key = "FAKE_API_KEY_DO_NOT_LOG_12345"

        with patch.dict(os.environ, {"GEMINI_API_KEY": fake_key}):
            from backend.app.integrations.gemini.service import _log_call
            (tmp_path / "logs").mkdir()
            _log_call(
                project_path=tmp_path,
                project_id="demo",
                stage="test",
                model="gemini-2.5-flash-lite",
                elapsed_ms=100,
                input_tokens=10,
                output_tokens=20,
                artifact_path="cache/scene_index.json",
            )

        log_path = tmp_path / "logs" / "gemini_calls.jsonl"
        content = log_path.read_text()
        assert fake_key not in content

    def test_log_fields_are_present(self, tmp_path):
        (tmp_path / "logs").mkdir()
        from backend.app.integrations.gemini.service import _log_call
        _log_call(
            project_path=tmp_path,
            project_id="demo",
            stage="scene_analysis",
            model="gemini-2.5-flash-lite",
            elapsed_ms=250,
            input_tokens=100,
            output_tokens=200,
            artifact_path="cache/scene_index.json",
        )
        log_path = tmp_path / "logs" / "gemini_calls.jsonl"
        record = json.loads(log_path.read_text().strip())
        for field in ("timestamp", "project_id", "stage", "model",
                      "elapsed_ms", "input_token_count", "output_token_count",
                      "artifact_path"):
            assert field in record
