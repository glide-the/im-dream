"""Shared canonical project guidance for Dream Agent turns."""

from __future__ import annotations

import hashlib


def story_workspace_canonical_project_fallback_slug(project_name: str) -> str:
    """Return the byte-exact fallback slug without Unicode normalization."""

    digest = hashlib.sha256(project_name.encode("utf-8")).hexdigest()
    return f"proj-{digest[:8]}"


_FALLBACK_EXAMPLE_PROJECT_NAME = "郑州暴雨夜"
_FALLBACK_EXAMPLE_PROJECT_SLUG = story_workspace_canonical_project_fallback_slug(
    _FALLBACK_EXAMPLE_PROJECT_NAME
)


STORY_WORKSPACE_CANONICAL_PROJECT_INSTRUCTION = (
    "如果当前 server-trusted Dream 消息已经明确给出分配好的 project_id/project_slug，"
    "必须原样使用，禁止重新计算或替换；只有未给出分配值时，才先完成 drama-init "
    "的项目初始化语义，再推进任何 Episode 工作。\n"
    "规范项目身份要求：先创建 stories/<project_slug>/project.yaml；"
    "project_slug 必须与 project_id 完全相同，并且两者都必须匹配 "
    "^[a-z0-9]+(?:-[a-z0-9]+)*$。\n"
    "project_name 只用于显示，禁止把 project_name 当作目录或 source path 的项目段；"
    "全中文 project_name 不得直接成为物理项目身份；没有可保留的 ASCII 片段时，"
    "fallback 算法固定为 proj- + "
    "sha256(原始 project_name 的 UTF-8 bytes).hexdigest()[:8]。"
    "直接编码原始 project_name，不 trim、casefold，也不对 project_name 做 "
    "Unicode normalization；不同原始 Unicode code-point/byte 序列可以得到不同标识。"
    f"示例：{_FALLBACK_EXAMPLE_PROJECT_NAME} → {_FALLBACK_EXAMPLE_PROJECT_SLUG}。"
    "将该结果同时作为 project_id 与 project_slug。\n"
    "规范项目身份成立后，才能写入 storyboard canonical 文件。"
)

STORY_WORKSPACE_CANONICAL_PROJECT_PRIVATE_WRITER_SUFFIX = (
    "规范项目身份成立后，宿主会在主 Agent turn 成功结束时自动同步工作台文件。"
    "Story Workspace MCP 写工具仅用于主动即时预览或显式修复，不是同步成功的前置条件；"
    "若当前业务确需首次绑定 Episode，mcp__story_workspace__bind_first_episode "
    "仍必须传 expectedBindingRevision=0。"
)

STORY_WORKSPACE_RUN_ISOLATED_LAYOUT_INSTRUCTION = """# Run-isolated layout

```text
<shared-root>/<server-derived-thread-key>/.dream/runtime/runs/<run-id>/
  episode.json
  episode-workflow.json
  artifact/
    stories/<source-project-id>/
      project.yaml
      episodes/<EPxx>/
        script.md
        episode-outline.md
        storyboard.yaml
        review-report.md
```

`<run-id>` is the server-trusted workflow_run_id in this Dream context. The
server derives `<shared-root>` and `<server-derived-thread-key>`; never infer,
replace or accept either from browser/user text. The host owns `.dream/**`
publication and automatically synchronizes completed canonical workbench
files after a successful root turn. Generic file or Bash tools must never
write this private layout."""

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
    "STORY_WORKSPACE_RUN_ISOLATED_LAYOUT_INSTRUCTION",
    "story_workspace_canonical_project_fallback_slug",
]
