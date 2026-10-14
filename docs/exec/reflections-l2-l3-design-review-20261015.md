<!-- [Sync] 2026-10-15: 此文保留批准前设计判断；实现及真实验收状态见reflections-l2-l3-implementation-20261015.md，现行正式稿已更新。 -->
<!-- [Input] 用户对L2/L3、页面范围与Agent读取的纠正，Notion词表正文和本轮源码核对。 -->
<!-- [Output] 修订判断、来源依据、独立评审、最小实施与文档检查记录。 -->
<!-- [Pos] 本次L2→L3文档设计交付记录，不表示功能实现或真实业务通过。 -->
<!-- [Sync] 2026-10-15: 现行稿已修订并完成独立评审及文档/图示检查，完整前稿保留；未实现功能。 -->
# L2蒸馏与L3行为设计修订

## 1. 问题判断与选定方向

前稿把目标收敛为报告内提取、人工保存和个人事实库，并暂不设计L3，偏离本轮用户要求。现改为：每次保存的Reflections回顾后台生成`memory_distillation.md`；Agent按需读取；从L2生成L3主题与当前适用策略；唯一新页面为Settings中的L3行为设置。Reflections/报告/时间轴页面不改，也不保留前稿的四个写入/检索工具。

执行依据一次更新为：保留原设计任务的只读研究、文档授权和禁止实现边界，采用用户明确指定的L2→文件→L3处理关系，研究已提供词表/指南，给出可执行主题、排除/回应/反馈规则及设置生效合同；保持原回顾入口，保存完整历史并完成评审/文档检查。该优化依据只用于本轮修订，不递归优化或代替设计交付。

发现：既有报告有来源与三视角，没有派生文件；标签正文提供四主题/十六Tag。定义：缺转换、读取和策略执行，UI只设置行为。比较：覆盖单文件、人工提取、原生Read扩权均排除；选择每报告版本文件+两读取Tool+独立L3resolver。交付：重写[PRD](../prd/memory/reflections-agent-memory-prd.md)和[正式稿](../design/memory/reflections-agent-memory-interaction-design.md)。

## 2. 指定资料与新增正文依据

原三份指定资料已在[上一轮证据记录](reflections-agent-memory-design-review-20261014.md)列出。本轮继续以正文而非其工程状态为依据，并补读：

