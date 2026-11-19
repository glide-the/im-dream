<!-- [Input] 已授权的本机Web Bearer发布、既有生产制品与真实账户只读Chat验收。 -->
<!-- [Output] 本机发布、可回滚构建、真实认证闭环、请求计数与ARMS证据。 -->
<!-- [Pos] 发布执行记录；正常业务规则归Web认证设计。 -->

# Web Bearer发布执行记录

## 范围与当前状态

用户已澄清Dream Web只在本机使用，当前发布目标为正常5173入口；公网Dream发布与Natapp退出本轮范围。发布内容为Dream Web Bearer迁移；Admin、Python、Gateway、PostgreSQL、原生安装和用户已有未提交修改保持原所有者。本轮不调用模型，不发送Chat消息，不修改指定Thread内容。

正常本机服务为`localhost:5173`的Next生产服务和`127.0.0.1:8765`的Python。原Next PID为47564，原制品目录为`/Users/dmeck/project/.ink-dream-web-releases/20261119-final-22167680.0t4xav`，BUILD_ID为`yrXg1YWOwl8EO6zLWaUZ2`，登记提交为`3c8ddac16b7d8ec1285fd1344686b78b464f73a8`。本轮源码为该develop提交加工作区Bearer迁移；制品另外登记源码清单摘要。

最初按转交信息检查公网时，ECS `39.97.252.88`的nginx将`ink-frontend.suoxya.com`和`ink-backend.suoxya.com`转发到`https://dream.suoxya.com`；Admin域名独立转发该ECS的3000端口。两条本机Natapp进程存在，当前公网Dream根页面及健康均404；本机根页面与健康均200。既有Natapp日志最后记录1104过期错误，文件时间为2026-11-16；公网404在本轮切换前已经存在。该历史入口检查不作为当前本机发布的阻塞条件。

## 真实验收影响范围

| 对象 | 入口与数据所有者 | 本轮影响 |
| --- | --- | --- |
| 当前账户 | 既有Chrome、Admin正常登录/OAuth、正常业务数据库 | 验证同一账户、刷新恢复、自然续期与退出 |
| Chat Thread | 既有指定Thread与公开Chat页面 | 只读历史，记录状态和消息数量，排除正文 |
| Project与Episode | 既有规范文件和Admin投影 | 范围外 |
| canonical Artifact与Run私有.dream发布 | 原Agent和Hook | 范围外 |
| Run、模型、结算 | 原生产链路 | 不创建Run或模型调用 |
| 浏览器网络 | 实际公开入口与原授权链 | 仅记录方法、路径模板、凭据存在性、状态和Trace ID |

## 构建与回滚准备

macOS arm64、Node v24.13.0、Next 16.1.6；物理内存16 GiB，可回收容量按`memory_pressure -Q`约32%，磁盘约8.4 GiB可用。macOS无Linux cgroup层；保留现有主机交换策略。构建只运行一份，使用原`pnpm run build`的`next build --webpack`，完整类型检查与锁文件保持。

候选在原`.ink-dream-web-releases`独立目录准备，复用锁定node_modules；原服务`.next`和原制品保持。已核对Next实际worker代码：`CIRCLE_NODE_TOTAL=2`使静态worker为1；webpack和类型worker各1，阶段依次执行。构建堆上限2 GiB；静态worker沿Next隔离内存规则移除该参数，预算覆盖约4.2 GiB默认堆及宿主余量。监控本轮进程组，达到预算或期限即终止该构建，原服务保持。

候选先在自有临时Web端口进行健康与静态制品检查；真实认证使用已注册的正常5173入口。切换保留原PID身份、制品、环境文件、依赖与原启动命令的恢复能力。认证或请求回归即恢复原制品。当前只对本机正常入口执行真实验收，ARMS继续使用既有线上服务。

## 执行回执

### 独立制品

- 新制品：`/Users/dmeck/project/.ink-dream-web-releases/20261120-web-bearer-001503`。
- BUILD_ID：`uHgNnGNCYKOrpr9mfFyPB`；源码1223文件，摘要`2826a5d75328571a668e98e9cd2e83e49eafc5d60994c7e61aee709e6c7c9a03`。
- 命令：在独立frontend快照执行`CIRCLE_NODE_TOTAL=2 NODE_OPTIONS=--max-old-space-size=2048 INK_TRACE_ENABLED=false NEXT_TELEMETRY_DISABLED=1 pnpm run build`，退出0；完整编译和类型检查完成，约30秒，进程组RSS峰值1888 MiB。
- 初次快照误包含原生编译缓存，已经终止本轮自有准备/构建进程并删除两份不完整快照；原制品、依赖和服务保持。后续快照排除ios/android构建树，单份Web构建通过。
- 自有15173候选健康和根页面200，11个静态资源全部200；浏览器bundle包含新的Web OAuth owner。
- 实际线上Admin capability调用成功，正常本机授权入口303；client为`ink-dream-browser-local`，callback为`http://localhost:5173/auth/callback`，resource为`https://ink-frontend.suoxya.com/api`，S256 PKCE保持。
- 范围澄清前的nginx头配置探测返回303，投影公网callback为`https://ink-frontend.suoxya.com/auth/callback`。该探测作为历史记录保留，公网端到端认证移出本轮范围。现有resource值继续作为OAuth audience标识。

### 正常5173入口

