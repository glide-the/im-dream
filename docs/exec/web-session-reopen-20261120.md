<!-- [Input] 用户要求localhost:5173关闭重开保持登录、既有Bearer设计与正常Chrome会话。 -->
<!-- [Output] 持久恢复、跨标签轮换及退出的交付、技术回归和真实入口验收。 -->
<!-- [Pos] 本机会话恢复执行记录；现行认证规则归Web Bearer设计。 -->

# Web关闭重开会话恢复

## 范围与问题

用户反馈重新打开`http://localhost:5173/`后会话未保留。原实现把Refresh存入sessionStorage，仅覆盖同一标签页刷新；关闭标签页结束存储生命周期。2026-11-20早前发布记录的刷新验收保持为历史证据，本次补充关闭重开及跨标签场景。

正常5173当前由用户VS Code启动的Next dev提供，Next子PID70617、父PID70615，cwd为本仓库frontend，沿原online preloader连接正常Admin。现有`.next/BUILD_ID`属于磁盘历史制品，当前dev身份由实际父进程确认。源码由正常开发入口加载，本次无需切换生产制品或重启用户服务。之前的backend诊断改动及iPhone记录保持。

## 业务概念与影响

| 对象 | 真值与所有者 | 预期影响 |
| --- | --- | --- |
| 账户登录 | Admin OAuth授权、正常Chrome、Dream公开认证入口 | 变更：关闭重开恢复；同源标签页同步登录与退出 |
| 现有Thread与历史 | 正常Admin业务接口、既有账户归属 | 保持：只读现有页面；消息正文排除证据 |
| Project与Episode | 规范文件与原投影owner | 范围外 |
| canonical Artifact与Run私有.dream发布 | Agent及after-turn Hook | 范围外 |
| PostgreSQL/API投影、Run和模型 | 原正常Admin/Gateway/PostgreSQL | 保持：无测试数据写入、无模型或消息提交 |
| 最终UI消费者 | localhost:5173的AuthProvider与既有页面 | 变更：先续期和profile，再恢复已登录页面 |

## 方案与交付

内存Access保持原Bearer业务链路。localStorage只保存Refresh与随机登录标识，callback保留一次性sessionStorage交付，初始化后删除。刷新、关闭重开和新标签页先调用原OAuth续期；Admin grant有效期与权限保持。

同源Web Lock串行处理callback、旧标签凭据迁移、轮换和退出，等待方重新读取最新Refresh。各标签页单独保存内存Access。storage事件只在登录替换或删除时重建公开用户；同次登录的Refresh轮换保留当前用户。迟到续期在保存前核对登录标识与旧Refresh，防止恢复已退出状态。

技术浏览器场景使用自有临时Chrome profile与端口0：真实PKCE生产handler加MockTransport，关闭Chrome并重启同一profile、并发新标签页、跨标签退出及再次重启，另覆盖原sessionStorage迁移。该场景单独标为Provider-free技术验证。真实验收复用用户Chrome及正常localhost:5173、Admin和账户；仅操作登录、重新打开及读取，保持最后可使用的登录状态。

## 验证回执

首轮Luna回归：91项认证合同、Web与原生类型检查通过，5个Chrome场景通过，51.9秒；业务Bearer覆盖100%，Cookie/CSRF存在0，resolve 0，页面错误0。7个认证文件ESLint无warning/error；16个Markdown及48条引用检查通过；8个Mermaid图由本机Chrome解析通过。

真实Chrome首次刷新遇到`/auth/refresh`和`/auth/options`503；随后正常options探测恢复200，约2.55秒。授权回调显示`BFF_REQUEST_FAILED`。源码复核发现进程全局Admin客户端可跨Route模块或热更新保留，错误的构造函数身份随模块改变，原instanceof会把另一模块的认证错误转成通用503。已为BffBoundaryError加入共享Symbol身份，并按同一协议标识替换旧缓存；跨模块的401与普通对象拒绝分别加入合同验证，相关回归重新执行。

