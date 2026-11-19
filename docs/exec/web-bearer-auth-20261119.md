<!-- [Input] Web认证迁移范围、当前develop与本轮分层命令回执。 -->
<!-- [Output] 交付项、技术验证、兼容边界及后续本机真实采用记录。 -->
<!-- [Pos] 项目执行记录；认证规则归正式设计，状态以本轮回执更新。 -->

# Web Bearer认证迁移执行记录

## 范围与基线

工作区为`/Users/dmeck/project/ink-dream-memory`，分支`develop`。`git fetch origin develop`退出0，`git rev-list --left-right --count develop...origin/develop`为`0 0`，HEAD为`3c8ddac16b7d8ec1285fd1344686b78b464f73a8`。本轮开始已有`docs/exec/.folder.md`修改与`docs/exec/iphone-latest-install-20261119.md`，均保留。2026-11-19实现阶段未切换分支、提交、推送或部署，后续本机采用登记于末节。

目标为Web登录后的业务请求、续期与退出使用OAuth凭据，业务请求直接发送Bearer并停止调用`browser-sessions/resolve`。需求提供的Trace解析耗时为2.46秒，本轮未重新测量该Trace或宣称同等耗时改善。

## 交付项

| 工作项 | 交付物 | 状态与证据 |
| --- | --- | --- |
| 登录与当前用户 | 原PKCE交易、CSP完成文档、Bearer principal/profile | 源码完成；隔离OAuth及浏览器验证 |
| 续期与退出 | 内存Access、sessionStorage仅Refresh、single flight与成功后清理 | 源码完成；并发、取消、轮换、撤销及失败保留合同 |
| 业务代理 | 显式Bearer优先；Web fetch省略Cookie；Python/Admin原权限链 | 源码完成；代理与Node Apps技术合同 |
| Chat与文件 | 原SSE/Stop协议、FormData、Blob图片与下载 | 源码完成；隔离浏览器三个场景全部通过 |
| 原生兼容 | 原Cookie owner、私有协议callback、Device边界 | 原生类型和原Cookie合同通过；真机未执行 |
| 文档 | [认证设计](../design/web-bearer-auth.md)、现行架构及目录清单 | 已更新；历史Cookie原文独立保存 |

## 已取得的验证

所有技术验证使用注入transport或本轮Vite随机端口，不连接真实业务数据库，不调用模型，不启动替代Admin/Gateway。浏览器使用本机Chrome；测试进程按fixture生命周期关闭。现有5173和8765保持原PID与服务所有权。

| 命令 | 目录 | 退出码 | 结果 |
| --- | --- | --- | --- |
| `node --test --experimental-strip-types app/api/_auth/api-proxy.test.ts app/api/_auth/handlers.test.ts app/api/_auth/login-boundary.test.ts app/api/_auth/runtime-request.test.ts app/api/_auth/retired-auth.test.ts app/api/_auth/web-oauth.test.ts app/_dream/lib/browserSession.test.ts app/_dream/lib/browserSession.web.test.ts` | frontend | 0 | 89通过；OAuth、Cookie兼容、Bearer、代理/SSE/abort、Node Apps与竞态合同 |
| `npx playwright test e2e/web-bearer-auth.spec.ts --reporter=line --workers=1` | frontend | 0 | 3通过；约35.1秒；零页面运行错误 |
| `npx tsc --noEmit --pretty false` | frontend | 0 | 类型检查通过 |
| `pnpm native:typecheck` | frontend | 0 | 原生类型检查通过 |
| 认证修改文件的`npx eslint` | frontend | 0 | 零error；4条AIInputDock既有Hook依赖warning |
| `PYTHONPATH="$PWD:$PWD/.venv/lib/python3.12/site-packages" uv run --no-project --python .venv/bin/python --with pytest==8.4.2 python -m pytest tests/test_admin_request_auth.py -q` | backend | 0 | 58通过；JWT claim/主体/profile/scope公开边界，httpx MockTransport，无PG或模型 |
| `python3 /tmp/web-bearer-doc-check.py` | 仓库根目录 | 0 | 28个Markdown、130条本地引用、零缺失、目录条目完整 |
| `node --input-type=module < /tmp/check-web-bearer-mermaid-browser.mjs` | frontend | 0 | 本机Chrome解析8个Mermaid图成功 |
| `git diff --check` | 仓库根目录 | 0 | 零空白错误 |

