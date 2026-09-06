<!-- [输入] task_301、DEC-002 与旧 npm lock 下的 Phase 0 命令回执。 -->
<!-- [输出] P0-01—P0-08 历史实现、验证、失败和回滚记录。 -->
<!-- [范围] 只作为历史技术证据；不代表当前 pnpm lock、当前源码或 production Apps 已通过。 -->
<!-- [同步] 2026-09-06：保留实际命令、退出码、安全结论并明确当前重验缺口。 -->

# task_301 Phase 0 历史执行证据

## 1. 适用范围

本报告记录 2026-09-04 在旧 npm lock 上完成的 provider-free Phase 0 PoC。该候选使用：

- `@mcp-ui/client@7.1.1`
- `@modelcontextprotocol/ext-apps@1.7.5`
- `@modelcontextprotocol/sdk@1.30.0`
- `@playwright/test@1.62.1`
- Chrome `152.0.7977.77`
- `frontend/package-lock.json` SHA-256 `9938d0c4476f1e36c11915fb8ecdfb29c17f961af19eaeed4c603089b17e27ac`

DEC-005 改为根 pnpm workspace 后，这些结果只能说明旧候选曾经通过。当前结论必须在 `frontend/pnpm-lock.yaml`、当前 Browser 入口和当前源码上重新验证 P0-01/P0-04/P0-08，并核对其他 P0 证据指纹。

## 2. 历史实现事实

- `ImMcpAppHostAdapter` 是 PoC 中唯一持有权限 iframe 的组件，使用 `AppBridge` 与 `PostMessageTransport`。
- adapter 校验 `_meta.ui`、未知权限键和 immutable desired policy，计算 `requested ∩ desired ∩ Host supported`。
- outer/inner iframe 在导航和使用前获得相同 revision 的 sandbox 与 allow policy；proxy 返回匹配的 `Permissions-Policy`。
- Browser MCP 请求只访问 IM endpoint；Browser 不读取上游 URL、credential、command 或 env。
- 首次工具调用计数为 1，proxy 工具调用为 0，resource read 为 1。
- stdio、localhost、Node 可达 HTTP/SSE 和 fresh-session 行为由隔离 fixture 验证。
- Chat fake-DB round trip 保留 `serverRef`、原始 tool name、`toolCallId`、input 与完整 `CallToolResult`，没有 schema/DDL 写入。
- `production_apps_effective=false` 在整个验证中保持不变。

## 3. 命令与结果

| 命令 / 检查 | Exit | 关键结果 |
|---|---:|---|
| `shasum -a 256 frontend/package-lock.json` | 0 | 匹配旧 npm lock digest。 |
| `npm --prefix frontend ls @modelcontextprotocol/ext-apps @modelcontextprotocol/sdk @mcp-ui/client @playwright/test --all` | 0 | 根版本分别为 1.7.5、1.30.0、7.1.1、1.62.1。 |
| installed Chrome 轻量启动检查 | 0 | Chrome 152.0.7977.77；未下载 Playwright 浏览器。 |
| `npm --prefix frontend run e2e:mcp-apps-phase0` 第一次 | 1 | 隔离 harness 的 geolocation grant 分区和 desired-policy 读取计数需要修正。 |
| 同一命令第二次 | 1 | 权限路径通过；异步 teardown 顺序需要修正。 |
| 同一命令最终运行 | 0 | `4 passed in 9.9s`；权限正反向 probe、来源/schema 攻击、计数和 teardown 通过。 |
| `python backend/tests/fixtures/mcp_apps_phase0/phase0_standard_apps_fixture.py --probe-all` | 0 | stdio/local HTTP/SSE/fresh sessions 通过，共享状态可见。 |
| `PYTHONDONTWRITEBYTECODE=1 uv run --native-tls --project backend --frozen --with pytest python -m pytest backend/tests/mcp_apps_phase0 -q -p no:cacheprovider` | 0 | `3 passed in 0.84s`。 |
| scoped `git diff --check` | 0 | 无空白错误。 |

系统 Python 直接运行 pytest 时因该解释器没有安装 `pytest` 而失败；这是 harness 依赖缺失。冻结 uv project 对相同测试目标执行成功。

## 4. 历史验收结论

| ID | 旧候选结果 | 证据 |
|---|---|---|
| P0-01 | pass | 精确依赖、旧 lock digest 与 dry-run install。 |
| P0-02 | pass | 标准 Browser Client initialize/tools/list/resources/read 和 IM-only 网络 trace。 |
| P0-03 | pass | descriptor/resource trace、调用计数和 Chrome 截图。 |
| P0-04 | pass | 两层 iframe policy、CSP、Permissions-Policy、攻击拒绝和 teardown。 |
| P0-05 | pass | stdio、localhost、Node 可达 HTTP/SSE locality matrix。 |
| P0-06 | pass | 两个 fresh session 读取同一隔离状态。 |
| P0-07 | pass | Chat save/list/hydration 五字段 round trip，无 schema 变化。 |
| P0-08 | historical Go | 仅对应上述旧 npm lock 与源码指纹；production Apps 仍关闭。 |

## 5. 当前缺口

当前候选不能继承上述 `Go`。至少需要：

1. 记录唯一 `frontend/pnpm-lock.yaml` digest 与依赖树；
2. 在当前 Browser 入口重跑 P0-04；
3. 核对 P0-02/P0-03/P0-05/P0-06/P0-07 的源码、制品和运行入口指纹；
4. 根据当前证据原位形成新的 P0-08 `Go|No-Go`。

## 6. 回滚

只清理本轮具名 PoC 进程、端口、测试 fixture 和临时证据。不得回退普通 MCP/Chat、数据库、用户改动或其他任务文件；任何当前重验失败都保持 `production_apps_effective=false`。
