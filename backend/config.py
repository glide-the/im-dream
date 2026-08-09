"""Voice archetypes configuration - Echo system."""

import os

# Runtime model routing and credentials are intentionally absent here. Every
# inference entrypoint resolves an Admin-published alias through
# services.admin_gateway and has no direct Provider endpoint/key fallback.

# Retry configuration for image generation
IMAGE_RETRY_MAX_ATTEMPTS: int = int(os.getenv("INK_IMAGE_RETRY_MAX_ATTEMPTS", "3"))
IMAGE_RETRY_BASE_TIMEOUT: int = int(os.getenv("INK_IMAGE_RETRY_BASE_TIMEOUT", "90"))
IMAGE_RETRY_TIMEOUT_INCREMENT: int = int(
    os.getenv("INK_IMAGE_RETRY_TIMEOUT_INCREMENT", "30")
)
IMAGE_MAX_TOKENS: int = int(os.getenv("INK_IMAGE_MAX_TOKENS", "1000"))
IMAGE_DESCRIPTION_MAX_TOKENS: int = int(
    os.getenv("INK_IMAGE_DESCRIPTION_MAX_TOKENS", "500")
)
IMAGE_DESCRIPTION_TIMEOUT: int = int(
    os.getenv("INK_IMAGE_DESCRIPTION_TIMEOUT", "120")
)

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