补充错误身份合同后的技术回归：92/92项Node认证合同通过，Web类型检查与3文件ESLint通过，5/5项隔离Chrome场景通过，50.1秒；业务Bearer、无Cookie/CSRF、resolve 0及页面错误0继续满足。原生类型检查沿首轮通过回执。

终审补充跨标签迟到profile竞态：profile响应提交或处理401前重新读取持久记录，storage事件仍在排队时也可识别替换登录。新增合同分别验证旧200和401均保留replacement grant。最终93/93项Node合同、Web类型与两文件ESLint通过，5/5项隔离Chrome场景通过，38.7秒；算法、权限和原生路径保持。

2026-11-20 15:36（Asia/Shanghai）真实账户验收通过。正常授权回调返回Chat，原有标签页同步恢复，页面账户匹配。关闭本轮独立标签页后重新打开正常根入口，`/auth/refresh`200且Cookie缺失，`/auth/session`携带Bearer且无Cookie，完整profile正文在观察器内解析为账户匹配布尔值，页面恢复已登录状态。随后通过现有设置入口打开受保护页面。开发模块网络事件量触发观察器截断，真实记录仅作为单接口及最终UI回执，完整请求计数归隔离Chrome窗口。

本轮独立标签页全部关闭，用户原标签页保留已登录状态。真实Chrome进程未重启；完整Chrome进程关闭重启由隔离profile场景覆盖。正常5173及8765未重启，Admin、Gateway与数据保持。本轮消息提交和模型调用发起均为0。真实回执保存于`output/playwright/web-session-reopen-20261120/real-session.json`；`restored-session.png`只包含通用设置区域，排除账户与正文。

| 命令 | 目录 | 退出码 | 最终结果 |
| --- | --- | --- | --- |
| `node --test --experimental-strip-types app/api/_auth/api-proxy.test.ts app/api/_auth/handlers.test.ts app/api/_auth/login-boundary.test.ts app/api/_auth/runtime-request.test.ts app/api/_auth/retired-auth.test.ts app/api/_auth/web-oauth.test.ts app/_dream/lib/browserSession.test.ts app/_dream/lib/browserSession.web.test.ts` | frontend | 0 | 93通过，零失败/跳过 |
| `npx playwright test e2e/web-bearer-auth.spec.ts --reporter=line --workers=1` | frontend | 0 | 5通过，38.7秒；关闭重开、并发轮换、跨标签退出和旧凭据迁移 |
| `npx tsc --noEmit --pretty false` | frontend | 0 | 最终Web类型检查通过 |
| `pnpm native:typecheck` | frontend | 0 | 原生类型检查通过 |
| 修改文件的`npx eslint` | frontend | 0 | 首轮7文件及补充3文件均无warning/error |
| `node --input-type=module < /tmp/check-web-bearer-mermaid-browser.mjs` | frontend | 0 | 本机Chrome解析8个Mermaid图 |
| `python3 /tmp/web-bearer-doc-check.py` | 仓库根目录 | 0 | 16个Markdown、48条引用，新增/继承缺失和目录失败0 |
| `git diff --check` | 仓库根目录 | 0 | 无空白错误 |

隔离fixture、随机端口及临时Chrome profile均由测试关闭或移除；Luna恢复本轮类型检查缓存，正常服务保持。2026-11-20现场采用时源码保持未提交状态，前次backend诊断和用户iPhone文档继续保留。

## 2026-11-26集成复核

本次Git交付以默认分支develop的`39fb4b8a`为基线，在独立工作树提取会话恢复及认证诊断的29个文件。其他任务的源码、设计修订和iPhone记录保留在原工作区，共享目录文档只提取本次段落。

Luna重新执行上述Node认证合集、Web及原生类型检查，退出码均0；Node 93/93项通过。Chrome隔离浏览器5/5项通过，耗时7.3秒，未下载浏览器。后台认证诊断的117项Provider-free回归通过。真实账户回执归2026-11-20现场，本次集成验证只使用MockTransport、注入writer和隔离Chrome profile。
