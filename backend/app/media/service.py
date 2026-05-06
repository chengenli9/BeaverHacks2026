from __future__ import annotations

import json
import math
import shutil
import subprocess
from pathlib import Path

from PIL import Image, ImageStat

from .models import (
    AudioCheck,
    AudioStreamInfo,
    FrameCheck,
    MediaProbe,
    ProbedSource,
    QaIssue,
    RenderQa,
    RenderQaSummary,
    Shot,
    ShotIndex,
    TimelineSourceRef,
    VideoStreamInfo,
)


VIDEO_EXTENSIONS = (".mp4", ".mov", ".m4v", ".webm", ".avi", ".mkv")


def find_source_videos(project_path: str | Path) -> list[Path]:
    source_dir = Path(project_path) / "source"
    if not source_dir.exists():
        return []
    return [
        entry
        for entry in sorted(source_dir.iterdir(), key=lambda item: item.name.lower())
        if entry.is_file() and entry.suffix.lower() in VIDEO_EXTENSIONS
    ]


def find_primary_video(project_path: str | Path) -> Path | None:
    videos = find_source_videos(project_path)
    return videos[0] if videos else None


def inspect_source_media(project_path: str | Path) -> MediaProbe:
    project_root = Path(project_path)
    video_paths = find_source_videos(project_root)
    if not video_paths:
        raise FileNotFoundError("No source video found in project source/")
    sources: list[ProbedSource] = []
    offset = 0.0
    for video_path in video_paths:
        raw_probe = _ffprobe(video_path)
        video_stream = next((stream for stream in raw_probe.get("streams", []) if stream.get("codec_type") == "video"), None)
        if video_stream is None:
            raise RuntimeError(f"No video stream found in {video_path.name}")
        audio_stream = next((stream for stream in raw_probe.get("streams", []) if stream.get("codec_type") == "audio"), None)
        duration_seconds = float(raw_probe.get("format", {}).get("duration", 0) or 0)
        source = ProbedSource.model_validate(
            {
                "path": video_path.relative_to(project_root).as_posix(),
                "duration_seconds": duration_seconds,
                "has_audio": audio_stream is not None,
                "video_stream": {
                    "codec": video_stream.get("codec_name", "unknown"),
                    "width": int(video_stream.get("width", 0) or 0),
                    "height": int(video_stream.get("height", 0) or 0),
                    "fps": _parse_frame_rate(video_stream.get("avg_frame_rate") or video_stream.get("r_frame_rate") or "0/1"),
                },
                "audio_stream": None
                if audio_stream is None
                else {
                    "codec": audio_stream.get("codec_name", "unknown"),
                    "sample_rate": int(audio_stream.get("sample_rate", 0) or 0),
                    "channels": int(audio_stream.get("channels", 0) or 0) or None,
                },
                "start_offset_seconds": round(offset, 4),
                "end_offset_seconds": round(offset + duration_seconds, 4),
            }
        )
        sources.append(source)
        offset += duration_seconds

    probe = MediaProbe.model_validate(
        {
            "project_id": project_root.name,
            "total_duration_seconds": round(offset, 4),
            "sources": [source.model_dump(mode="json") for source in sources],
        }
    )

    out_path = project_root / "cache" / "media_probe.json"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(probe.model_dump_json(indent=2), encoding="utf-8")
    return probe


def detect_shots(project_path: str | Path, media_probe: MediaProbe | None = None) -> ShotIndex:
    project_root = Path(project_path)
    probe = media_probe or inspect_source_media(project_root)
    frames_dir = project_root / "cache" / "frames"
    frames_dir.mkdir(parents=True, exist_ok=True)
    normalized_shots: list[Shot] = []
    shot_counter = 1
    for source in probe.sources:
        source_path = project_root / source.path
        shots = _scenedetect_shots(source_path)
        if not shots:
            shots = [(0.0, source.duration_seconds)]

        for start, end in shots:
            end = max(end, start + 0.01)
            duration = max(end - start, 0.01)
            mid = start + duration / 2
            shot_id = f"shot_{shot_counter:03d}"
            start_frame = frames_dir / f"{shot_id}_start.jpg"
            mid_frame = frames_dir / f"{shot_id}_mid.jpg"
            end_frame = frames_dir / f"{shot_id}_end.jpg"
            _extract_frame(source_path, start, start_frame, source_duration_seconds=source.duration_seconds)
            _extract_frame(source_path, mid, mid_frame, source_duration_seconds=source.duration_seconds)
            _extract_frame(
                source_path,
                max(end - 0.05, start),
                end_frame,
                source_duration_seconds=source.duration_seconds,
            )
            normalized_shots.append(
                Shot.model_validate(
                    {
                        "shot_id": shot_id,
                        "source": source.path,
                        "start": round(source.start_offset_seconds + start, 3),
                        "end": round(source.start_offset_seconds + end, 3),
                        "duration": round(duration, 3),
                        "start_frame_path": start_frame.relative_to(project_root).as_posix(),
                        "mid_frame_path": mid_frame.relative_to(project_root).as_posix(),
                        "end_frame_path": end_frame.relative_to(project_root).as_posix(),
                    }
                )
            )
            shot_counter += 1

    shot_index = ShotIndex.model_validate(
        {
            "project_id": project_root.name,
            "total_duration_seconds": probe.total_duration_seconds,
            "sources": [
                TimelineSourceRef.model_validate(
                    {
                        "path": source.path,
                        "duration_seconds": source.duration_seconds,
                        "start_offset_seconds": source.start_offset_seconds,
                        "end_offset_seconds": source.end_offset_seconds,
                    }
                ).model_dump(mode="json")
                for source in probe.sources
            ],
            "shots": [shot.model_dump(mode="json") for shot in normalized_shots],
        }
    )
    out_path = project_root / "cache" / "shot_index.json"
    out_path.write_text(shot_index.model_dump_json(indent=2), encoding="utf-8")
    return shot_index


