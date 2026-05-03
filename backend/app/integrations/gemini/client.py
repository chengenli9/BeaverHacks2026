"""Low-level Gemini API wrapper.

Handles authentication, structured-JSON requests, TTS, and image generation.
Never logs the API key. Logs model name and elapsed time.
"""
import io
import json
import time
import wave
from pathlib import Path
from typing import Any

from google import genai
from google.genai import types

from .settings import (
    GEMINI_API_KEY,
    GEMINI_IMAGE_MODEL,
    GEMINI_MAX_OUTPUT_TOKENS,
    GEMINI_TEXT_MODEL,
    GEMINI_TTS_MODEL,
    assert_not_pro,
)

_client: genai.Client | None = None


def get_client() -> genai.Client:
    """Return the module-level Gemini client, creating it on first call."""
    global _client
    if _client is None:
        if not GEMINI_API_KEY:
            raise RuntimeError("GEMINI_API_KEY is required for live Gemini calls")
        _client = genai.Client(api_key=GEMINI_API_KEY)
    return _client


# ---------------------------------------------------------------------------
# Text / structured-JSON
# ---------------------------------------------------------------------------


def complete_json(
    prompt: str,
    *,
    system: str | None = None,
    model: str | None = None,
    schema: dict | None = None,
) -> tuple[Any, dict]:
    """Call Gemini for structured JSON output.

    Args:
        prompt: User-facing instruction text.
        system: Optional system / persona text prepended to the prompt.
        model: Override model. Defaults to GEMINI_TEXT_MODEL.

    Returns:
        (parsed_json, usage_metadata_dict)

    Raises:
        ValueError: If the response cannot be parsed as JSON or a Pro model
            is requested.
    """
    target_model = model or GEMINI_TEXT_MODEL
    assert_not_pro(target_model)

    client = get_client()
    full_prompt = f"{system}\n\n{prompt}".strip() if system else prompt

    t0 = time.monotonic()
    config_kwargs = {
        "response_mime_type": "application/json",
        "max_output_tokens": GEMINI_MAX_OUTPUT_TOKENS,
    }
    if schema is not None:
        config_kwargs["response_json_schema"] = schema

    response = client.models.generate_content(
        model=target_model,
        contents=full_prompt,
        config=types.GenerateContentConfig(**config_kwargs),
    )
    elapsed_ms = int((time.monotonic() - t0) * 1000)

    parsed = json.loads(response.text)
    usage = _extract_usage(response, target_model, elapsed_ms)
    return parsed, usage


def complete_json_with_file(
    prompt: str,
    file_path: Path,
    *,
    mime_type: str | None = None,
    system: str | None = None,
    model: str | None = None,
    schema: dict | None = None,
) -> tuple[Any, dict]:
    """Call Gemini with an uploaded file plus a text prompt for structured JSON.

    The file is uploaded via the Files API and referenced by URI in the
    request so large video files are handled server-side.
    """
    target_model = model or GEMINI_TEXT_MODEL
    assert_not_pro(target_model)

    client = get_client()
    t0 = time.monotonic()

    uploaded = client.files.upload(
        file=str(file_path),
        config=types.UploadFileConfig(mime_type=mime_type) if mime_type else None,
    )

    # Poll until the file is ACTIVE (uploads are async for large files)
    while uploaded.state.name == "PROCESSING":
        time.sleep(2)
        uploaded = client.files.get(name=uploaded.name)

    if uploaded.state.name != "ACTIVE":
        raise RuntimeError(
            f"File upload failed — final state: {uploaded.state.name}. "
            "The file may be too large or an unsupported format."
        )

    full_prompt = f"{system}\n\n{prompt}".strip() if system else prompt
    contents = [
        types.Content(
            role="user",
            parts=[
                types.Part(
                    file_data=types.FileData(
                        file_uri=uploaded.uri,
                        mime_type=uploaded.mime_type,
                    )
                ),
                types.Part(text=full_prompt),
            ],
        )
    ]

    config_kwargs = {
        "response_mime_type": "application/json",
        "max_output_tokens": GEMINI_MAX_OUTPUT_TOKENS,
    }
    if schema is not None:
        config_kwargs["response_json_schema"] = schema

    response = client.models.generate_content(
        model=target_model,
        contents=contents,
        config=types.GenerateContentConfig(**config_kwargs),
    )
    elapsed_ms = int((time.monotonic() - t0) * 1000)

    parsed = json.loads(response.text)
    usage = _extract_usage(response, target_model, elapsed_ms)
    return parsed, usage


# ---------------------------------------------------------------------------
# TTS
# ---------------------------------------------------------------------------