2026-11-20 00:19（Asia/Shanghai），沿原独立制品Next入口切换5173，原PID47564退出，新PID27880，健康200。原制品完整保留，rollback脚本按PID、cwd、监听端口和BUILD_ID核对后恢复。Admin、Python、Gateway、数据库与Natapp/nginx均未重启或修改；自有15173候选已关闭。

切换后新Web正常显示登录表单。正常`/auth/start`进入线上Admin重新认证，使用用户提供的原账户在正常页面提交，登录callback回到本机Chat。profile返回200且账户匹配，刷新页面触发真实OAuth refresh 200并恢复公开用户。指定Thread通过现有活动/历史侧栏打开，历史接口200、Thread匹配，读取10条消息且页面已呈现；网络为Bearer、Cookie缺失。

刷新后的完整网络窗口覆盖80个受保护请求，Bearer缺失0、Cookie存在0、HTTP错误0、模型POST 0。两次`/auth/refresh`均200，间隔370秒；第二次由Access自然到期后的正常历史读取触发，历史接口随后200，页面呈现10条消息。测试未修改浏览器时钟。

通过现有用户菜单执行Logout，`POST /auth/logout`返回200，页面回到Welcome Back。再次刷新后保持未登录，受保护请求派发数为0。证据排除密码、Token、账户标识和消息正文，保存于`output/playwright/web-bearer-release-20261120/real-acceptance.json`；退出截图为同目录`signed-out.png`，裁剪范围只包含通用登录标题与Google入口。

浏览器观察器在跨域登录返回后重新启用；早期窗口的阶段标签存在闭包捕获问题，最终80请求计数采用重新建立的可变状态对象。最终窗口`windowComplete=true`，无截断；早期有效HTTP回执单独作为补充，未并入最终请求计数。

### ARMS与范围收敛

新制品健康请求HTTP200，Trace ID为`27014d59e29770c74ae8235f2908697f`。北京ARMS详情显示新的Next健康操作，列表1个Span、handle resolve为0。该健康Trace用于验证遥测到达。

指定Thread的首个历史Trace `5a443a3cac1f313feeb555c5c259c2ff`已核对完整列表248行，`browser-sessions/resolve`为0。最终完整浏览器窗口的历史Trace为[`c577113114b97bf8dd5a5b63ce8aa07b`](https://cmsnext.console.aliyun.com/next/region/cn-beijing/workspace/default-cms-1230976711767463-cn-beijing/app/apm/trace-detail?regionId=cn-beijing&traceId=c577113114b97bf8dd5a5b63ce8aa07b&startTime=1795105493215&endTime=1795107293215)，ARMS完整列表221行，`browser-sessions/resolve`为0，`/principal`和`chat-message.page`保留。自然续期后的历史Trace为`0bfbc120e9287376a9f15e01b8ea9fef`。本轮确认认证handle解析链路已移除，整体历史耗时改善未做同条件测量。

范围澄清前，为恢复同一Dream入口准备了本轮独立SSH回环转发，ECS回环健康与静态资源摘要和本机候选一致。nginx尚未修改，转发未接入公网。用户明确只发布本机后，已bootout并删除本轮独立转发、配置及自有日志；原Natapp、nginx、Admin和数据保持。Natapp无需在本轮登录、续费或修复。

### 当前验收状态

| 项目 | 状态 |
| --- | --- |
| 生产构建、完整类型检查、静态制品 | 通过 |
| 正常5173切换及健康 | 已发布；PID27880、BUILD_ID匹配，健康200 |
| 正常账户与指定Thread只读 | 已登录，profile/历史200，账户和Thread匹配，10条历史消息 |
| 自然续期、刷新恢复、退出 | 通过；refresh 200/200，logout 200，退出后刷新保持未登录 |
| 新业务请求Bearer、Dream Cookie缺失及resolve=0 | 80个受保护请求全部Bearer/无Cookie；完整业务Trace的resolve=0 |
| ARMS新进程数据到达 | 健康和真实业务Trace均通过 |
| 公网及Natapp | 用户明确移出范围；本轮准备的转发已撤除，nginx保持 |

### 最终检查与恢复

2026-11-20 00:44（Asia/Shanghai）最终身份检查退出0：5173监听PID27880、cwd与BUILD_ID均匹配新制品，健康200，原制品完整保留，8765继续由原PID12060监听，自有15173已关闭，本轮转发LaunchAgent已撤除。发布元数据和最终验收JSON保存在新制品目录；原制品恢复入口为`python3 /tmp/switch-web-bearer-release.py rollback`，执行前自动核对当前服务身份。

首次终端urllib健康探测经宿主代理得到502；`curl --noproxy '*' --max-time 15 -sS -o /dev/null -w '%{http_code}\n' http://localhost:5173/api/health`退出0、HTTP200，直接连接本机的`http.client`身份检查随后退出0。浏览器真实验收窗口HTTP错误计数保持0。

独立文档验证：`python3 /tmp/web-bearer-doc-check.py`退出0，检查29个Markdown与131条本地引用，新增缺失0、继承缺失0、目录失败0；`git diff --check`退出0；`rg -n 'web-bearer-release-20261120\.md' docs/exec/.folder.md`退出0。两份执行记录的禁用逻辑话术计数为0。初始实现阶段文字已补充日期边界，最终采用状态归2026-11-20本机验收。代码保持未提交状态，源码清单与BUILD_ID定位当前采用制品。