def build_render_qa(project_path: str | Path) -> RenderQa:
    project_root = Path(project_path)
    render_path = project_root / "renders" / "final_render.mp4"
    if not render_path.exists():
        raise FileNotFoundError("Render not available for review")

    raw_probe = _ffprobe(render_path)
    summary = RenderQaSummary.model_validate(
        {
            "has_video": any(stream.get("codec_type") == "video" for stream in raw_probe.get("streams", [])),
            "has_audio": any(stream.get("codec_type") == "audio" for stream in raw_probe.get("streams", [])),
            "duration_seconds": float(raw_probe.get("format", {}).get("duration", 0) or 0),
        }
    )

    qa_frames_dir = project_root / "cache" / "frames" / "render_qa"
    qa_frames_dir.mkdir(parents=True, exist_ok=True)
    timestamps = _review_timestamps(summary.duration_seconds)
    frame_checks: list[FrameCheck] = []
    issues: list[QaIssue] = []
    for index, timestamp in enumerate(timestamps, start=1):
        frame_path = qa_frames_dir / f"frame_{index:03d}.jpg"
        _extract_frame(render_path, timestamp, frame_path)
        frame_check = _analyze_frame(project_root, frame_path, timestamp)
        frame_checks.append(frame_check)
        if frame_check.is_near_black:
            issues.append(
                QaIssue(
                    code="near_black_frame",
                    severity="medium",
                    message=f"Frame at {timestamp:.2f}s is nearly black or empty.",
                    evidence=[frame_check.frame_path],
                )
            )

    audio_checks, audio_issues = _analyze_audio(render_path)
    issues.extend(audio_issues)

    render_qa = RenderQa.model_validate(
        {
            "project_id": project_root.name,
            "render_path": render_path.relative_to(project_root).as_posix(),
            "summary": summary.model_dump(mode="json"),
            "frame_checks": [check.model_dump(mode="json") for check in frame_checks],
            "audio_checks": [check.model_dump(mode="json") for check in audio_checks],
            "issues": [issue.model_dump(mode="json") for issue in issues],
        }
    )
    out_path = project_root / "cache" / "render_qa.json"
    out_path.write_text(render_qa.model_dump_json(indent=2), encoding="utf-8")
    return render_qa


def _ffprobe(path: Path) -> dict:
    if shutil.which("ffprobe") is None:
        raise RuntimeError("ffprobe is required for media inspection")
    command = [
        "ffprobe",
        "-v",
        "error",
        "-show_streams",
        "-show_format",
        "-of",
        "json",
        str(path),
    ]
    completed = subprocess.run(command, capture_output=True, text=True, check=True)
    return json.loads(completed.stdout)


def _parse_frame_rate(value: str) -> float:
    if not value or value == "0/0":
        return 0.0
    if "/" in value:
        numerator, denominator = value.split("/", 1)
        denominator_value = float(denominator or 0)
        if denominator_value == 0:
            return 0.0
        return round(float(numerator) / denominator_value, 3)
    return float(value)


def _scenedetect_shots(source_path: Path) -> list[tuple[float, float]]:
    try:
        from scenedetect import SceneManager, open_video
        from scenedetect.detectors import ContentDetector
    except Exception:
        return []

    video = open_video(str(source_path))
    manager = SceneManager()
    manager.add_detector(ContentDetector())
    manager.detect_scenes(video, show_progress=False)
    detected = manager.get_scene_list()
    return [
        (round(scene_start.get_seconds(), 3), round(scene_end.get_seconds(), 3))
        for scene_start, scene_end in detected
    ]


