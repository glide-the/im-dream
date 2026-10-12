<!-- [Input] User-reported normal-service 409 and unavailable AI models after image/sketch delivery. -->
<!-- [Output] Actual diagnosis, minimal corrections and fresh full-path validation receipts. -->
<!-- [Pos] Image delivery service recovery; previous isolated receipts remain historical evidence. -->
<!-- [Sync] 2026-10-10: record recovery purpose and impact before fixes and validation. -->

# 图片交付后正常服务恢复

## Optimized Prompt

在既有 Ink & Memory 执行任务中修复用户启动正常服务后遇到的409和AI模型无法访问。先从当前已登录浏览器的公开接口和必要服务诊断取得真实状态、错误码与响应结构，分别定位目录校验、端点授权、数据能力或会话冲突；不根据状态码猜测。复核上轮Images改动对普通文本、模型目录、Runtime授权、消息发送与历史的影响，修复最小必要合同，不改订阅、账本、权限或数据库Schema来绕过失败。保留用户及其他Agent改动，更新现行文档及目录。补齐“正常服务未验收”的状态，撤销实际可用性未证实的结论。由luna_test_runner重新执行确定性合同测试及完整公开生产入口的隔离E2E，不能只用组件测试证明可用；正常浏览器与真实模型验收由主执行者操作，明确账号、模型、当前数据库记录和覆盖。用户已要求不询问，使用已有明确上下文推进，缺少关键真实输入时记录未验收，不创建影子账户或替代业务数据库。不得重启、部署或停止用户服务，除非已有明确授权。

## 影响与计划

| 边界 | 需要核对 |
| --- | --- |
| 模型设置和新会话 | 订阅可用状态、Messages端点callable、图片专用模型过滤、默认模型及保存模型选择。 |
| 普通发送与Tool | 原身份/Thread授权、Runtime grant、模型请求、SSE与文字/图片Tool兼容。 |
| 消息与事件 | 409具体来源、错误码、Thread/消息关联；不改变冲突恢复或取消语义。 |
| 图片与文件 | 原附件/草图、图片显示、现有访问授权和后续编辑。 |
| 保存与恢复 | 公开消息持久化/历史读取；真实业务证据与隔离fixture分别记录。 |

1. 已确认正常浏览器模型目录GET返回200，前端仍拒绝目录；继续定位409的实际来源。
2. 修正最小受影响合同，补回归和完整公开入口隔离E2E。
3. 等待并核验新命令回执；复查用户正常会话的目录和发送边界，记录真实模型/数据库未验证项。

## 首次实际证据

当前已登录Chrome的IM页面为本机`/story-workspace/settings/model`。点击原“重新加载模型”，`GET /api/gateway/models`返回200，13个模型、原data/defaultModelAlias DTO；页面显示“平台模型目录响应异常”。部分模型availability为included而Messages端点callable为false；前端`gatewayModelSchema`仍要求二者相等。这会使整个列表失败，不能归因上游模型不可达。

首次观察时409的端点与错误码尚待取得，不将目录校验问题自动当成409原因。上轮13条浏览器检查是隔离生产组件journey，未覆盖正常服务发起至Runtime与真实模型的完整链路，不能作为当前服务可用性证明。

## 已定位的409及恢复计划调整

正常浏览器在新建本轮验证Thread后，`POST /api/claude-agent`返回409，`detail.error_code=GATEWAY_MODEL_SELECTION_STALE`。历史GET返回空消息，状态为not_found、turn_count=0；拒绝发生于模型执行之前，未接受一个运行中的turn。记录保留，未删除业务数据。

Admin `app/lib/gateway/models.ts`新增Messages/Chat端点资格只按独立plan entitlement计算，但既有`app/lib/subscriptions/gateway.ts:resolveGatewaySubscription`允许`entitlementSource=allowance-only`覆盖文本推理；新增目录和实际入口不一致。恢复沿用既有文本资格：Provider、价格、订阅周期、用户模型权限和Token余额仍由原边界检查；目录明确排除chat=false模型，Images仍要求独立scope、模型能力与价格。未改订阅、权限、账本、Schema或服务key。

### 调整前的Optimized Prompt

在已定位的目录资格回归基础上完成正常服务恢复：先通过Admin文本/图片合同、IM目录/选择、完整公开入口与历史回归；在独立Next输出目录构建可审查的新产物。当前正常Admin通过pnpm start运行已构建产物，源代码修改不会进入该进程。为完成本轮已授权的服务修复，由主执行者在保留原构建、限定原端口和已识别进程的前提下激活通过检查的构建，失败恢复旧产物和原启动命令；不重启IM用户的VSCode调试进程，不改数据库和账户，不清理真实业务记录。随后以当前登录会话、原已保存模型验证正常发送、持久化和重新打开。本轮自动化检查继续由luna_test_runner执行，不把隔离组件检查等同完整或真实模型验收。

