# 2026-08-04 `.dream` 协议与 Dream 业务交互：任务二用户审阅修订实施记录

> **任务**：任务二用户审阅修订
> **日期**：2026-08-04
> **状态**：设计完成，独立评审通过；等待人工审阅后再进入任务三
> **代码变更**：无

## 1. 用户最终裁决

现行 Dream 主生命周期只有一条：

```text
Agent 产出 → 页面渲染 → 用户修改并确认 → 同一 Chat Agent 后续执行
```

本轮据此完成三项收口：

1. 所有 Dream 内容由同一 Chat Agent 通过会话工作空间文件产出；
2. Agent 在人物、场景、分镜 canonical 文件完成后，更新 `.dream/runtime` 对应 stage 描述，使前端显示对应页面；
3. 用户只修改内容并对整份 Dream 执行一次“确认并继续”；确认回到发起 Dream 的原 Chat thread，由同一 Agent 写入修改并继续。

当前业务稿没有逐项审批、否定式处置、多分支恢复、内容归档或确认后的第二次确认。

## 2. 文件协议裁决

### 2.1 静态启动层

- `.dream/README.md` 与 `.dream/workspace.json` 继续由 packer 在首个 agent turn 物理映射；
- `workspace.json` 保持 `dream-surface/v1` 和 `{deck_id, plugins[], entry_route}`；
- 静态层继续受 digest、冻结只校验与原子 temp-dir + rename 约束；
- run 级字段不写入 `workspace.json`。

### 2.2 Agent 运行内容层

新增目标目录：

```text
.dream/runtime/runs/<workflow_run_id>/
├── run.json
└── stages/
    ├── characters.json
    ├── scenes.json
    └── storyboards.json
```

- `run.json` 承载 `workflow_run_id`、thread、运行来源五字段、`projection_entry`、required stages 与 revision；
- stage 文件使用 `dream-stage/v1`，携带 revision、source files 与页面元信息；
- 实际写文件者是同一 Chat Agent，通过目标 helper `StoryWorkspaceDreamFileWriter` 写 `.dream/runtime/**`；
- 静态启动层仍禁止 Agent 修改；
- stage 文件存在且 schema 有效即对应模块可渲染，不增加额外业务状态机。

### 2.3 上游路径复核

独立评审发现首稿把分镜来源误写为 `.drama/checks/`。本轮已按 vendor 实际合同修正：

- 分镜唯一源是 `stories/<project>/episodes/EP??/storyboard.yaml`（`vendor/drama-forge/drama-forge/references/author_glossary.json:230-237`）；
- `.md` 只是投影副本，YAML 是唯一源（同文件 `:290`）；
- 内部运行的 `artifacts/` 与 `reports/` 位于 `.dramaforge/runs/<internal_run_id>/`（`vendor/drama-forge/drama-forge/docs/season-production.md:118-127`）；
- 运行报告只可作为 stage 的可选 source refs，不替代 storyboard YAML，也不阻塞 Outline 页面出现。

## 3. 页面与业务交互

### 3.1 确认前三栏

- 左：Assets / Outline 模块与 stage 文件到达状态；
- 中：人物、场景、故事线、叙事点和分镜摘要；
- 右：当前内容 Detail Editor；
- 底部：跨页面的唯一“确认并继续”。

右栏不再是逐项审批面板。

### 3.2 确认后协作执行页

对齐 Dreem 调研 PDF 第 3～8 页：

1. 第一层是 Assets / Outline 索引与叙事执行主工作面；
2. 第二层是选中叙事点或分镜摘要后的聚焦上下文；
3. 页面持续显示 Agent 工作空间写入与 revision 更新；
4. 不复制视频、上传、播放器、外部模型或黑底画布。

视觉遵循 UI Design v2 第 4～5 页：Warm Canvas、Paper Cream、Action Brown、少面板、多留白、轻分隔和无卡片。

## 4. 业务时序产出

新增 `design_007`，包含：

- 四阶段主业务时序；
- Agent canonical 文件 → `.dream` stage → 页面出现时序；
- Assets / Outline → 故事线 → 叙事点 → 聚焦上下文导航时序；
- 用户本地修改 → 单次确认 → 隐藏消息注入原 thread → 同一 Agent 继续时序。

## 5. 文档变更清单

