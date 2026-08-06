"""Reviewed drama-forge Episode workflow guidance for trusted Dream turns."""

from __future__ import annotations

from dataclasses import dataclass
import json
import re
from typing import Mapping

try:
    from story_workspace.contracts import (
        StoryWorkspaceDreamRunContext,
        StoryWorkspaceEpisodeAction,
    )
except ModuleNotFoundError:  # Support repository-root package imports.
    from backend.story_workspace.contracts import (
        StoryWorkspaceDreamRunContext,
        StoryWorkspaceEpisodeAction,
    )


_REVISION = re.compile(r"^sha256:[0-9a-f]{64}$")
_EPISODE_UID = re.compile(r"^[0-9a-f]{32}$")


@dataclass(frozen=True)
class StoryWorkspaceEpisodeVendorStep:
    """Server-private README evidence and the reviewed product boundary."""

    ordinal: int
    evidence: str
    action: StoryWorkspaceEpisodeAction | None
    boundary: str


@dataclass(frozen=True)
class StoryWorkspaceEpisodeWorkflowEntry:
    """One public dependency entry rendered from the reviewed vendor flow."""

    ordinal: int
    action: StoryWorkspaceEpisodeAction
    display_command: str
    prerequisites: str
    outputs: str
    approval_boundary: str
    completion_fact: str

    @property
    def public_entry(self) -> str:
        return (
            f"步骤 {self.ordinal}｜{self.display_command}｜"
            f"前置：{self.prerequisites}｜产物：{self.outputs}｜"
            f"边界：{self.approval_boundary}｜完成事实：{self.completion_fact}"
        )


_VENDOR_FIRST_EPISODE_FLOW = (
    StoryWorkspaceEpisodeVendorStep(1, "/drama-init", None, "initial_creation"),
    StoryWorkspaceEpisodeVendorStep(
        2,
        "/drama-plan",
        StoryWorkspaceEpisodeAction.PLAN_EPISODE,
        "episode_execution",
    ),
    StoryWorkspaceEpisodeVendorStep(
        3,
        "/drama-script (EP01)",
        StoryWorkspaceEpisodeAction.WRITE_SCRIPT,
        "episode_execution",
    ),
    StoryWorkspaceEpisodeVendorStep(
        4,
        "script-reviewer 审查",
        StoryWorkspaceEpisodeAction.REVIEW_SCRIPT,
        "episode_execution",
    ),
    StoryWorkspaceEpisodeVendorStep(
        5,
        "/drama-asset",
        StoryWorkspaceEpisodeAction.REFRESH_ASSETS,
        "episode_execution",
    ),
    StoryWorkspaceEpisodeVendorStep(
        6,
        "/drama-storyboard (EP01)",
        StoryWorkspaceEpisodeAction.REGENERATE_STORYBOARD,
        "episode_execution",
    ),
    StoryWorkspaceEpisodeVendorStep(
        7,
        "/drama-prompt (EP01)",
        StoryWorkspaceEpisodeAction.GENERATE_PROMPTS,
        "episode_execution",
    ),
    StoryWorkspaceEpisodeVendorStep(
        8,
        "[审查报告: APPROVED]",
        StoryWorkspaceEpisodeAction.REVIEW_FULL_CHAIN,
        "episode_execution",
    ),
    StoryWorkspaceEpisodeVendorStep(
        9,
        "validate_commit.sh",
        StoryWorkspaceEpisodeAction.VALIDATE_EPISODE,
        "episode_execution",
    ),
    StoryWorkspaceEpisodeVendorStep(
        10,
        "/drama-render + /drama-voice",
        StoryWorkspaceEpisodeAction.PREPARE_RENDER_GUIDE,
        "render_guide_only",
    ),
    StoryWorkspaceEpisodeVendorStep(11, "/drama-edit", None, "out_of_scope"),
    StoryWorkspaceEpisodeVendorStep(12, "/drama-promote", None, "out_of_scope"),
)


