"""Shared canonical project guidance for Dream Agent turns."""

from __future__ import annotations


STORY_WORKSPACE_CANONICAL_PROJECT_INSTRUCTION = (
    "先完成 drama-init 的项目初始化语义，再推进任何 Episode 工作。\n"
    "规范项目身份要求：先创建 stories/<project_slug>/project.yaml；"
    "project_slug 必须与 project_id 完全相同，并且两者都必须匹配 "
    "^[a-z0-9]+(?:-[a-z0-9]+)*$。\n"
    "project_name 只用于显示，禁止把 project_name 当作目录或 source path 的项目段。\n"
    "规范项目身份成立后，才能写入 storyboard canonical 文件。"
)

STORY_WORKSPACE_CANONICAL_PROJECT_PRIVATE_WRITER_SUFFIX = (
    "规范项目身份成立后，才能调用 "
    "mcp__story_workspace__write_dream_stage(storyboards)；首次调用 "
    "mcp__story_workspace__bind_first_episode 必须传 "
    "expectedBindingRevision=0。"
)

STORY_WORKSPACE_CANONICAL_PROJECT_RECOVERY_INSTRUCTION = (
    "若尚无规范项目，先按上述 drama-init 语义完成初始化。"
    "仅当工作区恰有一个非规范 story 目录，其中 project.yaml 给出唯一合法 ASCII "
    "project_id，目标 stories/<project_id> 不存在，且相关目录不存在符号链接时，"
    "才可保留内容并将该目录整理为 stories/<project_id>。"
    "整理后按最新文件事实重同步 storyboards stage。"
    "证据不唯一、目标冲突或发现符号链接时不得移动，说明仍需确认。"
)


__all__ = [
    "STORY_WORKSPACE_CANONICAL_PROJECT_INSTRUCTION",
    "STORY_WORKSPACE_CANONICAL_PROJECT_PRIVATE_WRITER_SUFFIX",
    "STORY_WORKSPACE_CANONICAL_PROJECT_RECOVERY_INSTRUCTION",
]
