from pathlib import Path

from backend.app.media.service import find_source_videos


def test_find_source_videos_returns_sorted_videos_only(tmp_path):
    source_dir = tmp_path / "source"
    source_dir.mkdir()
    (source_dir / "b_clip.mov").write_bytes(b"x")
    (source_dir / "a_clip.mp4").write_bytes(b"x")
    (source_dir / "notes.txt").write_text("ignore", encoding="utf-8")
    (source_dir / "c_clip.mkv").write_bytes(b"x")

    videos = find_source_videos(tmp_path)

    assert [path.name for path in videos] == ["a_clip.mp4", "b_clip.mov", "c_clip.mkv"]
