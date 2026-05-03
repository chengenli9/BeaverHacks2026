from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, Field, field_validator, model_validator


def _validate_project_relative_path(value: str) -> str:
    path = Path(value)
    if path.is_absolute() or ".." in path.parts:
        raise ValueError("paths must be project-relative and cannot contain '..'")
    return value


class VideoStreamInfo(BaseModel):
    codec: str
    width: int = Field(gt=0)
    height: int = Field(gt=0)
    fps: float = Field(gt=0)


class AudioStreamInfo(BaseModel):
    codec: str
    sample_rate: int = Field(gt=0)
    channels: int | None = Field(default=None, gt=0)


class ProbedSource(BaseModel):
    path: str
    duration_seconds: float = Field(gt=0)
    has_audio: bool
    video_stream: VideoStreamInfo
    audio_stream: AudioStreamInfo | None = None
    start_offset_seconds: float = Field(ge=0)
    end_offset_seconds: float = Field(gt=0)

    @field_validator("path")
    @classmethod
    def path_is_project_relative(cls, value: str) -> str:
        return _validate_project_relative_path(value)

    @model_validator(mode="after")
    def offsets_match_duration(self) -> "ProbedSource":
        if self.end_offset_seconds <= self.start_offset_seconds:
            raise ValueError("source end offset must be greater than start offset")
        expected = round(self.end_offset_seconds - self.start_offset_seconds, 6)
        if abs(expected - self.duration_seconds) > 0.01:
            raise ValueError("source offset range must match duration_seconds")
        return self


class MediaProbe(BaseModel):
    project_id: str
    total_duration_seconds: float = Field(gt=0)
    sources: list[ProbedSource]

    @model_validator(mode="before")
    @classmethod
    def normalize_legacy_shape(cls, value: Any) -> Any:
        if not isinstance(value, dict):
            return value
        payload = dict(value)
        legacy_source = payload.pop("source", None)
        legacy_duration = payload.pop("duration_seconds", None)
        legacy_has_audio = payload.pop("has_audio", None)
        legacy_video_stream = payload.pop("video_stream", None)
        legacy_audio_stream = payload.pop("audio_stream", None)
        if "sources" not in payload and legacy_source is not None:
            payload["sources"] = [
                {
                    "path": legacy_source,
                    "duration_seconds": legacy_duration,
                    "has_audio": legacy_has_audio,
                    "video_stream": legacy_video_stream,
                    "audio_stream": legacy_audio_stream,
                    "start_offset_seconds": 0.0,
                    "end_offset_seconds": legacy_duration,
                }
            ]
        if "total_duration_seconds" not in payload:
            payload["total_duration_seconds"] = sum(
                float(source.get("duration_seconds", 0) or 0) for source in payload.get("sources", [])
            )
        return payload

    @classmethod
    def from_file(cls, path: str | Path) -> "MediaProbe":
        return cls.model_validate(json.loads(Path(path).read_text(encoding="utf-8")))

    @model_validator(mode="after")
    def validate_totals(self) -> "MediaProbe":
        if not self.sources:
            raise ValueError("media probe must include at least one source")
        if abs(sum(source.duration_seconds for source in self.sources) - self.total_duration_seconds) > 0.01:
            raise ValueError("total_duration_seconds must equal the sum of source durations")
        return self

    @property
    def source(self) -> str:
        return self.sources[0].path

    @property
    def duration_seconds(self) -> float:
        return self.sources[0].duration_seconds

    @property
    def has_audio(self) -> bool:
        return any(source.has_audio for source in self.sources)

    @property
    def video_stream(self) -> VideoStreamInfo:
        return self.sources[0].video_stream

    @property
    def audio_stream(self) -> AudioStreamInfo | None:
        return self.sources[0].audio_stream