### 调整后的执行顺序

1. 已修正目录与实际文本资格差异，初次Admin 27条合同通过；继续公开入口完整E2E及错误恢复验证。
2. 独立目录构建并保留旧产物；主执行者限定激活Admin修复，不以测试清理停止已有服务。
3. 复核正常目录、原模型发送与重开；汇总新回执及图像真实模型未验收边界。

## 本次修订和影响范围

1. Admin `models.ts` 新增端点资格误要求文字模型独立plan行，偏离既有 `resolveGatewaySubscription` 的 allowance-only 行为。修正Messages/Chat目录并保持Images独立授权；没有修改账户、订阅、余额、Schema或调用权限。
2. IM `gatewayModelsApi.ts` 不再要求included等于Messages.callable，保留合法不可调用项并过滤明确chat=false；BFF也过滤图片专用项。默认和非法资格仍fail closed。
3. `ClaudeAgentTransport` 只映射已知HTTP409模型选择码，`ChatMessageList` 显示设置恢复说明；其他409和SSE逻辑不变，不自动换模型、重发或取消。
4. 完整公开图片GET揭露Host写到根generated而URI指向files/generated。修为Thread `files/generated/`，参考图读取保留URI中的files路径；新增files和generated符号链接否定检查，不放宽文件授权。
5. 上传PNG公开入口揭露Router缺少quote导入及URI重复files，造成视觉附件被跳过。补上导入并用workspace://加服务器files/...路径；正常附件同步、ContextBuilder及后续编辑使用同一个文件。

此次修改影响目录、执行前409反馈、图片文件与视觉附件；Runner、SSE、Thread恢复/取消、数据库及资源策略无新语义。代码检查和隔离E2E仍通过公开生产入口与真实DTO；SDK、Admin存储和上游Transport只在tests内注入。

## 正常服务恢复与真实文字验收

Admin原构建保留为 `.next`（BUILD_ID `c4Y11GbVh_S5-EFP7s28t`）；修正源码使用独立Next输出目录构建（`uKO2KYiY--5OpVGm_9RJJ`）。激活时第一次误用普通 `pnpm start`，原embedded supervisor在子进程退出时停止其数据库，导致IM会话检查503。已纠正为原正常监督启动路径 `INK_ADMIN_E2E_DIST_DIR=.next-e2e-im-recovery-20261010 PORT=3000 pnpm run start:embedded`，复用原 `.ink-memory/postgres`，身份/模型接口恢复200；没有初始化替代库、迁移或改账户。具体产物、监督进程与旧产物保留情况见[激活回执](/tmp/im-image-service-recovery-20261010/admin-activation.json)。正常服务新监督进程保留，不当测试资源清理。IM原前端与VSCode后端进程未停止。

使用当前已登录正常账户、原保存 `gpt-6.1-sol`，在正常业务Thread `27872a7b-1544-4742-9004-76995652a7c0` 发送“IM 服务验证：请只回复 OK，不调用工具。”。此前两个409拒绝未启动Agent/未持久化消息；修正后只发送一次，POST返回200并回复OK。正常历史API返回一条用户、一条助手消息；助手metadata模型为gpt-6.1-sol、turnStatus=completed、inputTokens=20229/outputTokens=5。刷新页面后从聊天历史重开可见OK，没有重新发起Agent。真实记录保留，未删除。

[正常浏览器回执](/tmp/im-image-service-recovery-20261010/normal-browser-receipt.json)、[重开截图](/tmp/im-image-service-recovery-20261010/normal-chat-reopened.jpg)。这是正常文字业务/模型证据；未执行真实图片模型、Images结算或Admin后台账本复核。后端图片/附件源码修正在隔离入口验证，当前用户VSCode实例未主动重启，不能宣称该实例已加载全部图片修订。

## 测试失败及修订轨迹

全部原失败回执保留在 `/tmp/im-image-service-recovery-20261010`。早期public fixture的broker属性、关闭方法、消息分页和幂等保存配置逐次修正。rerun4的图片公开访问失败揭露真实路径问题；rerun5为36 passed、exit0。首次完整17文件为649 passed/1 failed/1 skipped，失败是旧提示词断言，已对齐files目录规则。rerun6为93 passed/1 failed，上传视觉块断言揭露quote漏导入，已修正。失败不被后续成功覆盖，也不把注入边界错误或浏览器启动前置问题当成产品缺陷。

## 当前未验证边界

- 真实图片模型的生成、编辑、CLI自主调用工具与正常Images账本验收未执行，隔离Transport不能证明上游模型质量或收费。
- 后端用户调试实例未重启；新图片/附件源码需由正常启动加载后再做真实图片业务验收。
- Workspace Mode关闭的既有附件视觉能力缺口不在本轮改变范围；资源、线程与取消语义保持原合同。
- 当前历史API证明正常消息保存与重开；未额外打开Admin账单界面核对该文字请求的结算行。

