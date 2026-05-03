from __future__ import annotations

import json
from pathlib import Path
from typing import Annotated, Any, Literal, Union

from pydantic import BaseModel, Field, ValidationError, field_validator, model_validator


class RenderSettings(BaseModel):
    width: int = 1920
    height: int = 1080
    fps: int = 30
    video_codec: str = "libx264"
    audio_codec: str = "aac"
    sample_rate: int = 48000
    pixel_format: str = "yuv420p"


class MotionAssetRef(BaseModel):
    kind: Literal["remotion_scene"]
    runtime_template: Literal["hero-reveal", "split-panel", "stacked-pulse"]
    scene_spec_path: str
    decorator_module_path: str | None = None
    preview_frame_path: str | None = None

    @field_validator("scene_spec_path", "decorator_module_path", "preview_frame_path")
    @classmethod
    def motion_asset_paths_must_be_project_relative(cls, value: str | None) -> str | None:
        if value is not None:
            _validate_project_relative_path(value)
        return value


class BeatStyle(BaseModel):
    font_family: str | None = None
    font_variant: str | None = None
    text_color: str | None = None
    accent_color: str | None = None
    background_mode: Literal["image", "color", "gradient", "image_tint"] | None = None
    background_color: str | None = None
    text_alignment: Literal["left", "center", "right"] | None = None
    layout_preset: Literal["centered", "hero-left", "hero-right", "stacked"] | None = None


class TimelineSource(BaseModel):
    path: str
    duration_seconds: float = Field(gt=0)
    start_offset_seconds: float = Field(ge=0)
    end_offset_seconds: float = Field(gt=0)

    @field_validator("path")
    @classmethod
    def path_must_be_project_relative(cls, value: str) -> str:
        _validate_project_relative_path(value)
        return value

    @model_validator(mode="after")
    def offsets_must_match_duration(self) -> "TimelineSource":
        if self.end_offset_seconds <= self.start_offset_seconds:
            raise ValueError("source end offset must be greater than start offset")
        expected = round(self.end_offset_seconds - self.start_offset_seconds, 6)
        if abs(expected - self.duration_seconds) > 0.01:
            raise ValueError("source offset range must match duration_seconds")
        return self


class Scene(BaseModel):
    scene_id: str
    source: str
    start: float = Field(ge=0)
    end: float = Field(gt=0)
    summary: str
    visual_tags: list[str] = Field(default_factory=list)
    audio_notes: str
    demo_relevance: float = Field(ge=0, le=1)

    @field_validator("source")
    @classmethod
    def scene_source_must_be_project_relative(cls, value: str) -> str:
        _validate_project_relative_path(value)
        return value

    @model_validator(mode="after")
    def end_must_follow_start(self) -> Scene:
        if self.end <= self.start:
            raise ValueError("scene end must be greater than start")
        return self


class SceneIndex(BaseModel):
    project_id: str
    total_duration_seconds: float = Field(gt=0)
    sources: list[TimelineSource]
    scenes: list[Scene]

    @model_validator(mode="before")
    @classmethod
    def normalize_legacy_shape(cls, value: Any) -> Any:
        if not isinstance(value, dict):
            return value
        payload = dict(value)
        legacy_source = payload.pop("source", None)
        legacy_duration = payload.pop("source_duration", None)
        if "sources" not in payload:
            if legacy_source is None or legacy_duration is None:
                return payload
            payload["sources"] = [
                {
                    "path": legacy_source,
                    "duration_seconds": legacy_duration,
                    "start_offset_seconds": 0.0,
                    "end_offset_seconds": legacy_duration,
                }
            ]
        if "total_duration_seconds" not in payload:
            payload["total_duration_seconds"] = sum(
                float(source.get("duration_seconds", 0) or 0) for source in payload.get("sources", [])
            )
        if payload.get("sources"):
            default_source = payload["sources"][0]["path"]
            for scene in payload.get("scenes", []):
                scene.setdefault("source", default_source)
        return payload

    @classmethod
    def from_file(cls, path: str | Path) -> SceneIndex:
        return cls.model_validate(json.loads(Path(path).read_text(encoding="utf-8")))

    @model_validator(mode="after")
    def scenes_must_be_unique_and_within_source(self) -> SceneIndex:
        scene_ids = [scene.scene_id for scene in self.scenes]
        if len(scene_ids) != len(set(scene_ids)):
            raise ValueError("scene_id values must be unique")
        source_ranges = {source.path: source for source in self.sources}
        if len(source_ranges) != len(self.sources):
            raise ValueError("source path values must be unique")
        if not source_ranges:
            raise ValueError("scene index must include at least one source")
        if abs(sum(source.duration_seconds for source in self.sources) - self.total_duration_seconds) > 0.01:
            raise ValueError("total_duration_seconds must equal the sum of source durations")
        previous_start = -1.0
        for scene in self.scenes:
            source = source_ranges.get(scene.source)
            if source is None:
                raise ValueError(f"scene {scene.scene_id} references unknown source {scene.source}")
            if scene.start < source.start_offset_seconds or scene.end > source.end_offset_seconds:
                raise ValueError("scene ranges must be within source_duration")
            if scene.start < previous_start:
                raise ValueError("scene ranges must be in non-decreasing order")
            previous_start = scene.start
        return self

    def scene_by_id(self, scene_id: str) -> Scene:
        for scene in self.scenes:
            if scene.scene_id == scene_id:
                return scene
        raise KeyError(f"Unknown scene_id: {scene_id}")

    def source_by_path(self, source_path: str) -> TimelineSource:
        for source in self.sources:
            if source.path == source_path:
                return source
        raise KeyError(f"Unknown source path: {source_path}")

    def source_duration_map(self) -> dict[str, float]:
        return {source.path: source.duration_seconds for source in self.sources}

    @property
    def source(self) -> str:
        return self.sources[0].path

    @property
    def source_duration(self) -> float:
        return self.sources[0].duration_seconds


