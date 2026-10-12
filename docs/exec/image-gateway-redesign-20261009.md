<!-- [Input] 用户确认的Responses主对话+独立Images方向，三套源码、现行PRD/正式设计及历史稿。 -->
<!-- [Output] 本轮双钻石取舍、影响评估、文稿修订、独立评审与实际验证回执。 -->
<!-- [Pos] IM图片设计的本轮执行记录；不实施Admin Image模型中心或新图像功能。 -->
<!-- [Sync] 2026-10-09: 独立评审两处修订已复核，文档/三图和现有适配器本轮回执归档；不声明图像功能验收。 -->

# 图像方案：Gateway双链路重写与验证

本轮继续当前已登记IM执行任务`01a116cd-51e2-79b0-af95-db07ad5cfae9`，不重复创建任务。Codex目标覆盖设计交付、必要修订、独立评审和本轮验证。用户后续Admin Image模型中心请求已整理为提示词，没有在本轮实施。

## 目的与边界

用户在同一段聊天中获得图片、继续修改、查看下载，并在重开会话后接着使用。功能描述只写用户获得的能力；接口、认证、转换、文件及持久化规则归实施说明。范围仍为调研和设计，新增功能未实现，不做当前安装Codex App或真实模型验收。

[PRD](../prd/chat/image-generation.md)、[正式设计](../design/claude-agent/image-generation-interaction-design.md)、[实施说明](../design/claude-agent/image-generation-implementation-notes.md)是现行交付；[源码研究](../design/claude-agent/image-generation-source-research.md)、[接口对比](../design/claude-agent/codex-image-generation-call-comparison.md)、[Codex CLI完整链路](../design/claude-agent/codex-cli-image-generation-chain.md)提供证据。

## 双钻石的实际取舍

1. **发现问题**：用户关心图片持续使用，现有稿混淆Claude Runtime与主模型，未解释Gateway是否能转换Responses，也未追到Codex图像执行端。
2. **定义问题**：保留现有会话和CLI执行器，明确主对话与图像执行；图片需进入原回复和历史。不能只换Key、只展示工具文件链接或只画IPC箭头。
3. **展开方案**：比较独立Images、Responses内置image_generation和CLI直接改Responses。独立Images能复用现有工具执行；内置方案可适配但需要额外平台工具及图片结果通路；直接修改CLI扩大Runtime影响。
4. **收敛交付**：采用主对话CLI Messages经Gateway转换Responses，内部图像工具单独调用Images。补齐主对话图片适配是必要条件，不因采用独立Images而省略。保留内置方案为对比，当前不实现或自动切换。

本轮不是重新优化提示词或扩大产品范围；按已确认目的完成实际文稿和验证。

## 关键源码结论与修订

G1–G8依据及行号在实施说明；K1–K19在Codex CLI链路文档。当前Gateway确实有Messages→Chat→Responses转换，也有文本/函数返回及流转换，但存在：

- 第一层`anthropicContentToOpenAI`只保留text，用户image可被静默丢掉。
- 第二层`messageText`实际收到图片会抛协议不支持，不能与第一层丢图混为一谈。
- 图片tool_result转成JSON文字，不能作为视觉图片供主模型使用。
- `responseTools`只声明function，输出转换与流接线未消费image_generation_call。
- 普通OpenAI Provider不自动走Responses；codex managed认证不能当普通API Key。
- Admin公开Images入口与图像授权/计费合同仍待发布。

因此Claude Code经Gateway可使用Responses，当前完整图片兼容尚未实现。Runtime不决定主对话必须使用Claude模型。指定Codex CLI源码实现自定义image_gen.imagegen调用独立Images，不证明当前安装App版本一致或真实网络请求已观察。

## 验证前影响评估

