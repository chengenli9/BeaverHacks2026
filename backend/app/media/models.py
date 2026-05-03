from __future__ import annotations

import json
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, Field, field_validator


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


class MediaProbe(BaseModel):
    project_id: str
    source: str
    duration_seconds: float = Field(gt=0)
    has_audio: bool
    video_stream: VideoStreamInfo
    audio_stream: AudioStreamInfo | None = None

    @field_validator("source")
    @classmethod
    def source_is_project_relative(cls, value: str) -> str:
        return _validate_project_relative_path(value)

    @classmethod
    def from_file(cls, path: str | Path) -> "MediaProbe":
        return cls.model_validate(json.loads(Path(path).read_text(encoding="utf-8")))


class Shot(BaseModel):
    shot_id: str
    start: float = Field(ge=0)
    end: float = Field(gt=0)
    duration: float = Field(gt=0)
    start_frame_path: str
    mid_frame_path: str
    end_frame_path: str

    @field_validator("start_frame_path", "mid_frame_path", "end_frame_path")
    @classmethod
    def frame_paths_are_project_relative(cls, value: str) -> str:
        return _validate_project_relative_path(value)


class ShotIndex(BaseModel):
    project_id: str
    source: str
    shots: list[Shot]

    @field_validator("source")
    @classmethod
    def source_is_project_relative(cls, value: str) -> str:
        return _validate_project_relative_path(value)

    @classmethod
    def from_file(cls, path: str | Path) -> "ShotIndex":
        return cls.model_validate(json.loads(Path(path).read_text(encoding="utf-8")))


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