class PlanBeat(BaseModel):
    beat_id: str
    type: Literal["title", "source_clip", "scene_card", "end_card"]
    goal: str
    scene_id: str | None = None
    duration: float = Field(gt=0)
    narration: str | None = None
    onscreen_text: str | None = None
    style: BeatStyle | None = None

    @model_validator(mode="after")
    def source_beats_require_scene_id(self) -> PlanBeat:
        if self.type == "source_clip" and not self.scene_id:
            raise ValueError("source_clip beats require scene_id")
        if self.type != "source_clip" and self.scene_id is not None:
            raise ValueError("non-source beats cannot reference scene_id")
        return self


class Plan(BaseModel):
    project_id: str
    title: str
    target_duration: float = Field(gt=0)
    story_arc: list[str]
    beats: list[PlanBeat]

    @classmethod
    def from_file(cls, path: str | Path) -> Plan:
        return cls.model_validate(json.loads(Path(path).read_text(encoding="utf-8")))

    @model_validator(mode="after")
    def beat_ids_must_be_unique(self) -> Plan:
        beat_ids = [beat.beat_id for beat in self.beats]
        if len(beat_ids) != len(set(beat_ids)):
            raise ValueError("beat_id values must be unique")
        return self

    def beat_by_id(self, beat_id: str) -> PlanBeat:
        for beat in self.beats:
            if beat.beat_id == beat_id:
                return beat
        raise KeyError(f"Unknown beat_id: {beat_id}")

    def validate_against_scene_index(self, scene_index: SceneIndex) -> None:
        if self.project_id != scene_index.project_id:
            raise ValueError("plan project_id must match scene index project_id")
        scene_ids = {scene.scene_id for scene in scene_index.scenes}
        for beat in self.beats:
            if beat.scene_id and beat.scene_id not in scene_ids:
                raise ValueError(f"Unknown scene_id in plan beat {beat.beat_id}: {beat.scene_id}")


class BaseBlock(BaseModel):
    block_id: str
    type: str
    rendered_path: str
    motion_asset: MotionAssetRef | None = None

    @field_validator("rendered_path")
    @classmethod
    def rendered_path_must_be_project_relative(cls, value: str) -> str:
        _validate_project_relative_path(value)
        return value


class TextBlock(BaseBlock):
    background_asset: str | None = None
    text: str
    duration: float = Field(gt=0)
    fontfile: str
    font_family: str | None = None
    font_variant: str | None = None
    text_color: str | None = None
    accent_color: str | None = None
    background_mode: Literal["image", "color", "gradient", "image_tint"] = "image"
    background_color: str | None = None
    text_alignment: Literal["left", "center", "right"] = "center"
    layout_preset: Literal["centered", "hero-left", "hero-right", "stacked"] = "centered"

    @field_validator("background_asset", "fontfile")
    @classmethod
    def text_paths_must_be_project_relative(cls, value: str | None) -> str | None:
        if value is not None:
            _validate_project_relative_path(value)
        return value

    @model_validator(mode="after")
    def validate_background_requirements(self) -> "TextBlock":
        if self.background_mode in {"image", "image_tint"} and not self.background_asset and self.motion_asset is None:
            raise ValueError("background_asset is required for image-based text blocks")
        return self


class TitleBlock(TextBlock):
    type: Literal["title"]


class EndCardBlock(TextBlock):
    type: Literal["end_card"]


class SceneCardBlock(TextBlock):
    type: Literal["scene_card"]


