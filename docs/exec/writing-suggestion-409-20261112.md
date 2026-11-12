<!-- [Input] User-selected WritingSuggestionCell, HTTP409 and the linked normal subscription. -->
<!-- [Output] Scope, diagnosed dependency failure, delivered recovery and validation evidence. -->
<!-- [Pos] Writing suggestion failure execution record; interaction rules remain in the canonical design. -->
<!-- [Sync] 2026-11-12: separate normal subscription recovery, automatic scheduling and provider-free UI validation. -->
# 写作建议 409 修复记录

## 需求与根因

需求：修复用户提供的建议 Cell 无法生成并返回 `POST /api/claude-agent 409`。

按该 Cell 定位其原 Session 与 Thread。Thread 无历史消息和待处理队列，当前模型和 Provider 就绪。关联账户的 Free 套餐开启自动续期，原周期于北京时间 2026-11-11 16:51:14 结束；线上周期推进任务缺少调度。Gateway 因周期已结束判定模型不可调用，Dream 返回 `GATEWAY_MODEL_SELECTION_STALE`。前端传输原先丢弃 HTTP 错误码，建议状态最终保存 `WRITING_REQUEST_FAILED`，页面显示通用不可用文案。

## 交付范围

- [Writing传输](../../frontend/app/_dream/api/voiceApi.ts)保留 `detail.error_code` 和布尔 `detail.retryable`，继续复用 `ClaudeAgentTransportError` 与共享 SSE parser。
- [建议Cell](../../frontend/app/_dream/components/Editor/WritingSuggestionCell.tsx)按模型、进行中回复、待处理消息映射双语反馈；最新模型错误提供原订阅和模型设置入口。
- 建议仍由用户点击触发；原 Thread、正文快照、建议 Cell 和迟到响应校验沿用原控制器。后端模型、订阅及权限校验保持原入口。
- Admin 现用订阅服务完成本账户的原周期推进，保留原锚点、版本和审计；新周期结束于 2026-12-11 16:51:14。
- Admin 安装独立 `ink-memory-subscription-periods.timer` 与 oneshot，复用现用 release 的原周期服务。首轮自动处理 37 条既有到期边界，第二轮处理 0 条；主服务 PID 保持。详细运维回执位于同工作区 Admin 仓库的 `docs/verification/subscription-period-recovery-20261112.md`。

设计与异常恢复时序归[正式设计稿](../design/writing-manual-suggestions.md#161-生成前拒绝与恢复)。

## 验证证据

- 现用 Admin 的原 `listAvailableGatewayModels` 只读查询：本账户已选模型 `callable=true`、`availability=included`、`messages_callable=true`。
- systemd unit 校验退出 0；自动任务首轮和第二轮均退出 0，本账户新周期 allowance 与 `period_boundary` 审计各 1 条。
- 当前源码 Playwright：`corepack pnpm exec playwright test --config=.next/codex-validation-20261112T-final.config.mjs app/_dream/api/__tests__/voiceApi.writing-sse.test.ts app/_dream/hooks/__tests__/WritingSuggestionController.test.ts app/_dream/components/__tests__/WritingSuggestionContract.test.ts e2e/writing-manual-suggestions.spec.ts --reporter=line --workers=1`，退出 0，25 passed。临时配置以 frontend 为 testDir，排除 ios、legacy 和 node_modules；执行后删除。本机 Chrome 运行原传输的受控409 → 原控制器 → 建议Cell → 双语反馈、订阅/模型链接及同Cell重试，测试只使用自有随机 Vite 端口。
- `corepack pnpm exec tsc --noEmit --incremental false --pretty false`：退出 0。
- `corepack pnpm exec eslint app/_dream/api/voiceApi.ts app/_dream/components/Editor/WritingSuggestionCell.tsx app/_dream/i18n.ts`：最终退出 0，0 errors、0 warnings。首次检查发现 voiceApi 原有未使用导入，移除该导入后仅重跑此检查。
- Mermaid：原设计稿 3 个图均由已安装 Mermaid 运行时解析成功。相关相对链接缺失 0，目录清单核对通过。
- Admin `sh -n scripts/run-subscription-period-worker.sh`：退出 0。隔离命令夹具验证缺少配置、主服务停止时退出，active 时读取当前 release 并运行原 worker。
- Admin `corepack pnpm exec vitest run app/lib/subscriptions/cycle.test.ts app/lib/subscriptions/service.test.ts --exclude '**/*.integration.test.ts'`：退出 0，2 files、12 tests passed。

本轮保留两个仓库原有未提交修改。无 Dream/Admin 主服务重启、构建、数据库 schema 变更或数据回填。真实模型建议生成尚未执行。