_WORKFLOW_ENTRY_DETAILS: dict[
    StoryWorkspaceEpisodeAction,
    tuple[str, str, str, str],
] = {
    StoryWorkspaceEpisodeAction.PLAN_EPISODE: (
        "规范项目身份与 EP01 关联已成立",
        "episode-outline.md",
        "outline 是故事线 owner；本轮只规划第一集",
        "重新读取规范 outline 后由服务端文件事实确认",
    ),
    StoryWorkspaceEpisodeAction.WRITE_SCRIPT: (
        "当前 episode-outline.md",
        "script.md 与同轮 script-reviewer 审查结果",
        "drama-script 内置 reviewer 必须完成五维度审查",
        "重新读取规范剧本与审查报告后确认",
    ),
    StoryWorkspaceEpisodeAction.REVIEW_SCRIPT: (
        "当前 script.md revision 缺少有效 APPROVED 审查",
        "当前 script.md 对应的 review-report.md",
        "script-reviewer 五维度审查；不是 slash command",
        "报告必须引用当前剧本事实；已有当前 APPROVED 报告时跳过",
    ),
    StoryWorkspaceEpisodeAction.REFRESH_ASSETS: (
        "当前剧本与有效剧本审查",
        "与剧本一致的角色和场景资产",
        "只刷新本集依赖资产，不改写剧本 owner",
        "规范资产核验与服务端完成事实",
    ),
    StoryWorkspaceEpisodeAction.REGENERATE_STORYBOARD: (
        "当前剧本、审查与资产完成事实",
        "storyboard.yaml",
        "镜头结构由 storyboard owner 持有",
        "重新读取规范分镜与服务端完成事实",
    ),
    StoryWorkspaceEpisodeAction.GENERATE_PROMPTS: (
        "当前 storyboard.yaml",
        "prompts/ 中与 shot 显式关联的提示词",
        "缺失关联必须显式保留，不按数组位置猜测",
        "重新读取规范提示词与服务端完成事实",
    ),
    StoryWorkspaceEpisodeAction.REVIEW_FULL_CHAIN: (
        "outline、script、storyboard 与 prompts 当前且可关联",
        "full-chain review-report.md",
        "审查只评价当前完整链路，不接管内容 owner",
        "APPROVED 报告与服务端完成事实",
    ),
    StoryWorkspaceEpisodeAction.VALIDATE_EPISODE: (
        "当前 full-chain APPROVED 审查",
        "完整第一集产物校验结果",
        "仅校验和提交规范产物，不自动进入渲染",
        "校验成功与服务端完成事实",
    ),
    StoryWorkspaceEpisodeAction.PREPARE_RENDER_GUIDE: (
        "完整产物校验已完成",
        "renders/ 与 voice/render 执行指引",
        "本期只准备渲染与配音指引，不进入视频剪辑",
        "规范 render 事实与服务端完成事实",
    ),
}


def story_workspace_episode_vendor_workflow(
) -> tuple[StoryWorkspaceEpisodeVendorStep, ...]:
    """Return the reviewed README evidence mapping used by resolver tests."""

    return _VENDOR_FIRST_EPISODE_FLOW


def story_workspace_episode_workflow_entries(
) -> tuple[StoryWorkspaceEpisodeWorkflowEntry, ...]:
    """Build steps 2-10 from the same evidence owner as next-action ordering."""

    entries: list[StoryWorkspaceEpisodeWorkflowEntry] = []
    for step in _VENDOR_FIRST_EPISODE_FLOW:
        if step.action is None or not 2 <= step.ordinal <= 10:
            continue
        prerequisites, outputs, approval_boundary, completion_fact = (
            _WORKFLOW_ENTRY_DETAILS[step.action]
        )
        entries.append(
            StoryWorkspaceEpisodeWorkflowEntry(
                ordinal=step.ordinal,
                action=step.action,
                display_command=(
                    "script-reviewer 五维度审查（/drama-script 内置 required review Agent，"
                    "不是 slash command）"
                    if step.action is StoryWorkspaceEpisodeAction.REVIEW_SCRIPT
                    else (
                        "完整链路审查（目标：[审查报告: APPROVED]）"
                        if step.action
                        is StoryWorkspaceEpisodeAction.REVIEW_FULL_CHAIN
                        else (
                            "完整产物校验（vendor validate_commit.sh / commit）"
                            if step.action
                            is StoryWorkspaceEpisodeAction.VALIDATE_EPISODE
                            else step.evidence
                        )
                    )
                ),
                prerequisites=prerequisites,
                outputs=outputs,
                approval_boundary=approval_boundary,
                completion_fact=completion_fact,
            )
        )
    return tuple(entries)