| 范围 | 本轮改动与需要核对的行为 | 验证边界 |
|---|---|---|
| 用户发起 | 目的、功能与页面骨架，原输入框/附件/停止 | PRD骨架与正式稿一致性；无UI实现变更。 |
| Agent/Tool | 主模型/Runtime区别、内部MCP/授权/执行边界 | 实际稿评审、现有函数转换核查；新增Tool未执行。 |
| 消息/事件 | call ID、Messages/Responses请求与文本/函数回传 | 原适配器确定性测试及完整函数往返探针；不改SSE。 |
| 前端状态/图片 | 三图、授权/完成/失败/停止、原查看器 | 文稿和Mermaid实际渲染；无功能E2E。 |
| 文件/权限 | 当前Thread校验、安全新图写入、原读取 | 设计审查及源码引用；新图安全发布未实现。 |
| 保存/历史 | URI进入原parts、重新打开、文件/消息独立失败 | 设计完整流程及兼容检查；不宣称持久化实测。 |
| 失败/停止/重试 | 主适配错误与Tool错误区别、迟到边界、读取不生成 | 现有适配器错误核查+实际稿状态一致性。 |
| 既有文本/工具/媒体 | 不改旧消息、不改Runner/Thread/SSE/Schema | 受影响Gateway文本/工具/流回归；图片缺口如实保留。 |

## 本轮修订与历史保护

现行PRD保留六项功能及桌面/窄屏骨架；正式稿包含完整双链路正常时序、异常恢复及状态图；实施说明包含具体程序合同和必需V11/V12；源码研究/接口对比追加本轮Gateway证据，保留十幅原对比图。合并目录中同一Codex CLI文档的重复登记，未修改无关目录项或程序。

改写前原文完整保存在[正式稿前稿](../design/claude-agent/image-generation-interaction-design-20261009-gateway-history.md)、[实施说明前稿](../design/claude-agent/image-generation-implementation-notes-20261009-gateway-history.md)、[PRD前稿](../prd/chat/image-generation-20261009-gateway-history.md)。连同四份更早历史逐字SHA验证；不改历史原文。源代码基线包含12个实际文件的SHA，不含凭证。

## 独立评审与验证计划

交既有`luna_test_runner`评审实际PRD/正式稿/实施说明，并执行具名文档验证、Mermaid渲染、现有Admin三组纯适配器测试和新兼容探针。主执行者修订发现的问题，受影响检查重新执行后才收口。测试不访问正常数据库、不调用Provider、不启动业务服务；Chrome仅为文档图示渲染一次启动，不下载浏览器。

命令及原始回执保存在本机具名目录`frontend/test-results/image-gateway-redesign-20261009/`，该目录是忽略的验证产物，不以Markdown版本库链接引用。

## 独立评审发现与修订

首轮独立评审指出两处文稿不一致：异常/状态图没有分别标出第一层丢图与第二层拒绝；消息保存失败虽在异常时序中，却未明确其与图片可见状态的关系。主执行者已分开两条V12失败路径，明确第一层保护仍是建议、未实现，当前静默丢图不能当安全拒绝。状态表、异常图和状态图V8说明保存失败只报告原持久化错误、保留可见图，不增加状态机或自动重发。

评审未发现需要新的Runner、SSE、控制通道、环境分支、数据库表、接口选择页面或确认弹窗。修订后独立复核已关闭两项问题，方案在已列前置条件满足后可实施；首轮日志与评审保留，不用首轮图示结果代替最终稿复核。

## 本轮首轮回执

下表为实际命令本体；完整shell记录及原始日志在具名目录的`commands.json`。首轮结束后修改了正式稿两图，需要重新执行受影响文档/渲染检查及独立复核。未修改适配器/探针，不无理由重跑已通过的技术检查。

| 命令与cwd | 退出码 | 关键输出与实际覆盖 |
|---|---|---|
| 根目录：`python3 frontend/test-results/image-gateway-redesign-20261009/check-docs.py` | 0 | 17目标/17头，14清单、234本地引用、77行号、10 JSON；7历史、12源码SHA、10原对比图及2 PRD骨架保持；errors=[]。外链未联网逐项检查。 |
| frontend：`node test-results/image-gateway-redesign-20261009/render-mermaid.mjs` | 0 | Chrome一次启动，正式稿3/3语法解析与SVG渲染成功；自有browser/Vite已关闭。仅文档图示。 |
| Admin：`pnpm exec vitest run app/lib/gateway/protocol-adapters.test.ts app/lib/gateway/responses-adapter.test.ts app/lib/gateway/stream-adapters.test.ts --reporter=dot` | 0 | 3 files / 17 tests通过；纯请求/响应/流、函数ID、终态及协议错误。Node输出一项module.register弃用提示，不影响测试结果。 |
| Admin：`pnpm exec tsx /Users/dmeck/project/ink-dream-memory/frontend/test-results/image-gateway-redesign-20261009/probe-gateway-compatibility.ts` | 0 | 8/8：文本/function完整往返及流；分别复现图片丢失、图片拒绝、tool图片JSON化、内置工具声明/结果未转发、失败/cancelled错误。后六项为现有限制/错误核查，非图片功能验收。 |
| 根目录：`git diff --check -- <本轮明确文档清单>` | 0 | 无输出；精确路径列于commands.json，不检查或清理无关改动。 |