| 文件 | 说明 |
|---|---|
| `docs/architecture/术语表.md` | 新增静态启动层、Agent 运行内容层、stage、writer 与单次确认术语；标注实现状态 |
| `docs/design/story-workspace/design_006_dream-protocol-dir-mapping.md` | 重写为 `.dream` 唯一文件协议 owner，补 run/stage schema、三个生成阶段写入时点、确认合同和一致性边界 |
| `docs/design/story-workspace/design_007_dream-business-module-interaction.md` | 新增 Dream 业务功能模块设计和三份业务时序图 |
| `docs/design/story-workspace/story-workspace-prd.md` | 整体改写四阶段、一次确认、Agent 文件驱动、阶段化布局、API、状态、DEC 注记与缺口 |
| `docs/design/story-workspace/story-workspace-layout-design.md` | 整体改写确认前三栏和确认后两层协作工作台；删除旧逐项审批控件规范 |
| `docs/design/story-workspace/design_004_story-workspace-dream-surface-execution-page.md` | §3.4 与 DEC-029/033 同步分层写入和最终用户裁决；现行合同前向引用 design_006/007 |
| `docs/design/story-workspace/design_005_dream-module-dataflow-and-sequence.md` | 只追加目标差异注记，继续保持代码现状与 G 缺口事实 |
| `docs/design/story-workspace/2026-08-04-dream-protocol-task1-problem-decision-implementation-record.md` | 顶部追加最终裁决，原 P2 判定保留为历史 |
| `docs/design/story-workspace/2026-08-04-dream-protocol-task2-design-implementation-record.md` | 顶部追加最终裁决，首轮设计与评审保留为历史 |
| 本文件 | 记录用户审阅修订、评审、验证与任务三门禁 |

## 6. 独立评审

独立评审按六项约束打分，结论 **PASS**，无低于 8 分的阻断项：

| 项目 | 分数 | 证据摘要 |
|---|---:|---|
| A. Dreem PDF 第 3～8 页动线 | 9.5 | `design_007:13-50`；`story-workspace-layout-design:35-41,204-253` |
| B. 三阶段 Agent 文件写入规则 | 9.6 | `design_006:35-48,175-233`；初评路径建议已修正，复核确认 storyboard 唯一源、可选报告引用和“先 canonical、后 stage”顺序一致 |
| C. 一次确认回到同一 Agent | 9.6 | `design_006:267-330`；`design_007:115-137` |
| D. 单主链、无旧审批状态机 | 9.4 | `design_007:247-299`；`story-workspace-layout-design:255-278` |
| E. UI Design v2 | 9.5 | `design_007:301-309`；`story-workspace-layout-design:45-54` |
| F. owner、术语与现状缺口 | 9.2 | `design_006:11-22,397-408`；`story-workspace-prd:345-355`；`术语表:31-36,62-64` |

## 7. 验证结果

| 验证 | 结果 |
|---|---|
| `git diff --check` | 通过 |
| 四份现行文档 Markdown fence 偶数检查 | 通过 |
| 禁用术语检索 | “物化”零命中 |
| 路由一致性检索 | `dream-files` / `dream-confirmation` 统一使用 `/api/story-workspace/workflow-runs/{run_id}/...` |
| 后端静态 surface 基线 | `19 passed, 6 subtests passed in 0.62s` |
| 前端 Playwright Node seam | `11 passed (524ms)` |

前端测试命令出现 npm 日志目录 `EPERM` 提示，但 Playwright 进程退出码为 0，11 项测试全部通过；该提示不影响测试结果。

## 8. 按设计完成与留待任务三

| 项目 | 状态 |
|---|---|
| 静态 `.dream` 物理映射、surface receipt、前端 surface hook | 已实现基线，未改代码 |
| Agent 运行内容层与 `StoryWorkspaceDreamFileWriter` | 仅设计，待任务三 |
| `dream-files` REST 与 SSE revision 刷新 | 仅设计，待任务三（G5） |
| `StoryWorkspaceDreamConfirmationCommand` 与原 thread continuation | 仅设计，待任务三（G1～G3） |
| G6 入口聚合端点 | 未实现，继续列为遗留 |
| Dream 确认前三栏与后续两层执行布局 | 仅设计，待任务三 |
| 视频、画布、移动端等排除项 | 本期不做 |

## 9. 任务三门禁

本轮只完成任务一后的设计修订，不进入代码实现。人工确认 `design_006`、`design_007`、PRD 与布局稿后，才按 Subagent-Driven + TDD + 双阶段评审进入任务三。
