"""Voice archetypes configuration - Echo system."""

import json
import os
from typing import Any, Dict, Optional

# ---------------------------------------------------------------------------
# Text model configuration — read from environment variables.
#
# All LLM text-generation roles (voice analysis, chat, echo / trait /
# pattern analysis, image description) are configured entirely through .env.
# No models.json entry is required for these services.
# ---------------------------------------------------------------------------

# Shared provider endpoint and API key used by the PolyAgent text roles.
TEXT_API_ENDPOINT: str = os.getenv("TEXT_API_ENDPOINT", "")
TEXT_API_KEY: str = os.getenv("TEXT_API_KEY", "")

# Default model used as fallback for all text roles when no per-role override
# is set.
_TEXT_MODEL_DEFAULT: str = os.getenv(
    "INK_TEXT_MODEL_DEFAULT", "google/gemini-3-flash-preview"
)

VOICE_ANALYSIS_MODEL: str = os.getenv("INK_VOICE_ANALYSIS_MODEL", _TEXT_MODEL_DEFAULT)
VOICE_INSPIRATION_MODEL: str = os.getenv(
    "INK_VOICE_INSPIRATION_MODEL", _TEXT_MODEL_DEFAULT
)
VOICE_CHAT_MODEL: str = os.getenv("INK_VOICE_CHAT_MODEL", _TEXT_MODEL_DEFAULT)
ECHO_ANALYSIS_MODEL: str = os.getenv("INK_ECHO_ANALYSIS_MODEL", _TEXT_MODEL_DEFAULT)
TRAIT_ANALYSIS_MODEL: str = os.getenv("INK_TRAIT_ANALYSIS_MODEL", _TEXT_MODEL_DEFAULT)
PATTERN_ANALYSIS_MODEL: str = os.getenv(
    "INK_PATTERN_ANALYSIS_MODEL", _TEXT_MODEL_DEFAULT
)

# Image description uses the same API provider as image generation by default,
# but the model name can be overridden independently.
IMAGE_DESCRIPTION_MODEL: str = os.getenv(
    "INK_IMAGE_DESCRIPTION_MODEL", "anthropic/claude-haiku-4.5"
)

# ---------------------------------------------------------------------------
# Image generation model configuration — read from models.json.
#
# models.json retains only non-text (image generation) service configuration:
# the model entry, retry settings, and API endpoint/key for image calls.
# ---------------------------------------------------------------------------

CONFIG_PATH = os.path.join(os.path.dirname(__file__), "models.json")


def _load_models_config() -> Dict[str, Any]:
    """Load image-service configuration from models.json."""
    if not os.path.exists(CONFIG_PATH):
        raise RuntimeError(
            "models.json not found; copy backend/models.json.example and fill in your "
            "image-generation API credentials"
        )
    with open(CONFIG_PATH, "r", encoding="utf-8") as f:
        data = json.load(f)
    if not isinstance(data, dict):
        raise RuntimeError("models.json must contain a JSON object at the top level")
    return data


_CONFIG = _load_models_config()


def _resolve_image_generation_config() -> Dict[str, Any]:
    roles = _CONFIG.get("roles")
    if not isinstance(roles, dict):
        raise RuntimeError('models.json must define a "roles" object')
    image_gen_role = roles.get("image_generation")
    if not image_gen_role:
        raise RuntimeError(
            '"image_generation" role missing in models.json "roles"'
        )
    models = _CONFIG.get("models")
    if not isinstance(models, dict):
        raise RuntimeError('models.json must define a "models" object')
    entry = models.get(image_gen_role)
    if not isinstance(entry, dict):
        raise RuntimeError(
            f'image generation model "{image_gen_role}" not found under "models" in models.json'
        )
    return entry


_IMAGE_MODEL_CONFIG = _resolve_image_generation_config()

