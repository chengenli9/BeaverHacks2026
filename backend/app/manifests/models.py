from __future__ import annotations

import json
from pathlib import Path
from typing import Annotated, Literal, Union

from pydantic import BaseModel, Field, ValidationError, field_validator, model_validator


class RenderSettings(BaseModel):
    width: int = 1920
    height: int = 1080
    fps: int = 30
    video_codec: str = "libx264"
    audio_codec: str = "aac"
    sample_rate: int = 48000
    pixel_format: str = "yuv420p"


class Scene(BaseModel):
    scene_id: str
    start: float = Field(ge=0)
    end: float = Field(gt=0)
    summary: str
    visual_tags: list[str] = Field(default_factory=list)
    audio_notes: str
    demo_relevance: float = Field(ge=0, le=1)

    @model_validator(mode="after")
    def end_must_follow_start(self) -> Scene:
        if self.end <= self.start:
            raise ValueError("scene end must be greater than start")
        return self


class SceneIndex(BaseModel):
    project_id: str
    source: str
    source_duration: float = Field(gt=0)
    scenes: list[Scene]

    @classmethod
    def from_file(cls, path: str | Path) -> SceneIndex:
        return cls.model_validate(json.loads(Path(path).read_text(encoding="utf-8")))

    @field_validator("source")
    @classmethod
    def source_must_be_project_relative(cls, value: str) -> str:
        _validate_project_relative_path(value)
        return value

    @model_validator(mode="after")
    def scenes_must_be_unique_and_within_source(self) -> SceneIndex:
        scene_ids = [scene.scene_id for scene in self.scenes]
        if len(scene_ids) != len(set(scene_ids)):
            raise ValueError("scene_id values must be unique")
        for scene in self.scenes:
            if scene.end > self.source_duration:
                raise ValueError("scene ranges must be within source_duration")
        return self

    def scene_by_id(self, scene_id: str) -> Scene:
        for scene in self.scenes:
            if scene.scene_id == scene_id:
                return scene
        raise KeyError(f"Unknown scene_id: {scene_id}")


class PlanBeat(BaseModel):
    beat_id: str
    type: Literal["title", "source_clip", "end_card"]
    goal: str
    scene_id: str | None = None
    duration: float = Field(gt=0)
    narration: str | None = None
    onscreen_text: str | None = None

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

    @field_validator("rendered_path")
    @classmethod
    def rendered_path_must_be_project_relative(cls, value: str) -> str:
        _validate_project_relative_path(value)
        return value


class TextBlock(BaseBlock):
    background_asset: str
    text: str
    duration: float = Field(gt=0)
    fontfile: str

    @field_validator("background_asset", "fontfile")
    @classmethod
    def text_paths_must_be_project_relative(cls, value: str) -> str:
        _validate_project_relative_path(value)
        return value


class TitleBlock(TextBlock):
    type: Literal["title"]


class EndCardBlock(TextBlock):
    type: Literal["end_card"]


class SourceClipBlock(BaseBlock):
    type: Literal["source_clip"]
    source: str
    source_start: float = Field(ge=0)
    source_end: float = Field(gt=0)
    video_duration: float = Field(gt=0)
    tts_asset: str | None = None
    tts_duration: float | None = Field(default=None, ge=0)
    source_audio_volume: float = Field(default=0.15, ge=0, le=1)
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
    Union[TitleBlock, SourceClipBlock, EndCardBlock],
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

    @model_validator(mode="after")
    def approval_required_for_mvp(self) -> CriticSuggestion:
        if not self.requires_approval:
            raise ValueError("requires_approval must be true for MVP suggestions")
        if self.action == "replace_text" and not self.replacement_text:
            raise ValueError("replacement_text is required for replace_text")
        return self


class CriticSuggestions(BaseModel):
    project_id: str
    critic_scope: Literal["blind_manifest_only"]
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
