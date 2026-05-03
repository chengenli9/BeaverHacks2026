from backend.app.manifests.models import BlockManifest
from backend.app.manifests.service import reconcile_durations


def test_duration_reconciliation_extends_source_end_when_tts_is_longer():
    manifest = BlockManifest.model_validate(
        {
            "project_id": "demo_project",
            "version": 1,
            "render_settings": {},
            "blocks": [
                {
                    "block_id": "002_demo",
                    "type": "source_clip",
                    "source": "source/demo_footage.mp4",
                    "source_start": 12.0,
                    "source_end": 18.0,
                    "video_duration": 6.0,
                    "tts_asset": "assets/tts/tts_002.wav",
                    "tts_duration": 7.5,
                    "source_audio_volume": 1.0,
                    "tts_fade_seconds": 0.5,
                    "rendered_path": "blocks/002_demo.mp4",
                }
            ],
        }
    )

    reconciled = reconcile_durations(manifest)
    block = reconciled.blocks[0]

    assert block.source_end == 19.5
    assert block.video_duration == 7.5
    assert block.video_duration >= block.tts_duration