## 关键源码证据

| 修订 | 当前模块及符号 |
| --- | --- |
| 原文字资格 | [gateway.ts](/Users/dmeck/project/ink-admin-memory/app/lib/subscriptions/gateway.ts:74)，`resolveGatewaySubscriptionOnClient`；第207行 `entitlementSource=allowance-only`。 |
| 目录与实际入口一致 | [models.ts](/Users/dmeck/project/ink-admin-memory/app/lib/gateway/models.ts:284)，`textCallable`及Messages/Chat endpoint资格；Images独立。 |
| 浏览器模型目录 | [gatewayModelsApi.ts](../../frontend/app/_dream/api/gatewayModelsApi.ts:35)，`gatewayModelSchema`、目录default校验及第77行过滤。 |
| 执行前409反馈 | [claude-agent-transport.ts](../../frontend/app/_dream/lib/claude-agent-transport.ts:561)，`ClaudeAgentChatTransport`；[ChatMessageList.tsx](../../frontend/app/_dream/components/chat/ChatMessageList.tsx:893)，专用反馈。 |
| 文件/编辑路径 | [images.py](../../backend/services/admin_gateway/images.py:81)，`_reference`；第168行 `_publish`，按描述符依次打开files/generated。 |
| 视觉附件引用 | [claude_agent.py](../../backend/routers/claude_agent.py:1381)，`AttachmentPayload.id`；第81行编码导入。 |
| 完整公开入口 | [test_image_chat_public_journey.py](../../backend/tests/test_image_chat_public_journey.py)，两个HTTP旅程覆盖生成及上传参考编辑；只在测试边界注入外部依赖。 |

## 本轮最终验证回执

以下为本次重新执行结果，不复用上轮648项与13条的旧回执。主执行者已读取原始输出与exit文件。正常业务由主执行者核验；确定性测试由luna_test_runner执行。

| 检查 | 退出码 / 关键输出 | 实际覆盖与原始回执 |
| --- | --- | --- |
| 后端focused rerun7 | 0；95 passed | 公开HTTP图片/上传旅程、图片Tool/路径/安全与提示词；[stdout](/tmp/im-image-service-recovery-20261010/public-journey-backend-rerun7.out)。 |
| 后端完整17文件 rerun2 | 0；652 passed、1 skipped、253 subtests passed | 目录、身份、delegation、Factory/Runner/Service、SSE、workspace、持久化投影、两个完整公开HTTP旅程与恢复；[stdout](/tmp/im-image-service-recovery-20261010/public-journey-backend-full17-rerun2.out)。 |
| Chrome浏览器4组 | 0；13 passed | 草图操作/PNG/添加与发送、失败保留/重试/窄屏、旧输入/slash/队列、图片/报告预览下载及重载；[stdout](/tmp/im-image-service-recovery-20261010/frontend-public-playwright-rerun7.out)。 |
| 前端目录合同 | 0；6 passed | included但Messages不可调用、Images-only过滤、非法目录/默认拒绝；[stdout](/tmp/im-image-service-recovery-20261010/frontend-gateway-api-playwright-rerun7.out)。 |
| HTTP409及SSE合同 | 0；4 passed | 已知stale/conflict安全反馈、其他409兼容、普通SSE；[stdout](/tmp/im-image-service-recovery-20261010/frontend-http-errors-playwright-rerun7.out)。 |
| Admin合同 | 0；3files/27 tests | allowance-only文字资格、Images-only资格、原订阅与图片handler；[stdout](/tmp/im-image-service-recovery-20261010/admin-catalog-vitest.out)。 |
| 两仓TypeScript/ESLint | 各0，stdout为空 | 本轮前端6个文件与Admin目录两个文件；当前类型/静态检查。 |
| Admin独立构建 | 0；Compiled successfully、20/20 static pages | 修复产物随后用于正常启动，旧.next保留；[stdout](/tmp/im-image-service-recovery-20261010/admin-build.out)。 |
| 文档检查 | 0；31files/178links/23line references，warnings/errors均0 | 当前PRD正文骨架、设计正文图、Markdown引用/索引及README对应；[stdout](/tmp/im-image-service-recovery-20261010/recovery-docs-final.out)。追加本表之后另执行closure，最终引用数以closure为准。 |
| Mermaid | 0；2sources/6blocks/6SVGs，passed | 图片和草图各正常/恢复/状态图实际解析渲染；[stdout](/tmp/im-image-service-recovery-20261010/recovery-mermaid-final.out)。 |

