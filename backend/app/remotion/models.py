from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


RuntimeTemplate = Literal["hero-reveal", "split-panel", "stacked-pulse"]


class BackgroundRequirements(BaseModel):
    mode: Literal["local", "generated_image"]
    prompt: str | None = None


class GeneratedTextSceneSpec(BaseModel):
    version: int = 1
    block_type: Literal["title", "scene_card", "end_card"]
    text: str
    duration_seconds: float = Field(gt=0)
    runtime_template: RuntimeTemplate
    layout_preset: Literal["centered", "hero-left", "hero-right", "stacked"] = "centered"
    text_alignment: Literal["left", "center", "right"] = "center"
    font_family: str = "display-sans"
    font_variant: str = "bold"
    text_color: str = "#F9FAFB"
    accent_color: str = "#5B8CFF"
    background_mode: Literal["image", "color", "gradient", "image_tint"] = "color"
    background_color: str = "#111827"
    background_image_path: str | None = None
    animation_preset: Literal["fade-in", "slide-up", "typewriter"] = "fade-in"
    show_glass_panel: bool = True
    show_accent_bar: bool = True


class GeneratedTextSceneBundle(BaseModel):
    runtime_template: RuntimeTemplate
    scene_spec: GeneratedTextSceneSpec
    decorator_code: str | None = None
    background_requirements: BackgroundRequirements