正常backend虚拟环境缺少pytest；补充检查通过uv临时环境使用固定版本pytest，只读复用原依赖。正常`.venv`、manifest及lock均保持原状。Mermaid的Node解析缺少浏览器DOM，Vite的ES module路径触发dayjs导出问题；最终使用仓库自包含Mermaid包在本机Chrome完成语法解析。

### 浏览器网络证据

| 场景 | 业务请求数 | Bearer缺失/Cookie或CSRF存在 | handle resolve | 其它计数 |
| --- | --- | --- | --- | --- |
| 登录、私有图片、下载上传、Chat SSE/Stop、刷新页面、退出 | 8 | 0 | 0 | grants=1，refreshes=1，revokes=1 |
| 过期并发续期与已撤销Refresh | 26 | 0 | 0 | refreshes=2 |
| 临时续期/退出故障与重试恢复 | 35 | 0 | 0 | refreshes=2，revokes=2 |

共69个业务请求。专用`/auth/refresh`和`/auth/logout`使用JSON刷新凭据并省略Cookie；业务请求和`/auth/session`均携带Bearer并省略Cookie及旧CSRF头。证据仅含路径、方法、凭据存在性和计数，保存于仓库`output/playwright/web-bearer-auth-20261119/`的`login.json`、`expired.json`和`recovery.json`；OAuth callback查询、Token和业务正文均排除证据文件。

## 发现与修复

- 首轮旧Cookie优先断言与新的显式Bearer合同冲突，已按凭据实际选择更新。Cookie-only原生合同保持。
- 首次浏览器运行被fixture路径alias阻塞，已修复全路径匹配；该次结果归harness失败。
- 撤销并发场景发现失效Refresh后的等待请求仍发送无Bearer业务请求。已在Web认证边界停止派发并补充12请求合同；最终Node与完整浏览器回归均通过。

## 初始实现阶段的采用边界

2026-11-19技术验证结束时，正常本机Web、Python、在线Admin与真实账户尚未运行这批源码的业务验收。该阶段未执行真实Google登录、真实模型调用、物理设备安装或部署；隔离SSE证据验证生产transport及协议。2026-11-20真实账户采用状态见下节。

2026-11-19技术验证结束时，本机已有Next服务保持原运行制品。该阶段容量核对显示16 GiB物理内存、约3.9 GiB磁盘可用，既有`.next`约1.0 GiB；实现阶段未占用原服务输出目录构建。后续生产构建与真实服务切换记录于本机发布执行记录。

Web上传由fetch保证省略Cookie，进度展示保留开始和完成；原生平台进度保持。刷新凭据在当前标签页可被同源脚本读取；关闭、恢复或复制标签页的行为，以及未知轮换响应后的重新登录，按[设计规则](../design/web-bearer-auth.md)执行。

## 后续本机采用

2026-11-20已在正常`localhost:5173`采用独立生产制品，BUILD_ID为`uHgNnGNCYKOrpr9mfFyPB`。既有账户登录、刷新恢复、Access自然到期续期、指定Thread的10条历史读取及退出后刷新均通过；完整窗口80个受保护请求全部Bearer且无Cookie，ARMS业务Trace的handle resolve为0。模型调用为0。容量、恢复路径、真实业务与云端证据见[本机发布执行记录](web-bearer-release-20261120.md)。公网Dream与Natapp按用户指示移出范围。