IMAGE_GENERATION_MODEL: str = _IMAGE_MODEL_CONFIG.get(
    "model", list(_CONFIG.get("roles", {}).values())[-1]
)
IMAGE_API_KEY: Optional[str] = _IMAGE_MODEL_CONFIG.get("api_key")
if not IMAGE_API_KEY:
    raise RuntimeError(
        f'api_key missing for image generation model in models.json'
    )

_IMAGE_API_SECTION = _CONFIG.get("image_api") or {}
IMAGE_API_ENDPOINT: Optional[str] = _IMAGE_MODEL_CONFIG.get(
    "endpoint"
) or _IMAGE_API_SECTION.get("endpoint")
if not IMAGE_API_ENDPOINT:
    raise RuntimeError(
        'endpoint missing for image generation model in models.json '
        'and no "image_api.endpoint" fallback provided'
    )

# Retry configuration for image generation
_IMAGE_RETRY = _CONFIG.get("image_retry") or {}
IMAGE_RETRY_MAX_ATTEMPTS: int = _IMAGE_RETRY.get("max_attempts", 3)
IMAGE_RETRY_BASE_TIMEOUT: int = _IMAGE_RETRY.get("base_timeout", 90)
IMAGE_RETRY_TIMEOUT_INCREMENT: int = _IMAGE_RETRY.get("timeout_increment", 30)
IMAGE_MAX_TOKENS: int = _IMAGE_RETRY.get("max_tokens", 1000)
IMAGE_DESCRIPTION_MAX_TOKENS: int = _IMAGE_RETRY.get("description_max_tokens", 500)
IMAGE_DESCRIPTION_TIMEOUT: int = _IMAGE_RETRY.get("description_timeout", 120)

# ---------------------------------------------------------------------------
# Prompt helpers and voice archetypes
# ---------------------------------------------------------------------------


def _load_prompt(filename):
    """Load prompt from prompts/ directory."""
    prompt_path = os.path.join(os.path.dirname(__file__), "prompts", filename)
    try:
        with open(prompt_path, "r", encoding="utf-8") as f:
            return f.read().strip()
    except FileNotFoundError:
        return ""


# Voice archetypes (Echo system - 5 Chinese voice personas)
VOICE_ARCHETYPES = {
    "holder": {
        "name": "接纳者 (The Holder)",
        "systemPrompt": _load_prompt("holder.md"),
        "icon": "heart",
        "color": "pink",
    },
    "starter": {
        "name": "启动者 (The Starter)",
        "systemPrompt": _load_prompt("starter.md"),
        "icon": "fist",
        "color": "yellow",
    },
    "mirror": {
        "name": "照镜者 (The Mirror)",
        "systemPrompt": _load_prompt("mirror.md"),
        "icon": "eye",
        "color": "green",
    },
    "weaver": {
        "name": "连接者 (The Weaver)",
        "systemPrompt": _load_prompt("weaver.md"),
        "icon": "compass",
        "color": "purple",
    },
    "absurdist": {
        "name": "幽默者 (The Absurdist)",
        "systemPrompt": _load_prompt("absurdist.md"),
        "icon": "masks",
        "color": "pink",
    },
}

# @@@ Analysis prompt for LLM
ANALYSIS_PROMPT_TEMPLATE = """You are analyzing internal dialogue using the voice system from Disco Elysium.

In Disco Elysium, thoughts manifest as distinct inner voices - each representing a cognitive skill with its own personality and perspective. These voices interrupt, comment on, and debate each other as the protagonist thinks.

Analyze this text and identify which voices are speaking:

"{text}"

Available voice archetypes:
{voice_list}

For each voice you detect:
1. Extract the EXACT phrase that triggered it (word-for-word from the text)
2. Choose the matching voice archetype
3. Write what this voice is saying (as if the voice itself is speaking)
4. Use the voice's designated icon and color

IMPORTANT:
- Maximum {max_voices} voices
- Only identify clearly present voices
- Phrase must be verbatim from text
- Each voice should be distinct
"""