class SourceClipBlock(BaseBlock):
    type: Literal["source_clip"]
    source: str
    source_start: float = Field(ge=0)
    source_end: float = Field(gt=0)
    video_duration: float = Field(gt=0)
    tts_asset: str | None = None
    tts_duration: float | None = Field(default=None, ge=0)
    source_audio_volume: float = Field(default=1.0, ge=0, le=1)
    tts_fade_seconds: float = Field(default=0.5, ge=0)

    @field_validator("source", "tts_asset")
    @classmethod
    def source_paths_must_be_project_relative(cls, value: str | None) -> str | None:
        if value is not None:
            _validate_project_relative_path(value)
        return value

    @model_validator(mode="after")
    def validate_source_timing(self) -> SourceClipBlock:
        if self.source_end <= self.source_start:
            raise ValueError("source_end must be greater than source_start")
        expected_duration = round(self.source_end - self.source_start, 6)
        if abs(self.video_duration - expected_duration) > 0.001:
            raise ValueError("video_duration must equal source_end - source_start")
        if self.tts_asset is not None and self.tts_duration is None:
            raise ValueError("tts_duration is required when tts_asset is set")
        return self


Block = Annotated[
    Union[TitleBlock, SourceClipBlock, SceneCardBlock, EndCardBlock],
    Field(discriminator="type"),
]


class BlockManifest(BaseModel):
    project_id: str
    version: int
    render_settings: RenderSettings = Field(default_factory=RenderSettings)
    blocks: list[Block]

    @classmethod
    def from_file(cls, path: str | Path) -> BlockManifest:
        return cls.model_validate(json.loads(Path(path).read_text(encoding="utf-8")))

    @model_validator(mode="after")
    def block_ids_must_be_unique(self) -> BlockManifest:
        block_ids = [block.block_id for block in self.blocks]
        if len(block_ids) != len(set(block_ids)):
            raise ValueError("block_id values must be unique")
        return self

    def block_by_id(self, block_id: str) -> Block:
        for block in self.blocks:
            if block.block_id == block_id:
                return block
        raise KeyError(f"Unknown block_id: {block_id}")


class CriticSuggestion(BaseModel):
    suggestion_id: str
    block_id: str
    action: Literal["trim_end", "extend_end", "reorder_after", "replace_text", "lower_source_audio"]
    amount_seconds: float = Field(default=0, ge=0)
    max_allowed_trim_seconds: float = Field(default=0, ge=0)
    reason: str
    requires_approval: bool = True
    replacement_text: str | None = None
    target_block_id: str | None = None
    source_audio_volume: float | None = Field(default=None, ge=0, le=1)
    category: str | None = None
    severity: Literal["low", "medium", "high"] | None = None
    confidence: float | None = Field(default=None, ge=0, le=1)
    viewer_problem: str | None = None
    evidence: list[str] = Field(default_factory=list)
    before_summary: str | None = None
    after_summary: str | None = None

    @model_validator(mode="after")
    def approval_required_for_mvp(self) -> CriticSuggestion:
        if not self.requires_approval:
            raise ValueError("requires_approval must be true for MVP suggestions")
        if self.action == "replace_text" and not self.replacement_text:
            raise ValueError("replacement_text is required for replace_text")
        if self.action == "reorder_after" and not self.target_block_id:
            raise ValueError("target_block_id is required for reorder_after")
        return self


class CriticSuggestions(BaseModel):
    project_id: str
    critic_scope: Literal["blind_manifest_only", "render_review"]
    suggestions: list[CriticSuggestion]

    @classmethod
    def from_file(cls, path: str | Path) -> CriticSuggestions:
        return cls.model_validate(json.loads(Path(path).read_text(encoding="utf-8")))

    def suggestion_by_id(self, suggestion_id: str) -> CriticSuggestion:
        for suggestion in self.suggestions:
            if suggestion.suggestion_id == suggestion_id:
                return suggestion
        raise KeyError(f"Unknown suggestion_id: {suggestion_id}")


class ApplyPatchesRequest(BaseModel):
    project_id: str
    approved_suggestion_ids: list[str] = Field(default_factory=list)
    rejected_suggestion_ids: list[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def suggestion_ids_must_not_overlap(self) -> ApplyPatchesRequest:
        approved = set(self.approved_suggestion_ids)
        rejected = set(self.rejected_suggestion_ids)
        overlap = approved & rejected
        if overlap:
            raise ValueError(f"suggestion ids cannot be both approved and rejected: {sorted(overlap)}")
        return self


def _validate_project_relative_path(value: str) -> None:
    path = Path(value)
    if path.is_absolute() or ".." in path.parts:
        raise ValueError("paths must be project-relative and cannot contain '..'")
