# [Sync] 2026-11-04: 生成固定播放问题，要求原问答answers；不播放返回declined，缺回答不产生播放请求。
# [Input] Opt-in platform tool descriptors and Agent-supplied audio metadata.
# [Output] Strict platform/audio inputs, AskUserQuestion fields and playback_requested/declined results.
# [Pos] Shared protocol; contains no player, file reads, network or approval store.
from __future__ import annotations

import json
from typing import Any, Literal
from urllib.parse import unquote

from pydantic import BaseModel, ConfigDict, Field, FiniteFloat, field_validator

MOBILE_CLOCK_AUDIO_TYPE = "mobile_clock_audio"
MOBILE_CLOCK_AUDIO_TOOL = "mcp__mobile_clock_audio__ask_user"
PlatformToolType = Literal["mobile_clock_audio"]
AUDIO_PLAYBACK_QUESTION = "是否在这台设备播放以下音频？"


def playback_questions() -> list[dict[str, Any]]:
    return [{"question": AUDIO_PLAYBACK_QUESTION, "header": "音频播放", "type": "radio",
             "required": True, "multiSelect": False, "options": [
                 {"label": "播放", "description": "按所示队列方式播放这些音频。"},
                 {"label": "不播放", "description": "保留角色或当前播放。"},
             ]}]


class PlatformToolDescriptor(BaseModel):
    """A client may select a backend-owned tool type, never its implementation."""

    model_config = ConfigDict(extra="forbid", strict=True)
    type: PlatformToolType


class MobileClockAudioItem(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    title: str = Field(min_length=1, description="音频标题")
    resource_uri: str = Field(
        pattern=r"^workspace://files/[^\s?#]+$",
        description="当前Thread工作区中已有音频的workspace://files/相对资源引用",
    )
    source_label: str | None = Field(default=None, min_length=1, description="音频来源摘要")
    duration_seconds: FiniteFloat | None = Field(default=None, gt=0, description="已知音频时长，单位秒；未知时省略")

    @field_validator("title", "source_label")
    @classmethod
    def nonempty_text(cls, value: str | None) -> str | None:
        if value is not None and not value.strip():
            raise ValueError("Audio metadata is empty")
        return value

    @field_validator("resource_uri")
    @classmethod
    def workspace_reference(cls, value: str) -> str:
        relative = value.removeprefix("workspace://files/")
        decoded = unquote(relative, errors="strict")
        # Allow encoded filenames while rejecting escaped path boundaries and traversal.
        if unquote(decoded) != decoded or decoded.count("/") != relative.count("/") or "\\" in decoded or "\x00" in decoded:
            raise ValueError("Audio resource reference is invalid")
        if decoded.startswith("/") or any(part in ("", ".", "..") for part in decoded.split("/")):
            raise ValueError("Audio resource must stay in the current workspace files")
        return value


class MobileClockAudioInput(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    items: list[MobileClockAudioItem] = Field(min_length=1, description="本次请求播放的音频列表")
    queue_mode: Literal["replace", "append"] = Field(default="replace", description="替换或追加当前播放队列")
    reason: str = Field(min_length=1, description="本次播放原因，展示于原工具确认区域")
    questions: list[dict[str, Any]] = Field(default_factory=playback_questions, description="运行时提供的AskUserQuestion问题与选项")
    answers: dict[str, str] | None = Field(default=None, description="运行时收集的用户回答")

    @field_validator("reason")
    @classmethod
    def nonempty_reason(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("Playback reason is empty")
        return value


def prepare_audio_question(arguments: dict | None) -> dict[str, Any]:
    """Rebuild the question and discard Agent-authored answers before asking."""
    if not isinstance(arguments, dict):
        raise ValueError("Audio tool input must be an object")
    request = MobileClockAudioInput.model_validate({key: value for key, value in arguments.items() if key not in {"questions", "answers"}})
    return request.model_dump(mode="json", exclude_none=True)


def handle_mobile_clock_audio(arguments: dict | None) -> str:
    """Return a playback request only for the answer collected by AskUserQuestion."""
    request = MobileClockAudioInput.model_validate(arguments)
    if request.questions != playback_questions():
        raise ValueError("Audio playback question does not match")
    if request.answers is None or set(request.answers) != {AUDIO_PLAYBACK_QUESTION}:
        raise ValueError("A user playback answer is required")
    choice = request.answers[AUDIO_PLAYBACK_QUESTION]
    if choice not in {"播放", "不播放"}:
        raise ValueError("Audio playback answer is invalid")
    return json.dumps(
        {"type": MOBILE_CLOCK_AUDIO_TYPE,
         "status": "playback_requested" if choice == "播放" else "declined",
         "choice": choice,
         **request.model_dump(mode="json", exclude_none=True, exclude={"questions", "answers"})},
        ensure_ascii=False, allow_nan=False,
    )