def generate_audio(text: str, *, voice: str = "Aoede", model: str | None = None) -> tuple[bytes, dict]:
    """Generate TTS audio from text.

    Returns:
        (wav_bytes, usage_metadata_dict) — wav_bytes is a valid WAV file at
        24 000 Hz, 16-bit, mono.
    """
    target_model = model or GEMINI_TTS_MODEL
    assert_not_pro(target_model)

    client = get_client()
    t0 = time.monotonic()

    response = client.models.generate_content(
        model=target_model,
        contents=text,
        config=types.GenerateContentConfig(
            response_modalities=["AUDIO"],
            speech_config=types.SpeechConfig(
                voice_config=types.VoiceConfig(
                    prebuilt_voice_config=types.PrebuiltVoiceConfig(voice_name=voice)
                )
            ),
        ),
    )
    elapsed_ms = int((time.monotonic() - t0) * 1000)

    pcm_data = b""
    for part in response.candidates[0].content.parts:
        if part.inline_data and part.inline_data.data:
            pcm_data = part.inline_data.data
            break

    wav_bytes = _pcm_to_wav(pcm_data)
    usage = _extract_usage(response, target_model, elapsed_ms)
    return wav_bytes, usage


def measure_wav_duration(wav_path: Path) -> float:
    """Return the duration in seconds of a WAV file."""
    with wave.open(str(wav_path), "rb") as wf:
        frames = wf.getnframes()
        rate = wf.getframerate()
        return frames / float(rate)


# ---------------------------------------------------------------------------
# Image generation
# ---------------------------------------------------------------------------


def generate_image(
    prompt: str,
    *,
    model: str | None = None,
    allow_fallback: bool = False,
) -> tuple[bytes, dict]:
    """Generate a textless background PNG image.

    Returns:
        (png_bytes, usage_metadata_dict)
    """
    target_model = model or GEMINI_IMAGE_MODEL
    assert_not_pro(target_model)

    client = get_client()
    t0 = time.monotonic()
    elapsed_ms = 0

    try:
        response = client.models.generate_images(
            model=target_model,
            prompt=prompt,
            config=types.GenerateImagesConfig(
                number_of_images=1,
                output_mime_type="image/png",
            ),
        )
        elapsed_ms = int((time.monotonic() - t0) * 1000)

        png_bytes = b""
        if getattr(response, "generated_images", None):
            first = response.generated_images[0]
            image = getattr(first, "image", None)
            png_bytes = getattr(image, "image_bytes", b"") if image else b""
        if not png_bytes and getattr(response, "images", None):
            first_image = response.images[0]
            png_bytes = getattr(first_image, "image_bytes", b"")
        if not png_bytes:
            raise RuntimeError("No image data in response")

        usage = _extract_usage(response, target_model, elapsed_ms)
        return png_bytes, usage

    except Exception as exc:  # noqa: BLE001
        elapsed_ms = int((time.monotonic() - t0) * 1000)
        if not allow_fallback:
            raise RuntimeError(
                f"Image generation failed for model '{target_model}': {exc}"
            ) from exc
        png_bytes = _placeholder_png()
        usage = {
            "elapsed_ms": elapsed_ms,
            "model": target_model,
            "input_token_count": 0,
            "output_token_count": 0,
            "error": "image_generation_fallback",
            "error_detail": str(exc),
        }
        return png_bytes, usage


# ---------------------------------------------------------------------------
# Private helpers
# ---------------------------------------------------------------------------


def _pcm_to_wav(
    pcm_data: bytes,
    sample_rate: int = 24000,
    channels: int = 1,
    sample_width: int = 2,
) -> bytes:
    """Wrap raw PCM bytes in a RIFF WAV container."""
    buf = io.BytesIO()
    with wave.open(buf, "wb") as wf:
        wf.setnchannels(channels)
        wf.setsampwidth(sample_width)
        wf.setframerate(sample_rate)
        wf.writeframes(pcm_data)
    return buf.getvalue()


def _placeholder_png(width: int = 1920, height: int = 1080) -> bytes:
    """Return a solid dark-grey 1920×1080 PNG as a fallback background."""
    from PIL import Image  # imported lazily to keep startup fast

    img = Image.new("RGB", (width, height), color=(30, 30, 35))
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


def _extract_usage(response: Any, model: str, elapsed_ms: int) -> dict:
    meta = getattr(response, "usage_metadata", None)
    return {
        "elapsed_ms": elapsed_ms,
        "model": model,
        "input_token_count": getattr(meta, "prompt_token_count", 0) if meta else 0,
        "output_token_count": getattr(meta, "candidates_token_count", 0) if meta else 0,
    }
