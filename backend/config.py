# [Input] Environment-backed runtime policy values and repository prompt files.
# [Output] Central configuration for voice archetypes, screenplay Deck defaults,
#          and the default Claude plugin selected for newly created Decks.
# [Pos] backend configuration source of truth
# [Sync] 2026-08-14: define the screenplay-creation Deck template, retire legacy
#                    system Deck defaults, and select drama-forge v1.0.1 for new Decks.
# [Sync] 2026-08-31: remove retired daily-picture generation tuning.
# [Sync] 2026-09-19: add the music-creation team, arranger, lyricist, and exact plugin set to the code-owned registry.
"""Voice archetypes and product-default configuration."""

import os


def _csv_env(name: str, fallback: str) -> tuple[str, ...]:
    """Read an ordered, de-duplicated comma-separated policy list."""

    values: list[str] = []
    for raw in os.getenv(name, fallback).split(","):
        value = raw.strip()
        if value and value not in values:
            values.append(value)
    return tuple(values)


DEFAULT_SYSTEM_DECK_ID = os.getenv(
    "INK_DEFAULT_SYSTEM_DECK_ID",
    "screenplay_creation_deck",
).strip()
MUSIC_SYSTEM_DECK_ID = "music_creation_deck"
RETIRED_SYSTEM_DECK_IDS = _csv_env(
    "INK_RETIRED_SYSTEM_DECK_IDS",
    "introspection_deck,scholar_deck,philosophy_deck",
)
DEFAULT_DECK_CLAUDE_PLUGIN_PACKAGE_NAME = os.getenv(
    "INK_DEFAULT_DECK_CLAUDE_PLUGIN_PACKAGE_NAME",
    "drama-forge",
).strip()
DEFAULT_DECK_CLAUDE_PLUGIN_VERSION = os.getenv(
    "INK_DEFAULT_DECK_CLAUDE_PLUGIN_VERSION",
    "1.0.1",
).strip()

SCREENPLAY_DECK_TEMPLATE = {
    "id": DEFAULT_SYSTEM_DECK_ID,
    "name": "剧本创作团队",
    "name_zh": "剧本创作团队",
    "name_en": "Screenplay Creation Team",
    "description": "覆盖剧情、结构、人物、对白和连续性的剧本创作角色",
    "description_zh": "覆盖剧情、结构、人物、对白和连续性的剧本创作角色",
    "description_en": "Screenplay roles for story, structure, character, dialogue, and continuity",
    "icon": "masks",
    "color": "purple",
    "voices": (
        {
            "id": "screenplay_screenwriter",
            "name": "编剧",
            "name_zh": "编剧",
            "name_en": "Screenwriter",
            "system_prompt": "你是一名专业编剧。把创作目标发展为可拍摄的剧情、场景和行动，确保冲突清晰、选择具体，并尊重项目已经确定的世界观与人物事实。 be workflow option come from explicit scenario input.must convert AskUserQuestion data.",
            "icon": "masks",
            "color": "purple",
        },
        {
            "id": "screenplay_dramaturg",
            "name": "戏剧结构师",
            "name_zh": "戏剧结构师",
            "name_en": "Dramaturg",
            "system_prompt": "你是一名戏剧结构师。检查目标、阻力、节拍、转折、铺垫与回收，指出结构问题并给出最小、可执行的调整建议，不替用户擅自改写核心主题。 be workflow option come from explicit scenario input.must convert AskUserQuestion data.",
            "icon": "compass",
            "color": "blue",
        },
        {
            "id": "screenplay_character_designer",
            "name": "人物塑造师",
            "name_zh": "人物塑造师",
            "name_en": "Character Designer",
            "system_prompt": "你是一名人物塑造师。维护人物欲望、阻力、秘密、关系和弧光的一致性，让行动来自人物选择，并明确区分已确定事实与创作建议。 be workflow option come from explicit scenario input.must convert AskUserQuestion data.",
            "icon": "heart",
            "color": "pink",
        },
        {
            "id": "screenplay_dialogue_editor",
            "name": "对白编辑",
            "name_zh": "对白编辑",
            "name_en": "Dialogue Editor",
            "system_prompt": "你是一名对白编辑。改善潜台词、人物声线、节奏和可表演性，删去解释性重复，同时保持剧情事实、人物身份和场景目的不变。 be workflow option come from explicit scenario input.must convert AskUserQuestion data.",
            "icon": "masks",
            "color": "green",
        },
        {
            "id": "screenplay_continuity_editor",
            "name": "连续性审校",
            "name_zh": "连续性审校",
            "name_en": "Continuity Editor",
            "system_prompt": "你是一名连续性审校。检查时间、空间、道具、人物状态、信息获知顺序和前后因果，列出可定位的矛盾及最小修正，不制造新的权威事实。 be workflow option come from explicit scenario input.must convert AskUserQuestion data.",
            "icon": "eye",
            "color": "yellow",
        },
    ),
}

MUSIC_DECK_TEMPLATE = {
    "id": MUSIC_SYSTEM_DECK_ID,
    "name": "音乐创作",
    "name_zh": None,
    "name_en": None,
    "description": "Describe your deck here",
    "description_zh": None,
    "description_en": None,
    "icon": "brain",
    "color": "blue",
    "voices": (
        {
            "id": "music_style_lyrics_creator",
            "name": "风格和歌词生成",
            "name_zh": None,
            "name_en": None,
            "system_prompt": "You are a helpful assistant.",
            "icon": "brain",
            "color": "blue",
        },
        {
            "id": "music_arranger",
            "name": "编曲师",
            "name_zh": "编曲师",
            "name_en": "Music Arranger",
            "system_prompt": "你是一名专业编曲师。优先使用 music-composition 插件中的 mc-workflow 及相关 Skills，把创作目标整理为可执行的 ARR-SPEC，明确调性、速度、曲式、和声、配器、能量曲线、演唱与混音意图；与作词师的 LYR-SPEC 及 YuE2 生成环节保持段落、拍数、重音和交付格式一致。区分用户已确定的事实与编曲建议，不复制受保护作品的旋律或编配。",
            "icon": "music",
            "color": "purple",
        },
        {
            "id": "music_lyricist",
            "name": "作词师",
            "name_zh": "作词师",
            "name_en": "Lyricist",
            "system_prompt": "你是一名专业作词师。优先使用 lyric-writing 插件中的 lw-workflow 及相关 Skills，把创作意图整理为可执行的 LYR-SPEC，明确主题、叙述对象、时刻、意象、段落、行长、重音、押韵和语言层检查；与编曲师的 ARR-SPEC 保持段落、拍数、音节和重音接口一致，并为 YuE2 生成输出完整歌词。区分用户已确定的事实与创作建议，不仿写或复制受保护歌词。",
            "icon": "pen-tool",
            "color": "pink",
        },
    ),
    "plugins": (
        {
            "package_name": "yue2",
            "marketplace": "yue2-skills",
            "resolved_version": "0.4.0",
        },
        {
            "package_name": "music-composition",
            "marketplace": "music-composition-skills",
            "resolved_version": "1.0.0",
        },
        {
            "package_name": "lyric-writing",
            "marketplace": "lyric-writing-skills",
            "resolved_version": "1.0.0",
        },
    ),
}

SYSTEM_DECK_TEMPLATES = (
    SCREENPLAY_DECK_TEMPLATE,
    MUSIC_DECK_TEMPLATE,
)

# Runtime model routing and credentials are intentionally absent here. Every
# inference entrypoint resolves an Admin-published alias through
# services.admin_gateway and has no direct Provider endpoint/key fallback.

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
