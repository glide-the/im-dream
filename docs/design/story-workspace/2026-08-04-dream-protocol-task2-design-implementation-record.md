# 2026-08-04 `.dream` 协议与 Dream 执行布局：任务二设计实施记录

> **任务**：`.dream` 映射交互独立设计 + Dream 页面布局对齐调研与 UI 规范（任务二）
> **输入**：[任务一问题判定记录](./2026-08-04-dream-protocol-task1-problem-decision-implementation-record.md)
> **状态**：设计完成，独立评审通过；等待人工审阅后再进入任务三
> **日期**：2026-08-04

> **2026-08-04 用户审阅最终修订**：本记录描述首轮任务二及其评审结果。首轮“运行期零写入”已被静态启动层 + Agent 运行内容层取代；不采用 host event/projection 状态机。现行主链是“同一 Chat Agent 写 workspace 与 `.dream/runtime` stage 文件 → 页面渲染 → 用户修改并确认一次 → 确认回到原 Chat → 同一 Agent 继续”。现行合同见 `design_006`、`design_007` 与后续审阅修订记录；本文件只保留为历史证据。

## 1. 结果摘要

任务二按任务一裁决完成两项设计收敛：

1. 新增 [design_006_dream-protocol-dir-mapping.md](./design_006_dream-protocol-dir-mapping.md)，作为 `.dream` 协议目录的唯一 canonical owner；术语表只定义名称和索引，`design_004` 只保留历史推导、DEC 原文与前向引用。
2. 整体校准 [story-workspace-prd.md](./story-workspace-prd.md)：主生命周期统一为「Agent 产出 → 页面渲染 → 用户审阅确认 → 后续执行」；审阅阶段保留三栏，后续执行改为独立两层协作工作台。

P2 采用任务一的方案 a：维持静态冻结。人物、场景、分镜生成期不写 `.dream/`；`workspace.json` 不加入 `workflow_run_id`、运行来源五字段、`projection_entry` 或时间戳（`design_006:48-54`、`:191-203`）。运行期事实继续由插件原有产物、host 解析/持久化、SSE 与 actor-scoped REST API 承载（`design_006:217-241`）。

## 2. 调研与上游证据如何进入设计

### 2.1 Dreem 创作者协作页面

逐页检查 `调研Dreem_app平台.pdf` 第 3～8 页后，设计采用的是信息架构与操作动线，不复制其暗色视觉和视频模块：

| 页码 | 截图要点 | 本设计处理 |
|---|---|---|
| 第 3 页 | 数据层与侧边指导 Agent 构成两种交互深度 | 执行页拆为索引/主工作面与选中项上下文协作区 |
| 第 4 页 | Assets / Outline 作为定位入口，资产按组浏览 | 执行第一层保留 Assets / Outline 上下文索引 |
| 第 5 页 | 确认后进入后续生成；截图包含上传等能力 | 保留“确认后推进”，排除上传与平台视频 |
| 第 6 页 | 故事线 → 叙事点 → 镜头文稿，点击后进入上下文 | 适配为叙事点/执行步骤 → 结构化产物摘要 |
| 第 7 页 | 确认触发后续生成，并出现预览、历史、上传 | 确认、历史、运行记录保留；预览/上传/播放器排除 |
| 第 8 页 | 决策控件和可视化编辑 | 本期只读结构化呈现，不引入画布或决策控件编辑 |

PRD 已把目标动线写为「索引定位 → 叙事点/执行步骤 → 上下文协作」，并明确两层布局不是固定第三栏（`story-workspace-prd.md:497-546`）；`design_004` 同步修订执行页目标与取舍（`design_004:305-327`）。

### 2.2 Ink & Memory UI Design v2.1

逐页检查 `Ink & Memory UI Design v2.pdf` 第 4～5 页后，执行页新增约束：

- Warm Canvas `#F6EFE5` 页面背景；
- Paper Cream `#FFFAF2` 轻纸面分区；
- Action Brown 聚焦主操作；
- Border Paper 用于页面级单一虚线边界；
- 少面板、多留白，普通静止条目无卡片阴影、外框或深色底。

对应 PRD 证据位于 `story-workspace-prd.md:205-214`、`:748-780`；布局稿执行布局增量位于 `story-workspace-layout-design.md:67-106`。

### 2.3 drama-forge 上游

只读核对 `vendor/drama-forge/`、`vendor/drama-forge-upstream-changes.md` 与 packer 后，确认：

- 上游包没有 `.dream`、`workflow_run_id`、`projection_entry` 合同；
- packer 注入的是 `.ink/workspace-init.json`，不是上游插件生成的 `.dream`；
- 上游用户项目运行区是 `stories/`、`assets/`、`exports/`、`.dramaforge/`；分镜唯一源为 `stories/<project>/episodes/EP??/storyboard.yaml`，运行产物与报告位于 `.dramaforge/runs/<internal_run_id>/{artifacts,reports}/`；
- `.dramaforge/runs/{internal-run-id}` 是插件内部运行审计，不能推断等同 host `workflow_run_id`。

以上兼容边界已进入 `design_006:57-62`、`:217-241`，并进入 DEC-029 的 2026-08-04 注记（`design_004:451-456`）。

## 3. 文档变更