唯一skip为既有 `TestClaudeAgentRunnerToolConfirmation.test_tool_confirmation_callback_is_called`，它需要真实Claude SDK子进程PreToolUse；注入SDK不能证明该hook。25 warnings为现有FastAPI lifespan迁移提示。浏览器使用已安装Chrome，未下载revision；测试自有临时服务/浏览器已退出，正常服务、数据库、Thread和回执保留。

### 实际命令

cwd `/Users/dmeck/project/ink-dream-memory`：

```sh
PYTHONPATH=backend:. backend/.venv/bin/python -m pytest backend/tests/test_image_chat_public_journey.py backend/tests/test_image_generation_tool.py backend/tests/test_claude_agent_context_builder.py -q
PYTHONPATH=backend:. backend/.venv/bin/python -m pytest backend/tests/test_image_generation_tool.py backend/tests/test_admin_gateway_models.py backend/tests/test_admin_gateway_model_selection.py backend/tests/test_admin_request_auth.py backend/tests/test_admin_delegation.py backend/tests/test_session_projection_broker.py backend/tests/test_claude_agent_service.py backend/tests/test_claude_agent_context_builder.py backend/tests/test_claude_agent_runner.py backend/tests/test_claude_agent_workspace.py backend/tests/test_server_claude_agent.py backend/tests/test_workspace_router.py backend/tests/test_claude_agent_sse.py backend/tests/test_claude_agent_thread_factory.py backend/tests/test_claude_agent_gateway_model.py backend/tests/test_gateway_models_router.py backend/tests/test_image_chat_public_journey.py -q
python3 frontend/output/image-service-recovery-20261010/check-docs.py
git diff --check
```

cwd `/Users/dmeck/project/ink-dream-memory/frontend`：

```sh
pnpm exec playwright test e2e/sketch-input.spec.ts app/_dream/components/chat/__tests__/AIInputDockSlashMenuRegression.test.ts app/_dream/components/chat/__tests__/WorkspaceUriPreview.test.ts app/_dream/components/chat/__tests__/WorkspaceReportPreview.test.ts --workers=1 --reporter=line --output=/tmp/im-image-service-recovery-20261010/playwright-public-rerun7
pnpm exec playwright test app/_dream/api/__tests__/gatewayModelsApi.test.ts --reporter=line --workers=1 --output=/tmp/im-image-service-recovery-20261010/playwright-gateway-api-rerun7
pnpm exec playwright test app/_dream/lib/__tests__/claude-agent-http-errors.test.ts --reporter=line --workers=1 --output=/tmp/im-image-service-recovery-20261010/playwright-http-errors-rerun7
pnpm exec tsc --noEmit --incremental false
pnpm exec eslint app/_dream/api/gatewayModelsApi.ts app/_dream/api/__tests__/gatewayModelsApi.test.ts app/_dream/lib/claude-agent-transport.ts app/_dream/lib/__tests__/claude-agent-http-errors.test.ts app/_dream/components/chat/ChatMessageList.tsx app/_dream/i18n.ts
node output/image-service-recovery-20261010/render-mermaid.mjs
```

cwd `/Users/dmeck/project/ink-admin-memory`：

```sh
pnpm exec vitest run app/lib/gateway/models.test.ts app/lib/subscriptions/gateway.test.ts app/lib/gateway/image-handler.test.ts --reporter=verbose
pnpm exec tsc --noEmit
pnpm exec eslint app/lib/gateway/models.ts app/lib/gateway/models.test.ts
INK_ADMIN_E2E_DIST_DIR=.next-e2e-im-recovery-20261010 pnpm build
```

`INK_ADMIN_E2E_DIST_DIR`只选择Next构建产物目录，不改变业务运行路径或授权。

## 任务和目标状态

沿用既有任务“调研并设计 Tool 图像生成交互” `01a116cd-51e2-79b0-af95-db07ad5cfae9`，没有重建或递归派发Admin任务。本轮恢复目标在最后文档收口和差异回执退出0后标记完成；完成范围为409/模型目录恢复、受影响源码修正、完整隔离技术验证和正常文字模型验收。图片真实模型、上游结算及当前调试实例加载新图片代码仍按上文未验证边界记录，不宣布图片已通过真实业务验收。

### 收口回执

追加最终回执表后的closure文档检查退出0：31文件、187链接、23行引用，warnings/errors均为空；IM `git diff --check`退出0，Admin本次实际修改路径检查退出0。原始 `recovery-docs-closure.out/.exit`、`im-recovery-diff-closure.out/.exit`、`admin-recovery-diff-closure.out/.exit` 位于前述回执目录，输出分别为通过JSON、空、空。

Admin收口的准确命令（cwd `/Users/dmeck/project/ink-admin-memory`）：

```sh
git diff --check -- app/lib/gateway/models.ts app/lib/gateway/models.test.ts app/lib/gateway/.folder.md docs/design/image-model-center.md docs/prd/image-model-center/README.md
```
