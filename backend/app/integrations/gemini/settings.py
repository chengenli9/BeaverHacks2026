"""Gemini API settings loaded from environment variables."""
import os

from dotenv import load_dotenv

load_dotenv()

# Required for live Gemini calls. Keep import-time loading permissive so
# offline tests and non-AI app routes can import without a local secret.
GEMINI_API_KEY: str = os.getenv("GEMINI_API_KEY", "")

# Model defaults (cheap by policy)
GEMINI_TEXT_MODEL: str = os.getenv("GEMINI_TEXT_MODEL", "gemini-3.1-flash-lite-preview")
GEMINI_TTS_MODEL: str = os.getenv("GEMINI_TTS_MODEL", "gemini-2.5-flash-preview-tts")
GEMINI_IMAGE_MODEL: str = os.getenv("GEMINI_IMAGE_MODEL", "gemini-2.5-flash-image")

# Feature flags
GEMINI_ENABLE_GROUNDING: bool = os.getenv("GEMINI_ENABLE_GROUNDING", "false").lower() == "true"
GEMINI_MAX_OUTPUT_TOKENS: int = int(os.getenv("GEMINI_MAX_OUTPUT_TOKENS", "4096"))

# Pro model names that must never be used by default
# don't want to go broke over gemini
_FORBIDDEN_DEFAULT_MODELS: frozenset[str] = frozenset(
    {
        "gemini-2.5-pro",
        "gemini-2.0-pro",
        "gemini-1.5-pro",
        "gemini-pro",
    }
)


def assert_not_pro(model: str) -> None:
    """Raise if a Pro model is accidentally passed in the default path."""
    for forbidden in _FORBIDDEN_DEFAULT_MODELS:
        if model.startswith(forbidden):
            raise ValueError(
                f"Pro model '{model}' is not allowed in the default path. "
                "Use a Flash or Flash-Lite model."
            )