| 文件 | 说明 |
|---|---|
| `docs/design/story-workspace/design_006_dream-protocol-dir-mapping.md` | 新增 `.dream` 唯一协议 owner：触发链路、目录/schema、写入规则、物理映射、冻结、Agent 边界、前端发现、receipt 关系、异常和验收 |
| `docs/design/story-workspace/story-workspace-prd.md` | 校准四阶段生命周期、阶段化布局、调研/UI 约束、验收、风险、遗留项与 DEC 增量注记 |
| `docs/design/story-workspace/design_004_story-workspace-dream-surface-execution-page.md` | 将 §3 降为历史说明并指向 design_006；修订 DEC-029/030 注记和执行页目标布局 |
| `docs/design/story-workspace/story-workspace-layout-design.md` | 把三栏限定为审阅阶段；新增执行两层布局、视觉约束和截图适配说明 |
| `docs/architecture/术语表.md` | 更新 `.dream` 条目及文档索引，明确静态字段边界和 design_006 canonical 归属 |
| `docs/design/story-workspace/2026-08-04-dream-protocol-task1-problem-decision-implementation-record.md` | 增补行号证据所对应输入基线 commit，防止任务二排版移动后误读 |
| 本文件 | 记录任务二证据、评审、校验和任务三门禁 |

## 4. 合同收敛结果

### 4.1 `.dream` owner 与冻结

- canonical 分工见 `design_006:19-31`；术语表的唯一索引见 `docs/architecture/术语表.md:31`。
- `workspace.json` schema 与禁止字段见 `design_006:177-203`。
- 人物、场景、分镜各阶段写入 owner 见 `design_006:217-226`。
- 冻结、幂等、原子、并发和失败语义见 `design_006:245-283`。
- launch-manifest、pack-receipt、plugin-load-receipt 与前端发现算法见 `design_006:287-310`。

### 4.2 Dream 生命周期与布局

- 四阶段目标生命周期见 `story-workspace-prd.md:586-626`。
- 审阅三栏与执行两层布局见 `story-workspace-prd.md:495-546`。
- DEC-003/007/001 的 2026-08-04 增量注记见 `story-workspace-prd.md:887-915`；原决策文本保留未覆盖。
- DEC-029/030 增量注记见 `design_004:431-456`；原决策文本保留未覆盖。

## 5. 按设计实现与留占位对照

任务二只改设计文档，没有把目标态伪装成生产实现：

| 项目 | 当前事实 | 本次处理 |
|---|---|---|
| pack 期 `.dream` 物理映射 | 已实现 | design_006 收编现有合同，不改代码 |
| `workspace.json` 静态冻结 | 已实现 | 维持现状；明确拒绝运行期字段和生成期追加写 |
| Agent 对 `.dream/` 只读 | 已有合同 | 继续保持；不新增运行期写区 |
| Dream 审阅三栏 | 已实现基线 | 保留为审阅阶段布局 |
| 执行页两层协作工作台 | 目标态待实现 | 文档完成；当前常驻 360px guidance sidebar 诚实标为过渡实现 |
| G1 queued 后生产推进 | 未实现 | 遗留到任务三范围裁决 |
| G2 confirm 驱动 run | 未实现 | 遗留到任务三范围裁决 |
| G3 preflight/run UI 接线 | 未实现 | 遗留到任务三范围裁决 |
| G5 projection REST | 未实现 | 执行页设计显式空态，禁止文件补探测 |
| G6 六态按钮聚合端点 | 未实现 | 继续默认隐藏，禁止前端猜测状态 |
| G4/G7 | 仍为 design_005 缺口 | 未宣称解决 |

缺口在 `design_006:308-310`、`:339-366` 和 `story-workspace-prd.md:626`、`:870-872`、`:942-945` 中均保留为待实现。

## 6. 独立评审

独立评审按三份约束逐项复核，首轮发现并打回三项：PRD 代码围栏顺序错误、`design_004` 对 workspace-init 实现状态表述过期、上游 `episodes` 目录描述过度外推。整改后复评通过：

| 维度 | 得分 | 结论 |
|---|---:|---|
| Dreem 调研 PDF 第 3～7 页布局与动线 | 8.5 / 10 | 通过 |
| UI Design v2.1 第 4～5 页视觉规范 | 9.5 / 10 | 通过 |
| 术语 canonical 与禁用词 | 9.5 / 10 | 通过 |

复评剩余阻断项为 0。三个非阻断建议也已处理：调研页码改为第 3～7 页；面包屑限定为审阅页排除、执行页保留；镜头文稿改为结构化摘要且继续排除视频。

## 7. 校验记录

### 7.1 既有行为回归

```text
$ .venv/bin/python -m pytest -q backend/tests/test_workspace_init_surfaces.py
...................                                                      [100%]
19 passed, 6 subtests passed in 0.40s
```

```text
$ cd frontend
$ npx playwright test src/hooks/story-workspace/__tests__/useWorkspaceSurfaces.test.ts --reporter=line
11 passed (334ms)
```

### 7.2 文档静态检查

- `git diff --check`：通过，无空白错误。
- 修改文档 Markdown fence 数量均为偶数：通过。
- 五个审查文件检索禁用词：0 命中。
- 已核对 design_006、PRD、design_004、布局稿和术语表之间的 canonical 引用与 DEC 增量注记。

本任务无代码、数据库或插件制品变更，因此 `npx tsc -b`、ESLint 改动文件检查和 `claude plugin validate` 不适用；既有映射与前端 surface 检测仍以上述定向回归覆盖。

## 8. 本期不做与任务三门禁

本期继续排除：复杂画布/可视化编辑、平台视频、上传、播放器、可编辑图库、移动/平板/触控、多用户实时协作、计费积分、Deck 编辑器工作流编排、数据库 DDL，以及 Agent 写 `.dream/**`。详见 PRD `:50-63` 和 design_006 `:337-348`。

任务二到此暂停。未经人工审阅确认，不进入任务三，不修改生产代码；任务三若纳入 G1～G3、G5 或 G6，需再拆为独立 TDD 实现单元和独立评审提交。
