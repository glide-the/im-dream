<!-- [Input] Original task receipts, current local service observations and production Next/Browser sandbox owners. -->
<!-- [Output] Minimal dynamic-entry recovery design, review and separate live versus isolated evidence. -->
<!-- [Pos] Local recovery receipt; not production enablement or a second Host design. -->
<!-- [Sync] 2026-09-13: replace fixed-port sandbox configuration with the actual frontend entry and enforced opaque isolation. -->

# MCP Apps 本机恢复与动态入口

## 背景与问题

原任务“MCP APP功能新增”（`01a07262-9a8d-7391-ab2c-59c754b5fa08`）
协调“MCP Apps 全阶段实现与验收（Sol）”
（`01a07268-c717-7961-b5fd-e0e8436d674f`）。旧回执覆盖真实 `get-time`
页面、时间按钮、Chat 消息和历史恢复；后续按用户要求停止了任务自有服务。
历史指令仅用于核查过程，不作为本轮操作授权。

本轮失败探测早于官方示例进程启动；重新进入连接详情后发现成功：
1 Tool、1 Resource、0 Prompts，工具 `get-time`，资源
`ui://get-time/mcp-app.html`。真实历史 Host 请求已成功且四项 effective 能力
均 enabled，但沙箱 URL 指向已停止的固定端口，父来源配置也与实际入口别名不符。
用户明确要求沙箱随前端入口动态变化，不能另建固定端口代理。

## 目标与边界

- 恢复真实 Dream→Python 配置→Next Host→官方 MCP→App 页面链路。
- 沙箱 URL 随实际前端协议、主机名、端口变化；正常启动 Next 即提供页面。
- 不另启 Host 或沙箱监听器，不增加代理、数据库 migration、依赖、配置面板或模型调用。
- 保持认证、连接 revision、低风险 positive list、CSP 和两层 iframe 隔离。
- 普通结果始终保留；不修改 SDK／Runtime 版本或 `productionAppsEffective=false`。

## 概念与规则

1. status 返回版本和插件 revision 绑定的根相对路径 `/mcp-apps-sandbox`。
   Browser 以真实入口解析完整 URL，只接受当前 origin 下的该路径；不按端口加一，
   不从环境标签推断入口，也不接受旧独立域名、端口或任意页面路径覆盖。
2. 现有 Next route 提供页面，沿用已验证的 public Host/protocol parser 精确绑定
   父页面来源。浏览器不得提供代理目标；旧 `INK_MCP_APPS_SANDBOX_URL` 与
   `INK_MCP_APPS_PARENT_ORIGINS` 不再决定挂载或父来源。
3. **URL 来源与文档有效来源不同。** 两层 iframe 均仅有 `allow-scripts`，
   外层 HTTP CSP 另强制 `sandbox allow-scripts`。文档实际 origin 为 `null`，
   不能访问父 DOM 或存储；消息仍检查精确 `event.source` 和对应来源。
   外层移除 iframe 属性也不能解除响应 CSP 的限制。Web permissions 与关闭网络的
   resource CSP 不变。
4. 这是 Dream 已有的严格零权限 technical-preview profile，不声明实现标准中
   带 `allow-same-origin` 的通用独立域名宿主模式。未来若增加该 token 或 Web
   capability，必须重新设计独立来源，不能沿用同入口 URL 直接放宽。
5. 工具发现仍为 cache-first。先启动外部 MCP Server，再进入详情；旧失败缓存
   按原 TTL 失效，不新增强制刷新按钮或无限轮询。
6. 通过现有 **Try interactive view again** 重试已降级的 App，不重放历史初始工具。
   App 时间按钮仅局部调用，不启动模型；消息按钮仍是当前 Chat 的新 turn。

## 设计评审

发现、可信投影、权限与 Host 生命周期已符合目标，不重写。只修改沙箱 URL 组合、
Browser URL 校验、现有 sandbox route 的精确父来源与 CSP，并复用公开请求来源解析。
隔离 harness 改为一个随机前端入口，刻意传入过期配置验证其不能钉死 URL。
无需新启动脚本、第二进程、端口注册或额外部署体系，符合最小修复目标。
README 同时校正已过期的“保存使用策略”说明为当前自动保存。

## 验证记录

- 修复前真实浏览器：匿名连接成功，发现响应 `complete`、无 error；历史 Host
  认证成功且 effective 四项 enabled。普通结果保留，未启动新模型消息。
- 确定性验证：Host policy 5 tests passed；Runtime 39 tests passed；MCP Apps
  及全前端 TypeScript 检查通过。两个需要随机监听端口的测试在允许测试监听后通过。
- 隔离 Chrome 回归：官方 1.7.4／1.7.5 协议 smoke、1.7.5 生产 Host 完整生命周期、
  window.im policy downgrade 共 4 tests passed（12.1s）。同前端随机入口挂载成功；
  两层文档 origin 均为 `null`，父 DOM／存储被拒；过期 URL／父来源配置不影响挂载。
  时间按钮、消息回流、历史不重放和标准 DELETE 回归均保留。
- 修复后真实页面结果待本轮验证，不用隔离 harness 或旧验收冒充真实业务通过。

## 本机操作与隔离回归

沿用已有 Admin、Python 后端与 Next 前端；另启官方 MCP Server。
无需手动清单第五个沙箱进程，详见 [README](../../../README.zh.md#本机预览服务)。
不为测试清理停止用户服务。

```bash
cd frontend
INK_MCP_APPS_OFFICIAL_ARTIFACT_CURRENT=/absolute/path/to/server-basic-vanillajs-1.7.5 \
INK_MCP_APPS_OFFICIAL_ARTIFACT_PREVIOUS=/absolute/path/to/server-basic-vanillajs-1.7.4 \
corepack pnpm exec playwright test \
  e2e/mcp-apps/phase-1/official-phase1-3.spec.ts \
  e2e/mcp-apps/phase-1/window-im-runtime-policy.spec.ts --reporter=line --workers=1
```

路径必须指向已准备的官方制品根目录，沿用安装的本机 Chrome。
该 harness 只证明生产模块技术合同，不证明真实账号、模型、OAuth 或消息结算。