测试未访问DB、Provider、真实账户/模型，未启停业务服务。原始日志、独立评审与SVG保留，仅清理本轮Chrome/Vite。源码SHA一致表明未修改所核查程序，不等于新功能已实现。

## 修订后复核

修订后重新执行同文档检查与正式稿三图渲染，不仅检查原发现位置。`commands-final.json`记录本轮使用`set -o pipefail`捕获底层命令失败，原日志存`*-final.out`，首轮和最终SVG分别保存在`svg-initial/`与`svg-final/`。

| 本轮重新执行的命令 | cwd / 退出码 | 关键输出 |
|---|---|---|
| `python3 frontend/test-results/image-gateway-redesign-20261009/check-docs.py` | IM根 / 0 | 17目标/17头、14清单、235引用、77行号、10 JSON；7历史/12源码SHA相等；10原图、2骨架保持，errors=[]。 |
| `node test-results/image-gateway-redesign-20261009/render-mermaid.mjs` | frontend / 0 | 正常/异常/状态3图全成功，SVG 51046/42622/41186字节；自有Chrome/Vite关闭。 |
| 下列限定`git diff --check` | IM根 / 0 | 无输出；包括当前CLI链路文档，不覆盖其他用户改动。 |

```bash
git diff --check -- docs/design/claude-agent/image-generation-interaction-design.md docs/design/claude-agent/image-generation-implementation-notes.md docs/design/claude-agent/image-generation-source-research.md docs/design/claude-agent/codex-image-generation-call-comparison.md docs/design/claude-agent/codex-cli-image-generation-chain.md docs/prd/chat/image-generation.md docs/design/claude-agent/.folder.md docs/prd/chat/.folder.md docs/exec/.folder.md docs/exec/image-gateway-redesign-20261009.md
```

`consistency-review-final.md`确认两项问题关闭，现行稿未把新增能力、当前App、Admin公开Images入口或真实Provider验收写成已实现。没有增加无业务依据框架或操作。17个纯适配器测试和8个探针未再次执行：其源程序及探针没有变化，首轮本次回执仍有效；图示修改后文档/渲染/一致性均实际重跑。

主执行者另核对正常保存失败确实由`ClaudeAgentService._persist_assistant_turn`抛`ClaudeAgentAssistantPersistenceError`（`service.py:3175`），不是图片生成失败；partial保存`service.py:3037`只记录异常，不借本设计改变原取消/部分保存语义。V8图片保留规则是新增图像结果的实施要求，不宣称partial保存新增UI反馈已存在。

## 未验收与实施条件

本轮设计评审与适配器技术核查不能代替新图像功能验收。新增Tool、Images请求授权/计费、安全图片写入、完整公开入口生成/编辑/保存/重开/恢复、当前安装Codex App及真实账户/模型均未验收。

实施先发布Admin图像能力并确认主对话Provider与图片兼容、附件→当前Thread文件映射、持久文件拓扑。然后执行V2–V9、V11与V12完整技术链，指定现有正常账户/模型/实体后按本机正常业务协议执行V10，保留Admin可查记录。Schema如有实际需求由Admin Drizzle管理；不增加Dream建表、运行时降级或新控制通道。

本轮已完成设计交付、必要修订、独立复核与现有适配器核查。最终回执归档的文档检查仍由Luna执行；目标在该检查通过后由主执行者标记完成，最终状态以Codex目标记录为准。此处完成范围为设计与验证，不包含新图像实现。