class Shot(BaseModel):
    shot_id: str
    source: str
    start: float = Field(ge=0)
    end: float = Field(gt=0)
    duration: float = Field(gt=0)
    start_frame_path: str
    mid_frame_path: str
    end_frame_path: str

    @field_validator("source", "start_frame_path", "mid_frame_path", "end_frame_path")
    @classmethod
    def frame_paths_are_project_relative(cls, value: str) -> str:
        return _validate_project_relative_path(value)


class TimelineSourceRef(BaseModel):
    path: str
    duration_seconds: float = Field(gt=0)
    start_offset_seconds: float = Field(ge=0)
    end_offset_seconds: float = Field(gt=0)

    @field_validator("path")
    @classmethod
    def path_is_project_relative(cls, value: str) -> str:
        return _validate_project_relative_path(value)


class ShotIndex(BaseModel):
    project_id: str
    total_duration_seconds: float = Field(gt=0)
    sources: list[TimelineSourceRef]
    shots: list[Shot]

    @model_validator(mode="before")
    @classmethod
    def normalize_legacy_shape(cls, value: Any) -> Any:
        if not isinstance(value, dict):
            return value
        payload = dict(value)
        legacy_source = payload.pop("source", None)
        if "sources" not in payload and legacy_source is not None:
            max_end = max((float(shot.get("end", 0) or 0) for shot in payload.get("shots", [])), default=0.0)
            payload["sources"] = [
                {
                    "path": legacy_source,
                    "duration_seconds": max_end or 0.01,
                    "start_offset_seconds": 0.0,
                    "end_offset_seconds": max_end or 0.01,
                }
            ]
        if "total_duration_seconds" not in payload:
            payload["total_duration_seconds"] = sum(
                float(source.get("duration_seconds", 0) or 0) for source in payload.get("sources", [])
            )
        if payload.get("sources"):
            default_source = payload["sources"][0]["path"]
            for shot in payload.get("shots", []):
                shot.setdefault("source", default_source)
        return payload

    @classmethod
    def from_file(cls, path: str | Path) -> "ShotIndex":
        return cls.model_validate(json.loads(Path(path).read_text(encoding="utf-8")))

    @model_validator(mode="after")
    def validate_sources(self) -> "ShotIndex":
        if not self.sources:
            raise ValueError("shot index must include at least one source")
        source_paths = {source.path for source in self.sources}
        for shot in self.shots:
            if shot.source not in source_paths:
                raise ValueError(f"shot {shot.shot_id} references unknown source {shot.source}")
        return self

    @property
    def source(self) -> str:
        return self.sources[0].path


class FrameCheck(BaseModel):
    frame_path: str
    timestamp_seconds: float = Field(ge=0)
    average_brightness: float = Field(ge=0, le=255)
    contrast: float = Field(ge=0)
    is_near_black: bool = False
    text_contrast_ratio: float | None = Field(default=None, ge=0)

    @field_validator("frame_path")
    @classmethod
    def frame_path_is_project_relative(cls, value: str) -> str:
        return _validate_project_relative_path(value)


class AudioCheck(BaseModel):
    check_type: Literal["silence", "loudness"]
    details: str
    value: float | None = None


class RenderQaSummary(BaseModel):
    has_video: bool
    has_audio: bool
    duration_seconds: float = Field(gt=0)


class QaIssue(BaseModel):
    code: str
    severity: Literal["low", "medium", "high"]
    message: str
    evidence: list[str] = Field(default_factory=list)


class RenderQa(BaseModel):
    project_id: str
    render_path: str
    summary: RenderQaSummary
    frame_checks: list[FrameCheck] = Field(default_factory=list)
    audio_checks: list[AudioCheck] = Field(default_factory=list)
    issues: list[QaIssue] = Field(default_factory=list)

    @field_validator("render_path")
    @classmethod
    def render_path_is_project_relative(cls, value: str) -> str:
        return _validate_project_relative_path(value)

    @classmethod
    def from_file(cls, path: str | Path) -> "RenderQa":
        return cls.model_validate(json.loads(Path(path).read_text(encoding="utf-8")))