def _extract_frame(
    video_path: Path,
    timestamp_seconds: float,
    output_path: Path,
    *,
    source_duration_seconds: float | None = None,
) -> None:
    if shutil.which("ffmpeg") is None:
        raise RuntimeError("ffmpeg is required for frame extraction")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    for candidate in _frame_timestamp_candidates(timestamp_seconds, source_duration_seconds):
        command = [
            "ffmpeg",
            "-y",
            "-ss",
            f"{candidate:.3f}",
            "-i",
            str(video_path),
            "-frames:v",
            "1",
            str(output_path),
        ]
        completed = subprocess.run(command, capture_output=True, text=True)
        if completed.returncode == 0 and output_path.exists() and output_path.stat().st_size > 0:
            return
    raise subprocess.CalledProcessError(
        completed.returncode,
        command,
        output=completed.stdout,
        stderr=completed.stderr,
    )


def _frame_timestamp_candidates(
    timestamp_seconds: float,
    source_duration_seconds: float | None,
) -> list[float]:
    base = max(timestamp_seconds, 0.0)
    if source_duration_seconds is None or source_duration_seconds <= 0:
        return [round(base, 3)]

    max_valid = max(source_duration_seconds - 0.25, 0.0)
    clamped = min(base, max_valid)
    candidates = [clamped]
    for step in (0.05, 0.1, 0.25, 0.5, 1.0):
        candidate = min(max(base - step, 0.0), max_valid)
        if candidate not in candidates:
            candidates.append(candidate)
    return [round(candidate, 3) for candidate in candidates]


def _review_timestamps(duration_seconds: float) -> list[float]:
    if duration_seconds <= 0:
        return [0.0]
    points = [0.0, duration_seconds / 2, max(duration_seconds - 0.1, 0.0)]
    return sorted({round(point, 3) for point in points})


def _analyze_frame(project_root: Path, frame_path: Path, timestamp_seconds: float) -> FrameCheck:
    image = Image.open(frame_path).convert("RGB")
    grayscale = image.convert("L")
    stats = ImageStat.Stat(grayscale)
    average_brightness = float(stats.mean[0])
    contrast = float(stats.stddev[0])
    is_near_black = average_brightness < 18 and contrast < 12
    return FrameCheck.model_validate(
        {
            "frame_path": frame_path.relative_to(project_root).as_posix(),
            "timestamp_seconds": timestamp_seconds,
            "average_brightness": round(average_brightness, 3),
            "contrast": round(contrast, 3),
            "is_near_black": is_near_black,
        }
    )


def _analyze_audio(render_path: Path) -> tuple[list[AudioCheck], list[QaIssue]]:
    checks: list[AudioCheck] = []
    issues: list[QaIssue] = []
    if shutil.which("ffmpeg") is None:
        return checks, issues

    loudness_command = [
        "ffmpeg",
        "-i",
        str(render_path),
        "-af",
        "volumedetect",
        "-f",
        "null",
        "-",
    ]
    loudness_run = subprocess.run(loudness_command, capture_output=True, text=True)
    mean_volume = _extract_named_db_value(loudness_run.stderr, "mean_volume")
    if mean_volume is not None:
        checks.append(AudioCheck(check_type="loudness", details=f"mean_volume={mean_volume:.2f} dB", value=mean_volume))
        if mean_volume < -35:
            issues.append(
                QaIssue(
                    code="quiet_mix",
                    severity="medium",
                    message="Rendered audio mix is very quiet.",
                    evidence=[f"mean_volume={mean_volume:.2f} dB"],
                )
            )

    silence_command = [
        "ffmpeg",
        "-i",
        str(render_path),
        "-af",
        "silencedetect=noise=-40dB:d=0.5",
        "-f",
        "null",
        "-",
    ]
    silence_run = subprocess.run(silence_command, capture_output=True, text=True)
    silence_duration = _extract_silence_duration(silence_run.stderr)
    if silence_duration is not None:
        checks.append(AudioCheck(check_type="silence", details=f"silence_duration={silence_duration:.2f}s", value=silence_duration))
        if silence_duration >= 1.5:
            issues.append(
                QaIssue(
                    code="long_silence",
                    severity="low",
                    message="Rendered output contains a long silence window.",
                    evidence=[f"silence_duration={silence_duration:.2f}s"],
                )
            )

    return checks, issues


def _extract_named_db_value(stderr: str, field_name: str) -> float | None:
    needle = f"{field_name}:"
    for line in stderr.splitlines():
        if needle not in line:
            continue
        raw_value = line.split(needle, 1)[1].strip().split(" ", 1)[0]
        try:
            return float(raw_value)
        except ValueError:
            return None
    return None


def _extract_silence_duration(stderr: str) -> float | None:
    durations: list[float] = []
    for line in stderr.splitlines():
        if "silence_duration:" not in line:
            continue
        raw_value = line.split("silence_duration:", 1)[1].strip().split(" ", 1)[0]
        try:
            durations.append(float(raw_value))
        except ValueError:
            continue
    if not durations:
        return None
    return max(durations)
