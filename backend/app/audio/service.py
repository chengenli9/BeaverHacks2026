"""Music library service — parses audio-descriptions.md and resolves track paths."""

from __future__ import annotations

import json
import re
import subprocess
from pathlib import Path

from ..manifests.models import MusicTrackRef

_REPO_ROOT = Path(__file__).resolve().parents[3]  # BeaverHacks2026/
_MUSIC_DIR = _REPO_ROOT / "assets" / "music"
_DESCRIPTIONS_FILE = _MUSIC_DIR / "audio-descriptions.md"

_cache: list[MusicTrackRef] | None = None


def load_music_library() -> list[MusicTrackRef]:
    """Parse the global audio-descriptions.md and return track metadata."""
    global _cache
    if _cache is not None:
        return _cache

    if not _DESCRIPTIONS_FILE.exists():
        _cache = []
        return _cache

    text = _DESCRIPTIONS_FILE.read_text(encoding="utf-8")
    # Strip leading whitespace per line for reliable parsing
    text = "\n".join(line.strip() for line in text.split("\n"))
    tracks: list[MusicTrackRef] = []

    # Each entry is separated by "---" on its own line.
    # Header: 1. "Display Name" - filename.mp3
    blocks = re.split(r"^---\s*$", text, flags=re.MULTILINE)
    for block in blocks:
        block = block.strip()
        if not block:
            continue

        header_match = re.match(
            r'\d+\.\s+"([^"]+)"\s*-\s*(\S+\.mp3)',
            block,
        )
        if not header_match:
            continue

        display_name = header_match.group(1)
        filename = header_match.group(2)

        # Extract BPM
        bpm_match = re.search(r'(\d+)\s*BPM', block)
        bpm = int(bpm_match.group(1)) if bpm_match else None

        # Extract use case
        use_case_match = re.search(r'Use case:\s*(.+?)(?:\n|$)', block, re.IGNORECASE)
        use_case = use_case_match.group(1).strip() if use_case_match else None

        # Build description from the paragraph after the header
        lines = block.split("\n")
        desc_lines: list[str] = []
        past_header = False
        for line in lines[1:]:
            stripped = line.strip()
            if not stripped:
                if past_header and desc_lines:
                    break
                continue
            if stripped.lower().startswith("use case"):
                break
            past_header = True
            desc_lines.append(stripped)
        description = " ".join(desc_lines).strip() or display_name

        if (_MUSIC_DIR / filename).exists():
            tracks.append(
                MusicTrackRef(
                    filename=filename,
                    display_name=display_name,
                    description=description,
                    bpm=bpm,
                    use_case=use_case,
                )
            )

    _cache = tracks
    return _cache


def resolve_music_path(filename: str) -> Path:
    """Return absolute path to a music file in the global library."""
    path = _MUSIC_DIR / filename
    if not path.exists():
        raise FileNotFoundError(f"Music file not found: {path}")
    return path


def get_audio_duration(path: str | Path) -> float:
    """Get audio duration in seconds using ffprobe."""
    command = [
        "ffprobe",
        "-v", "error",
        "-show_entries", "format=duration",
        "-of", "json",
        str(path),
    ]
    result = subprocess.run(command, capture_output=True, text=True, check=True)
    data = json.loads(result.stdout)
    return float(data["format"]["duration"])


def music_library_for_prompt() -> str:
    """Format the music library as a compact text block for Gemini prompts."""
    tracks = load_music_library()
    if not tracks:
        return "No music tracks available."
    lines = ["Available music tracks:"]
    for t in tracks:
        bpm_str = f", {t.bpm} BPM" if t.bpm else ""
        lines.append(
            f'  - "{t.filename}" ({t.display_name}{bpm_str}): {t.use_case or t.description}'
        )
    return "\n".join(lines)
