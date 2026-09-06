<!-- [输入] DEC-002、旧 npm lock 下的 P0-04/P0-08 证据与当前 pnpm 重验要求。 -->
<!-- [输出] P0-04 权限修复的历史证据边界和当前重验要求。 -->
<!-- [定位] 历史技术记录；只说明证据适用范围和当前重验条件。 -->
<!-- [同步] 2026-09-06：保留安全合同、证据适用范围与重验条件。 -->

# MCP Apps P0-04 / P0-08 历史证据说明

## 1. 历史事实

旧 npm lock 下，P0-04 曾按 DEC-002 验证最小 `ImMcpAppHostAdapter`：

- adapter 在 outer iframe 导航或 DOM 插入前设置 immutable sandbox tokens 和 allow policy；
- proxy 对 inner iframe 应用相同策略；
- requested/desired/effective/revision 可追踪；
- geolocation 正向 probe、camera 拒绝、非法消息来源、teardown 和 no-replay 有浏览器证据；
- P0-02、P0-03、P0-05、P0-06、P0-07 当时使用同一 lock；
- 唯一 P0-08 记录得到 Go，同时 `production_apps_effective=false`。

这些结论只适用于当时的依赖、lock、Chrome、入口和 fixture 指纹。

## 2. 当前适用范围

DEC-005 改为 pnpm workspace 后，旧 P0-04/P0-08 不能迁移为当前结论。当前候选必须：

1. 以唯一 `frontend/pnpm-lock.yaml` 重建 P0-01。
2. 使用当前 Host adapter、sandbox proxy、Browser 入口和兼容 Chrome 重跑 P0-04。
3. 核对 P0-02/P0-03/P0-05/P0-06/P0-07 是否与当前源码和 lock 一致。
4. 原位更新唯一 P0-08 Go/No-Go 记录。
5. 无论结论如何，都保持 `production_apps_effective=false`。

## 3. P0-04 验收

| 验收 | 当前候选要求 |
|---|---|
| 依赖与入口 | renderer、AppBridge、Playwright、pnpm lock、Chrome 和唯一 E2E 入口指纹完整。 |
| 权限状态 | requested/desired/effective/revision 来自 server-owned snapshot，revision 变化会失效旧 View。 |
| iframe | outer/inner sandbox 和 allow 与 proxy `Permissions-Policy` 一致。 |
| 正反向 probe | 允许的 Web API 成功；拒绝的 API、origin、message schema 和覆盖请求失败。 |
| 生命周期 | close、Thread switch、refresh、禁用和 revision 变化按 adapter→bridge→transport→iframe 顺序 teardown。 |
| no-replay | renderer/resource/fallback 不重复首次工具调用。 |
| 敏感边界 | Browser、trace、日志和错误无 credential、headers、env、完整 URL 或用户正文。 |

## 4. P0-08 结论规则

只有 P0-04 当前候选通过，且 P0-02/P0-03/P0-05/P0-06/P0-07 的源码、lock、Browser 和入口指纹一致时，P0-08 才能为 Go。其他情况记录 No-Go 和具体失败证据。

Go 只表示可以继续 Phase 1 当前候选验收；不启用 production Apps，不代表 Phase 1、Phase 2、Phase 3 或真实外部 Server 已通过。

## 5. 回滚

回滚只停止或删除本轮具名 fixture、Browser context、sandbox proxy、trace 和临时目录。保留普通 MCP、Chat、数据库、用户数据和历史证据；不恢复旧 npm lock、自建 Server、嵌套 Next 或旧 production 路径。
