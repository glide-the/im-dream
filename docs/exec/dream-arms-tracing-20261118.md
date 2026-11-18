<!-- [Input] Authorized server trace implementation and isolated verification scope. -->
<!-- [Output] Work items, validation receipts and separate remote/cloud delivery status. -->
<!-- [Pos] Dated project execution record; operating instructions remain in ../deploy/dream-arms-tracing.md. -->

# Dream ARMS 调用链交付记录

## 范围与判断

任务目标为一次 Deck 页面打开中的 `POST /api/decks/defaults/reconcile` 提供 BFF、Python、Admin 和本地插件校验的耗时关联。负责人为本会话主代理；确定性验证由 `luna_test_runner` 执行。

发现阶段核对当前主分支 `develop`、原工作区和已有独立工作区草稿，合入主分支最新 `c63a132f` 后继续实施。原工作区干净，未覆盖其他任务交付。现有实现先执行 reconcile 再读取目录；Admin 已有服务器 preload 及 W3C 父级采样合同，独立 Dream 服务缺少追踪装配。

范围选择为共享 BFF 工厂、ASGI 外层、现有认证与 Admin HTTP 边界，以及两段本地插件校验。逐路由复制和全量自动探针会扩大采集范围与重复 Span，方案采用专用 provider 和固定元数据接缝。浏览器输入由 BFF 根上下文隔离，服务间签名保留内部父级。Admin 代码维持现行实现，本轮无需 Admin PR。

交付物为 [运维指南](../deploy/dream-arms-tracing.md)、Python 可选 tracing 依赖、Next 服务端依赖、源码接缝、隔离合同和移动包配置防护。功能入口、页面顺序、OAuth/CSRF、Admin DTO、原重试、回执、取消和 SSE 保持原合同。

## 验证记录

| 阶段 | 命令 | 回执与边界 |
| --- | --- | --- |
| 第一轮后端回归 | `cd backend && .venv/bin/python -m pytest -q tests/test_admin_deck_default_routes.py tests/test_deck_defaults.py tests/test_admin_request_auth.py tests/test_admin_data_boundary.py tests/test_admin_service_token.py` | exit 1；189 passed，1 failed。原 `test_screenplay_and_music_are_active_system_templates` 缺少 repository-local 音乐 marketplace；本轮未改该测试或 resolver |
| 原代理合同 | `cd frontend && node --test --experimental-strip-types app/api/_auth/api-proxy.test.ts` | exit 0；13 passed |
| 类型检查 | `cd frontend && corepack pnpm exec tsc --noEmit --pretty false --incremental false` | exit 0；完整前端类型检查 |
| 新追踪合同初轮 | `cd backend && .venv/bin/python -m pytest -q tests/test_observability.py` | exit 1；11 passed，1 failed。隔离 collector 缺少 chunked 读取，已补充 harness 协议处理；业务结果、签名关联和清理已通过对应断言 |

最终候选验证回执如下。初轮类型检查生成的原 `tsconfig.tsbuildinfo` 已恢复，仅测试自建 loopback 监听与进程执行清理。无数据库、真实账号、模型或线上业务写入。

## 交付与验收状态

- 实施：源码、运维说明和隔离验证已进入本轮工作区；最终验证与远程收据追加于下方。
- 远程交付：按仓库默认主分支 `develop` 创建 PR，保留现行 GitHub 检查与正常合并流程。
- 云端验收：待后续单独授权部署与配置；本轮未部署、未重启、未修改服务器或 ARMS 云配置，未触发真实 reconcile 或模型调用。
- ARMS 到达：待部署后按同一 Trace ID 查到 Dream BFF、Python、Admin 与实际 pg 子段；本机 exporter 和替身接收结果归隔离集成证据。

## 最终候选验证

| 命令 | 退出码 | 关键结果 |
| --- | --- | --- |
| `cd backend && .venv/bin/python -m pytest -q tests/test_observability.py tests/test_admin_deck_default_routes.py tests/test_admin_request_auth.py tests/test_admin_data_boundary.py tests/test_admin_service_token.py tests/test_deck_defaults.py -k 'not test_screenplay_and_music_are_active_system_templates'` | 0 | 202 passed，1 deselected；排除项为上表已记录的缺失 marketplace 资源 |
| `cd backend && .venv/bin/python -m pytest -q tests/test_observability.py` | 0 | 最后追加真实 loopback OTLP 拒绝用例后 14 passed；确认业务先返回，导出失败日志隐藏接入点授权路径与响应正文 |
| `cd frontend && node --test --experimental-strip-types app/api/_auth/api-proxy.test.ts e2e/trace-contract.test.ts` | 0 | 14 passed；原 13 项代理合同与启用追踪的流式/取消/隐私 |
| `cd frontend && corepack pnpm exec tsc --noEmit --pretty false --incremental false` | 0 | 完整前端类型检查 |
| `uv lock --check --project backend` | 0 | 82 个锁定包解析一致 |
| `cd backend && uv export --locked --extra tracing --no-dev --no-emit-project --no-header --quiet`，逐行比较导出正文与 `requirements.txt` | 0 | 带 hash 的 tracing 依赖清单一致；既有依赖版本保持 |
| `git diff --check` 与本轮 Markdown 清单、相对引用、文档用语脚本 | 0 | 两份新增正文均有目录清单记录，相对链接存在，文档用语通过 |
| `cd frontend && node --input-type=module`，读取运维文档并逐块 `await mermaid.parse(block)` | 0 | 两张 Mermaid 时序图解析成功 |

跨语言用例通过原 Cookie/CSRF 和 AdminBffClient handle 解析，HTTP 进入隔离 Python，继续普通认证依赖、Deck 路由与实际 Admin DTO 构包，确认 BFF client → Python server → Admin receive 替身的 Trace ID 和父子关系。另覆盖无签名、错误签名、过期、路径不匹配、重复头、未采样、401、插件409、未处理500、关闭时缺少可选 SDK，以及移动包环境防护。

本轮没有发起真实账户、真实数据库或真实模型操作；测试自建进程、随机端口和 collector 均已结束。原音乐插件资源缺失项保持明确失败记录，未引入替代数据，也未调整其断言。