| 资料 | 与本次设计的对应 |
| --- | --- |
| [三层记忆系统架构与情绪标注](https://app.notion.com/p/2b630b7547c3801e9991c517d94a1e2e) | L2 memory_distillation.md→L3 memory_theme.md；前稿“暂不生成文件/不设计L3”已撤回 |
| [设备个人记忆系统前期方案](https://app.notion.com/p/29c30b7547c380d3aec4cafc97f97df5) | Memory_dis摘要字段和Memory_theme六字段；采用实际职责，避免设备/IP和旧文件调度照搬 |
| [情绪主题标签体系详细定义](https://app.notion.com/p/2b230b7547c380a7b0e2c4d0db258273) | 全部四主题/十六Tag ID已读取，正式稿直接列全词表 |
| [主题判断核心定义与触发逻辑指南](https://app.notion.com/p/2b230b7547c380ad8d07ea227fee69e0) | Focus/Polarity/Attribution、混合主题及按当前诉求处理；隐藏动机解释仍是推断，不自动执行 |
| [主题回应策略MVP](https://app.notion.com/p/2b530b7547c3807a869ded024184f7b6) | 作为回应映射参考；强制转移/打断/病理化不作为IM通用行为 |

资料给出词表和意图，本次建议补充版本引用、无标签、当前条件、排除、策略目录、用户设置和失败恢复，未宣称原文已实现这些工程能力。附件未读取，不影响本次已读词表，但不能据此声称验证了完整训练或心理体系。

## 3. 本轮必要源码定位

| 事实 | 证据 |
| --- | --- |
| 报告保存与派生衔接 | [reflections_agent.py](../../backend/reflections_agent.py) 800–832目前ensure后丢弃report_id；[Admin reflectionTaskService.ts](../../../ink-admin-memory/app/lib/dream/reflectionTaskService.ts) 308–325同任务返回同report、无结果不造报告 |
| 已有文件写入不等于原子发布 | [reflection_task_runtime.py](../../backend/services/admin_data/reflection_task_runtime.py) 166–185为O_TRUNC；本次需要另设版本文件临时写/校验/rename/登记合同 |
| 严格读取可以复用 | [workspace.py](../../backend/libs/claude_agent_kit/server/workspace.py) 1767–1877普通文件、拒绝符号链接/越界、容量及根身份检查 |
| 原生workspace协议不可扩大 | [workspace router](../../backend/routers/workspace.py) 223–279只认当前Thread files且受Workspace Mode约束；跨ThreadL2读取用owner-bound业务Tool |
| Settings可复用 | [StoryWorkspaceSettingsPage.tsx](../../frontend/app/_dream/views/story-workspace/StoryWorkspaceSettingsPage.tsx) 185/317/389现有导航、SettingsSection与响应式外壳；424 route映射需新增建议section |
| 设置路径不是已实现 | [storyWorkspacePath.ts](../../frontend/app/_dream/router/storyWorkspacePath.ts) 21–44为静态union/path，尚无behavior route |
| 不能任意塞配置 | [system_config_data.py](../../backend/services/admin_data/system_config_data.py) 86/163/223白名单、保存success、原收据，当前没有L3 revision/CAS；[preferences_data.py](../../backend/services/admin_data/preferences_data.py) 37 JSON不是L3 DTO |
| 每轮身份snapshot边界 | [service.py](../../backend/claude_agent/service.py) 1784读取本轮用户配置，1857只因system_prompt变化重建缓存；L3需独立每轮块和fresh revision |
| 表达背景与Runtime分离 | [context_builder.py](../../backend/claude_agent/context_builder.py) 357/566低优先级设置与Agent表达；[types.py](../../backend/libs/claude_agent_kit/types.py) 381 Runtime env不能承载主题策略 |

这是只读源码证据，不是正常数据库或模型效果验收。

## 4. 修订后的设计评审

| 目标 | 本次覆盖 |
| --- | --- |
| 不修改Reflections页面 | 原分析、报告/时间轴无新增按钮、区域或记忆列表；PRD骨架只画L3 Settings |
| 每次回顾转换 | 每报告独立L2文件，三视角转换矩阵、字段/性质/来源、版本和发布恢复均明确 |
| Agent读取memory_distillation.md | list_memory_distillations＋read_memory_distillation返回文件正文/版本，不放宽原生Read |
| L2→L3方案 | 四主题十六Tag、原六字段、同版本片段、混合主题/null/空标签和排除定义齐全 |
| 策略实际执行 | resolve_memory_behavior有当前表达判定、响应目录、来源/权限和失败状态；resolved不冒充效果保证 |
| L3设置 | 唯一Settings section、default/draft/desired/effective分开、下一轮生效及未知/冲突恢复 |
| 不过度设计 | 没有事实库CRUD、三模式Tool、标签编辑器、用户心理档案、固定计数、新通用任务平台 |
| 历史与状态准确 | 原稿逐字归档；新接口/文件/页面都标建议未实现，文档与功能验收分开 |

两项独立评审的问题均已修订：版本/重生成key、全文字节及元数据核验、派发输入冻结、未登记报告扫描、无报告/无蒸馏项分支、running内部发布阶段、L3规范字节先保存、Service生成且Host透传snapshot、plan_delivered不冒充used、父turn共享判定预算、同源BFF/Dream设置请求。L2复核要求的最后一个empty图示分支已补，L3复核通过；结论属于设计合同评审，不是功能验收。

## 5. 历史、最小实施与证据缺口

旧稿分别存[历史PRD](../prd/memory/reflections-agent-memory-prd-pre-l2-l3-20261015-history.md)与[历史正式稿](../design/memory/reflections-agent-memory-interaction-design-pre-l2-l3-20261015-history.md)。保存前字节摘要在 `output/docs/reflections-l2-l3-design-20261015/history-preservation.json`，历史链接继续相对可用。

最小实施是Admin派生/策略严格合同与capability、L2转换/文件发布、L3标注及resolver、三个Tools、独立turn snapshot和唯一Settings section。无需先建通用用户事实库。正常能力发布、模型蒸馏/标签/当前语境判定质量、文件/数据库恢复、Settings真实旅程和实际回应效果仍须验证。本轮不调用模型、不实现或测试这些功能。

## 6. 实际文档检查

以下由luna_test_runner在本仓库执行，主任务读取原始回执后收录；只验证文档。

| 实际命令 | exit | 结果 |
| --- | --- | --- |
| `node output/docs/reflections-l2-l3-design-20261015/chrome-mermaid-parse.mjs` | 0 | 本机Chrome与已安装Mermaid实际解析3/3图：两个sequence、一个stateDiagram；无page error |
| `node output/docs/reflections-l2-l3-design-20261015/validate-docs.mjs` | 0 | 动态16个Markdown、91个本地引用、Settings骨架、三图与历史字节全部通过，failures=[] |
| `git diff --check` | 0 | 无差异格式错误；只有docs文件变更，无删除 |

最新正式稿SHA-256为 `043387fccda0b931d795581ab77590ff96302e7a7f4101b8d2996ceb908ac799`，对应最后empty分支修订后的实际解析。PRD历史摘要 `c5c65d63b472e8ff2257db9d1044d03b34cb5bd46ddce5466aca4dfa52dd3834`、正式稿历史摘要 `96ef8ff6d48361f98941cf1c7b0e22dfd7718865197672ae892ba5e82d199681` 与保存前字节一致。

日志与脚本位于 `output/docs/reflections-l2-l3-design-20261015/`，最终记录为 `chrome-mermaid-parse-final.log`、`validate-docs-final.log`、`validation-summary.json`、`final-hash-receipt.json`。本轮具名Chrome profile、随机loopback服务及临时目录已清理，没有触碰正常Dream/Admin/Gateway、数据库或模型。收录本节后只做Markdown/差异复核，不再变更正式图稿；上述结果不是L2文件生成或L3策略功能通过。