def story_workspace_episode_workflow_guidance() -> str:
    """Render the public dependency template without private handshake values."""

    lines = [
        "第一集典型工作流（依赖指导，不是自动执行清单）：",
        *(
            entry.public_entry
            for entry in story_workspace_episode_workflow_entries()
        ),
        "步骤 11—12 不在本期范围；不得自动执行 /drama-edit 或 /drama-promote。",
        "每轮完成状态只由服务端重新读取规范产物与受控完成事实判定；"
        "Dream Agent 消息、工具许可或本轮处理结束都不等于产物完成。",
    ]
    return "\n".join(lines)


def story_workspace_private_episode_completion_guidance(
    context: StoryWorkspaceDreamRunContext,
    provenance: Mapping[str, object] | None,
) -> str | None:
    """Render completion guidance only for a complete server-owned action claim."""

    if not isinstance(provenance, Mapping) or set(provenance) != {
        "schema",
        "action",
        "episode_uid",
        "input_revision",
        "expected_facts_revision",
        "expected_manifest_revision",
        "expected_workflow_revision",
    }:
        return None
    try:
        action = StoryWorkspaceEpisodeAction(provenance.get("action"))
    except (TypeError, ValueError):
        return None
    episode_uid = provenance.get("episode_uid")
    input_revision = provenance.get("input_revision")
    facts_revision = provenance.get("expected_facts_revision")
    manifest_revision = provenance.get("expected_manifest_revision")
    workflow_revision = provenance.get("expected_workflow_revision")
    if (
        provenance.get("schema") != "story-workspace-episode-action/v1"
        or action is StoryWorkspaceEpisodeAction.NONE_IN_SCOPE
        or not isinstance(episode_uid, str)
        or _EPISODE_UID.fullmatch(episode_uid) is None
        or not isinstance(input_revision, str)
        or _REVISION.fullmatch(input_revision) is None
        or not isinstance(facts_revision, int)
        or isinstance(facts_revision, bool)
        or facts_revision < 0
        or not isinstance(manifest_revision, str)
        or _REVISION.fullmatch(manifest_revision) is None
        or not isinstance(workflow_revision, str)
        or _REVISION.fullmatch(workflow_revision) is None
    ):
        return None
    call = json.dumps(
        {"workflowRunId": context.workflow_run_id},
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    )
    return (
        "<story_workspace_episode_action_private>\n"
        f"当前 server-owned Episode action 是 {action.value}。"
        "只执行这个 action，不得继续后续步骤。\n"
        "完成创作后，重新读取并核验本轮规范产物。只有核验通过，才调用 "
        "mcp__story_workspace__record_episode_workflow_completion，参数必须为 "
        f"{call}。主机将重新校验当前消息 claim、action、Episode authority、"
        "current action input 与 workflow fact revision；"
        "不要猜测或补充版本参数。\n"
        "无论成功或 fail closed 都立即停止，等待服务端重新计算 nextAction。\n"
        "</story_workspace_episode_action_private>"
    )


__all__ = [
    "StoryWorkspaceEpisodeVendorStep",
    "StoryWorkspaceEpisodeWorkflowEntry",
    "story_workspace_episode_vendor_workflow",
    "story_workspace_episode_workflow_entries",
    "story_workspace_episode_workflow_guidance",
    "story_workspace_private_episode_completion_guidance",
]
