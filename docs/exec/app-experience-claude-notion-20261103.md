<!-- [Input] Notion原反馈、IMG_9153/9154、当前iOS资源打包和Notion Read调用链。 -->
<!-- [Output] APP-07根因、最小方案评审、源码范围、分项验证回执与剩余依赖。 -->
<!-- [Pos] App体验APP-07执行记录；真实账户、Simulator、物理设备及发布分别记录。 -->
<!-- [Sync] 2026-11-03: 原账户Read正文、Bash CLI搜索及Stop已验证；Transport补PATH默认值，20项目标回归通过，完整新包与手机资格单列。 -->

# APP-07：iOS Claude工具与Notion正文读取

## 目标与授权边界

修复现有端侧Claude工具执行与已选Notion资源的正文读取，保留原React Native、嵌入式Python、Node Worker、Linux ARM64解释执行、HTTP接口、认证、权限及Thread关系。任务启动基线为`ios-store@97f35b6d`，使用用户现有工作树；本轮自有修改按下表归属，其他任务改动保留。任务启动时物理iPhone构建29供用户手动测试，本任务设备安装和操作为0。APP-04保持用户暂停，前后台恢复实施和行为验收为0。

任务：[本对话](codex://threads/01a1a03a-0eba-7370-bef2-575887c4f68d)。[总清单](app-experience-fixes-20261102.md)登记为APP-07。[反馈原文与原图](https://app.notion.com/p/40b30b7547c380f7ac22f85fdd2dbdd0#40d30b7547c38097801ace9d88004b25)保留。截图下载至本轮私有证据目录，权限0600；本记录只描述技术错误，私人正文、凭据和完整环境内容输出为0。

## 发现与问题定义

| 证据 | 实际行为 | 执行边界 | 判断 |
| --- | --- | --- | --- |
| IMG_9153 | `spawn …/node/core/chunks/vendor/ripgrep/arm64-ios/rg ENOENT` | 原Runtime的内置`rg`选择器→原ChildProcess→guest解释器 | `prepare-node.py`只复制Runtime JavaScript，原darwin制品自带macOS rg；iOS选择器派生arm64-ios目录，包内缺该文件。截图未展示该次工具输入和完整工具标识，具体参数保持待确认。 |
| IMG_9153下方 | `.notion`页面轻索引JSON已有输出 | 原工作区文件读取 | 轻索引可见与实时正文读取分别验证。 |
| IMG_9154 | 正文读取回报`NOTION_CAPABILITY_UNAVAILABLE` | `Read`→`apply_notion_page_read_redirect`→`NotionOperationClient.get_page_markdown`→`ios_notion_runtime._create_process`→`host.cjs` | Hook将`NotionCLIUnavailableError`映射为该码。Node仅接受`notion-runtime`中的用户凭证home，thread内`.notion-home`在`IOS_NOTION_CLI_EXECUTABLE_INVALID`处遭拒。 |
| 定向生产代码回归 | 修复前thread断言退出1；实际`IOS_NOTION_CLI_EXECUTABLE_INVALID`，期望accepted | 执行原host connect校验语句，命令和凭据使用数0 | 已复现目录交付缺口；原截图缺少内部错误包，历史单次失败的完整因果仍由本轮目标执行核对。 |

问题范围收敛到两处平台交付：原工具依赖资源、原Notion线程凭证home。网络状态按实际请求证据判断，当前截图提供本地命令和能力失败证据。

## 方案比较与评审

| 方案 | 适配与影响 | 决定 |
| --- | --- | --- |
| 打包同版Runtime Linux ARM64静态rg，原Node/guest执行；iOS构建适配原选择器 | 复用原Grep/Glob schema、输出、取消和权限；仅增加锁定资源和单处selector适配 | 采用 |
| 新建替代搜索工具或通用命令代理 | 需要新工具与独立参数、输出和权限合同 | 排除；当前需求由原工具满足 |
| Node接受原工作区直属thread的`.notion-home` | 复用Python对actor、selected page、private home和auth文件的校验；保留精确ntn、无ambient token/HOME及原Worker取消 | 采用 |
| 扩大到任意cwd或改用共享用户home | 改变资源归属和凭证隔离 | 排除；当前需求具有明确thread home |

评审通过范围为最小源码与现行设计。原工具注册、描述、权限分类、HTTP接口、授权方式、schema及模型语义修改为0。端侧Python和Claude业务继续在App内执行，Mac直接命令结果只具有独立技术资格。

## 修改与交付物

| 文件 | 本轮职责 |
| --- | --- |
| `frontend/ios/node-dependencies.json` | 锁定同版Linux制品完整SHA-512、rg/COPYING SHA-256和guest目标路径。 |
| `frontend/ios/scripts/prepare-node.py` | 从固定制品提取rg和声明文件；精确匹配一处原选择器，给iOS选择host绑定的已校验路径；保留其他平台选择。 |
| `frontend/ios/scripts/bundle-node.py` | 核对锁、资源摘要和单处适配回执后打包，记录制品来源。 |
| `frontend/ios/runtime/host.cjs`、`worker.mjs` | 暂存rg并修复执行位，向Worker提供host拥有的路径；Notion命令接受规范化直属thread home。 |
| `backend/mobile_runtime/ios_claude_transport.py`、`backend/tests/test_ios_claude_transport_environment.py` | 仅在SDK省略PATH时交付服务端默认路径，保留显式PATH及父secret隔离；以原connect、SDK编码和自有socket验证四项边界。 |
| `frontend/ios/scripts/check-notion-session-paths.mjs`、`check-notion-staging-paths.mjs` | 生产校验语句的路径、env与资源损坏回归；自有fixture，无账户和命令执行。 |
| `backend/tests/ios_runtime_qualification.py`、`EmbeddedDreamBackendTests.swift` | 原SDK/Runtime实际Grep/Glob、原Bash/Stop/resume/权限拒绝，以及原ntn在actor/thread home中的目标执行。 |

[产品规则与页面骨架](../prd/mobile-app/mobile-app.md)和[正常、失败恢复及状态图](../design/multi-platform/mobile-ios-interaction.md)按现有业务目录维护。

## 构建前提与恢复

现有入口为原`prepare-node.py`、`bundle-node.py`及Xcode Debug Simulator `build-for-testing`；Next使用已完成完整类型检查的构建29兼容制品。`bundle-next.py --verify-sources`退出0，566项当前输入匹配。物理内存16GiB，`memory_pressure -Q`报告45%可用，磁盘9.3GiB；Mac无Linux cgroup适用限额。并行重型构建为0，Xcode jobs=1、Metro workers=1、Node old space 2048MiB。预算覆盖约2GiB的Node堆、原生编译进程、模拟器与现有应用，构建串行执行。未在业务服务器构建，未改主机网络与Admin服务。

构建29签名包、`package-receipt.json`和安装回执保留；本轮候选只采用到Simulator。任何构建失败先停止该轮并保留日志，原资源和数据继续保留。

## 验证矩阵与当前状态

证据目录：`frontend/ios/build/claude-notion-20261103/`。初始生产路径回归退出1的日志为`notion-path-baseline.log`，修复后路径11项退出0。资源准备`python3 frontend/ios/scripts/prepare-node.py`退出0；无依赖版本升级、环境重建或模型调用。

| 验证层级 | 范围 | 当前状态 |
| --- | --- | --- |
| 独立技术回归 | Notion权限、错误、取消、home归属及资源摘要 | 44项及33个subtest通过；路径11、暂存7、DNS6通过 |
| Simulator App内技术 | 原SDK/Runtime Grep/Glob/Bash、Stop/权限/历史恢复，ntn两类home | 实际3项通过；测试/摘要均退出0，6项安装资源与源码匹配 |
| Simulator原账户功能旅程 | 原模型→Bash/Grep、原Skill/Read正文、notion-cli Bash搜索→失败恢复/Stop/历史 | 原账户已授权；Read实时正文及CLI搜索均成功，原失败和正常历史保留；原Stop运行中取消通过。正常业务库与Gateway记录已关联，停止请求结算状态独立记录。最后PATH修复采用单Python资源候选验证，完整新App包、手机及发布分别保留资格 |
| 物理iPhone | 构建29保留供用户测试 | 本轮未执行 |
| 商店发布 | TestFlight/App Store | 本轮未执行 |

完成后按各项实际证据精确同步原反馈及已修复页，原失败和截图保留。

### 已执行命令与证据

| 命令 | 退出码 | 关键结果 |
| --- | --- | --- |
| `node frontend/ios/scripts/check-notion-session-paths.mjs` | 修复前1，修复后0 | 原生产校验复现thread home拒绝；当前11项通过，外部/嵌套/alias/env拒绝保持。 |
| `node frontend/ios/scripts/check-notion-staging-paths.mjs` | 0 | 7项通过，ntn/rg摘要、执行位和symlink拒绝。 |
| `node frontend/ios/scripts/check-guest-resolver.mjs` | 0 | 6项通过；DNS来源、离线清空和symlink合同保持。 |
| `python3 -m py_compile frontend/ios/scripts/prepare-node.py frontend/ios/scripts/bundle-node.py` | 0 | 语法通过；验证代理仅删除自有两份新增pyc。 |
| `cd backend && .venv/bin/python -m pytest tests/test_ios_notion_runtime.py tests/test_notion_runtime_integration.py tests/test_notion_auth.py tests/test_notion_operations.py tests/test_claude_agent_notion_cli_runtime.py tests/test_notion_credentials.py -q` | 0 | 44 passed，33 subtests passed；原权限、错误、取消和凭证隔离。 |
| `python3 frontend/ios/scripts/prepare-node.py` | 0 | Node24.21.0、原55份Runtime JS，恰好一处rg适配；rg为静态ELF AArch64，两个资源摘要匹配锁。 |
| 原`xcodebuild build-for-testing`，下方完整参数 | 0 | TEST BUILD SUCCEEDED；正常RN入口，当前566项Next输入和原锁复用。 |
| 原`xcodebuild test-without-building`，下方完整参数 | 0 | TEST EXECUTE SUCCEEDED；xcresult summary为Passed，total=3、passed=3、failed=0、skipped=0。 |
| `xcrun xcresulttool get test-results summary --path frontend/ios/build/claude-notion-20261103/target-r1.xcresult --format json` | 0 | 原生测试最终摘要成功；测试完成前一次读取缺metadata，原失败保留。 |
| 本轮安装资源只读审计 | 0 | host、worker、rg、manifest、COPYING、原适配JS共6项匹配本轮源码或准备资源。 |
| 本机Chrome Mermaid解析 | 0 | APP-07新增3图实际解析通过，浏览器已关闭。 |

```bash
env INK_IOS_NEXT_ROOT=/Users/dmeck/project/ink-dream-memory/frontend/ios/build/iphone-handoff-20261103-b29/Next NODE_OPTIONS=--max-old-space-size=2048 EXTRA_PACKAGER_ARGS='--max-workers 1' xcodebuild -workspace frontend/ios/InkMemory.xcworkspace -scheme InkMemory -configuration Debug -sdk iphonesimulator -destination 'id=120A4231-E08B-422F-A45E-08BDB72937D7' -derivedDataPath frontend/ios/build/RNWSimulator -jobs 1 COMPILER_INDEX_STORE_ENABLE=NO CODE_SIGNING_ALLOWED=NO ENTRY_FILE=index.native.js build-for-testing
xcodebuild -workspace frontend/ios/InkMemory.xcworkspace -scheme InkMemory -configuration Debug -destination 'id=120A4231-E08B-422F-A45E-08BDB72937D7' -derivedDataPath frontend/ios/build/RNWSimulator -parallel-testing-enabled NO -maximum-concurrent-test-simulator-destinations 1 -only-testing:InkMemoryTests/EmbeddedDreamBackendTests/testPackagedNotionCLIThroughOriginalBackend -only-testing:InkMemoryTests/EmbeddedDreamBackendTests/testOriginalRuntimeProtocolWithoutExternalProvider -only-testing:InkMemoryTests/EmbeddedDreamBackendTests/testOriginalDreamRunnerWithoutExternalProvider -resultBundlePath frontend/ios/build/claude-notion-20261103/target-r1.xcresult test-without-building
```

App PID91757中，原`ClaudeAgentRunner`合成provider请求4次，原Runtime协议合成provider请求17次，真实模型调用0；Grep/Glob搜索自有文件，Bash共享文件、权限拒绝、原Session重开与容器定位、运行中Bash interrupt和描述符清理均通过。ntn在原actor及直属thread home执行version/help共4次，账号凭据和Notion API使用为0。原测试方法均以sandbox-disabled既有部署值执行，工具审批仍由原SDK拥有。

三项断言在11.918秒内完成；随后测试宿主进入`exit→uv__threadpool_cleanup→uv_thread_join`。本轮只对自有测试宿主执行`simctl terminate`退出0，外层Xcode及最终xcresult确认3/3通过。该清理和采样记录独立保留，原生宿主退出行为未纳入本项源码修改或APP-04验收。

普通启动退出0、PID92548；Simulator安装采用`com.inkmemory.mobile`、0.1.0/1，数据由系统随安装迁移到当前容器，未删除用户数据。正常会话和Notion连接GET200，连接记录及原选择保留；本机auth文件数量0。原重新连接沿现有接口创建pending，原验证页已进入Notion正常登录页面。用户已收到完成原账户登录的输入请求，当前正文读取资格保留。

### 原账户与真实模型执行

后续采用本轮命名的Simulator验证驱动，通过调试器加载Foundation动态库，调用App已有`URLSession.shared`、原Cookie/CSRF/Origin和公开HTTP入口。驱动只承担请求、收集本轮响应和写入私有回执；Dream Python、原Factory/SDK/Runtime和命令执行均在App内。该方式覆盖公开API及正常会话历史，页面发送按钮的交互资格保留。代码、配置、认证和权限替换为0。

原账户现有Thread列表、实际Deck/Voice及已保存模型选择沿公开接口读取，创建一个正常测试Thread `45cac01b-a717-458c-a84f-45ceb90baee7`，标题“APP-07 iOS工具兼容验证”。用户原有历史保留。本轮使用原保存别名`codex-7c4d6162-84bd-40bc-8464-dc2ea09bfb15-gpt-6.1-sol`，未更改用户模型配置、Deck或订阅。前三个接受回合各设`max_turns=4`，第四回合设2；共4个持久化用户回合，原Runtime记录9个实际模型消息。既有业务日志和历史继续保留，正文及凭据输出为0。

| 回合与回执 | 公开入口结果 | 工具与恢复证据 |
| --- | --- | --- |
| `business-existing-r4`，消息`12398A2E-8870-4078-9898-1D05B116C297` | chat HTTP200，正常历史用户消息1条 | Bash的`printf`写入请求被原`.dream`保护规则拒绝，按要求停止；Grep执行0。 |
| `business-recovery`，消息`D95DFC27-7650-474E-A42F-FD1F1DD88B68` | HTTP200，正常历史用户消息2条 | `printf`原只读命令表未列入，原保守解析继续拒绝；保留规则与失败记录。 |
| `business-allowed-r2`，消息`BE0418C1-906C-4B0F-B78A-06F0170A769A` | HTTP200，正常历史用户消息3条 | Bash `echo APP07_COMMAND_OK`返回标记、`isError=false`；Grep搜索包内绝对路径遭原会话边界拒绝。 |
| `business-grep`，消息`2B10E0EA-3288-4BFA-B21C-02C31926CFC8` | HTTP200，正常历史用户消息4条 | 仅调用Grep，搜索同一Thread内既有`.dream/README.md`，`output_mode=count`，`isError=false`；原始输出首行25，随后原Runtime摘要为`Found 0 total occurrences across 0 files.`；保留完整输出。最终答复`APP07_TOOLS_OK`，`finishReason=stop`。 |

真实执行证据为`evidence/business-grep-proof.json`及各回合私有SSE；解析使用原`frontend/app/_dream/lib/claude-agent-sse-utils.ts`的`parseClaudeAgentSseBuffer`。正常messages接口使用既有final投影，完整工具过程沿原process入口读取。原页面“新建→聊天历史→APP-07 iOS工具兼容验证”重开后，四轮记录及最终`APP07_TOOLS_OK`实际可见。`finishReason=stop`为模型正常结束语义，本轮真实账户运行中Stop尚未验收；运行中Bash interrupt与原Stop合同已由前述App内合成provider资格验证。

### 验证驱动失败与诊断边界

驱动首轮编译缺C++模块条件退出1，改用Foundation头后退出0。旧App PID92548调试表达式未取得派发回执，停止本轮自有调试进程退出143，后续确认旧PID已退出，业务提交0；当前普通App PID95610接续。诊断表达式首次缺Darwin符号失败，修正后仅写函数名、行号和数量。动态库编译、临时签名与后续调试派发均退出0，原App制品和源码不受驱动修改。

首个创建请求缺原`Origin`，HTTP403，Thread创建0；按现有`NativeUploadRequest.local`补齐同源头后创建成功。简写模型`gpt-6.1-sol`触发HTTP409 `GATEWAY_MODEL_SELECTION_CONFLICT`，持久化和模型执行0；读取原保存别名后重试。`echo`回合预检曾HTTP503 `GATEWAY_UNAVAILABLE`，当次持久化0；正常模型目录恢复HTTP200且原别名`callable=true`后，沿相同消息ID重试一次成功。503在模型目录预检边界观察，网络故障类型和服务端原因未由该码推断。

目录观察驱动首版使用`.models`字段，产生无效`callable=false`结论；按原`gatewayModelsApi.ts`的`.data`字段修正，取得HTTP200、`callable=true`。两版驱动回执保留，验收使用修正版。

### 初始账单观察与授权等待（历史记录）

App内只读审计确认Gateway启用，最终SDK强制配置由`apply_gateway_sdk_env_to_options`在用户覆盖后应用，Gateway origin为现有`https://ink-admin.suoxya.com`。正常用量入口使用现有Admin Product origin `http://127.0.0.1:3000`。本轮未调整这两个地址或其他环境值。审计仅输出启用状态、scheme、host和port，凭据输出0。

`GET /api/story-workspace/usage`及同模型别名筛选均HTTP200。投影`asOf=2026-11-03T07:53:20.797Z`，当前订阅周期覆盖本轮；未筛选列表最新记录为11月1日，同模型列表最新记录为10月22日，尚未取得本轮Gateway request与Token结算的关联记录。真实模型响应和工具执行成立，正常Admin账单可见性保留为验收缺口；未通过其他账本、替代Gateway或隔离账户补齐。

Notion原授权页面等待用户完成登录，模拟器本机凭证数量仍为0。用户输入请求保持待回复，未再发起新授权、复制手机凭证或扩大权限。已选页面正文、同会话问答、真实失败重试和完整原账户验收保持待完成。物理iPhone构建29、APP-04暂停及发布状态保持。

独立文档检查r4退出0：10份存在、154条本地引用、87锚点及71围栏通过，990行新增内容禁词0，目录条目7/7；原新增3图解析通过。首次目录检查发现新脚本清单缺口，已在`frontend/ios/.folder.md`补登记；修订后检查、限定文档`git diff --check`及未追踪本文的尾空白/围栏检查均退出0。

已在原反馈APP-07行及“已修复问题”对应段落完成后续精确同步，两次更新均返回原page_id且无警告。当前同步内容包含真实Bash/Grep、四轮历史及重开、正常账单关联缺口和Notion待授权状态，原截图和技术回执保留。最终复核确认host/worker与已测资源一致，模拟器Notion凭证数量0且原登录页仍可见。原账户授权连续三轮待完成，当前目标等待用户完成登录后继续正文验收；正常账单关联缺口保留。


### 原账户登录后的授权恢复

用户反馈已完成浏览器登录，旧授权超时。当前Safari已进入原工作区的Notion CLI授权页，旧页显示HTTP400；App原Notion连接页面显示“已过期”。按原入口发起一次连接，最终取得“认证进行中”及新验证页；原浏览器登录会话保留，新页已选择原工作区。验证码、授权链接及浏览器凭据未写入本记录。

授权页明确声明继续操作包含同意Notion开发者条款，已向用户提交当前页面确认请求。等待用户点击授权后，返回App原页面完成轮询，再验证已选页面正文。原资源选择、同步策略、权限及物理设备保持。

重新连接期间存在另一任务的独立Simulator窗口置前；通过Simulator原Window菜单返回本轮iPhone 16 Plus。原App PID95610与原数据、安装容器均保留，未重启设备或App。App内只读协程诊断退出0，采样退出0；未据短暂UI观察将原请求判定为后端失败，最终原页面已取得pending。

### 授权后原账户验证与新增Bash CLI反馈

用户完成当前授权确认后，原连接GET200且`auth_status=authenticated`。原5个数据库选择、接受快照`snap-20261101T051641Z-4be83e39`保留；正常turn将234页轻索引及私有凭证投影到同一Thread。资源发现GET200，返回26个数据库，选择写入0。

Notion真实验证分三轮保留：首轮“两次Read”限制与原Skill前置步骤冲突，正文调用0；次轮Read收到模型传入的空`pages`，原schema返回`Invalid pages parameter: ""`；第三轮按原反馈恢复，Skill→Read(snapshot/connector/index)→Read(一个已选页面)，原调用采用合法`pages="1"`，四次Read均`isError=false`。实时正文payload的`ok=true`、Markdown非空且长度224；最终`APP07_NOTION_OK`。正常历史重开已实际展示该标记及前轮参数失败。正文内容和标题未写入本记录，私有SSE权限0600。

实际停止验证沿同一Thread公开chat入口，显式原模型且`max_turns=1`，请求仅生成合成文本。生产SSE parser观察到text-delta后，通过原Stop接口取消；前置status为running，Stop HTTP200且stop_requested=true，后置status为idle/running=false。流正常结束，`finishReason=stop,cancelled=true`，transportError=0。该证据覆盖运行中Agent停止，页面发送按钮交互和物理设备分别保留资格。

Admin只读核对已确认实际ECS主机、active服务、`ink-admin`用户及现用release。只读事务按本轮Thread及其模型response/idempotency identity关联到正常`ink-memory`业务库：8条user、8条assistant历史，包含两个验证标记和7份可用process；21条Gateway记录中20条settled，1条停止请求为CLIENT_CANCELLED、settlement_failed、HTTP502，原失败保留。正常用量列表先前缺少关联的观察保留，当前正常库记录已取得。未调整Admin服务、配置、账号或数据。

用户新增截图明确展示`notion-cli` Skill的Bash `ntn api v1/search --data '<query/page_size JSON>'`，退出4、`No workspace selected`。本轮在同一Simulator App、同一原账户与Thread，以合成关键词执行原Skill→原Bash→相同API路径，亦退出4；仅改变搜索关键词与分页用于限制私人结果，资源和权限保持。Read hook及资源发现的成功回执与该Bash失败分别记录，Bash CLI修复仍进行中。

actor home与thread home的auth/config/workspaces文件均存在且0600，目录700；config默认workspace与auth key匹配。原Runtime的`notionBashEnvironment`先清除子进程Notion变量，再执行`notionProjection`的cwd、home、owner、mode和原生ntn路径检查；下一项工作为定位其实际拒绝阶段。当前采用本轮命名的Simulator临时诊断制品，仅输出阶段、存在状态、UID及mode，原权限判断保留；源码和手机资源保持，诊断结束须恢复原资源并核对摘要。

### Bash CLI根因、修复与目标回执

临时诊断只记录原检查阶段及属性，实际得到`reason=native-executable`、Node UID501、home UID501/mode0700及正确Thread绑定。Bash投影检查收到的首项PATH为guest逻辑`/usr/local/bin`，Node文件系统无法定位ntn。服务端PATH首项为已校验的guest实体ntn目录。`IOSClaudeTransport.connect`只复制`options.env`，原SDK在PATH无需修正时省略显式值，父进程默认PATH在此缺失；原Runtime清除Notion绑定后，guest CLI返回未选工作区。

最小修复为Transport在显式env缺少PATH且服务端存在PATH时补当前默认值。显式PATH与显式空值保留，其他父凭据不继承。原Runtime的workspace、owner、mode、ntn binary及shadow检查保持。workspace文件、NOTION_WORKSPACE_ID、授权、资源选择、Tool描述及审批修改为0。

| 命令或目标 | 回执 | 资格 |
| --- | --- | --- |
| `cd backend && .venv/bin/python -m pytest tests/test_ios_claude_transport_environment.py -q` | 基线exit1，1 failed/3 passed；失败项缺少PATH | 无provider、账户或业务数据的传输合同 |
| `cd backend && .venv/bin/python -m pytest tests/test_ios_claude_transport_environment.py tests/test_ios_notion_runtime.py -q` | exit0，7 passed | 修复默认/显式/空/缺失PATH，父secret隔离及原Notion Worker合同 |
| `cd backend && .venv/bin/python -m pytest tests/test_sdk_env.py::TestNotionCliRuntimeEnv tests/test_notion_credentials.py -q` | exit0，13 passed | 原凭据/环境归属 |
| 原账户CLI基线，消息`B43463A5-D870-48C9-948B-F9E6FDFE47BF` | HTTP200保存，原Bash工具isError=true、exit4、No workspace selected | 原App内实际复现 |
| 修复后同链路，消息`65B4E981-FAC7-441C-9FE7-5673C372DF9C` | HTTP200，原Skill→原Bash执行一次`ntn api v1/search`；isError=false，返回合法list，最终APP07_NOTION_CLI_OK | 原账户、原模型max_turns=3、原Thread，资源写入0 |

CLI实际验证使用合成关键词与page_size=1，保留搜索响应为私有证据，仅导出类型、数量和成功状态。原Read正文的224字内容未公开。正常history接口采用最近20条投影，后续回执的userMessages=10表示该页数量；完整历史数量由正常Admin记录核对。

模块更新前确认Simulator所装原文件与修复前源码完全一致；新模块SHA-256为`24c2c5bc0252905bd5b2b2df2198d59036d0aea4a9c3f0c982d8ff887d1c7f38`。保留旧文件后原子更新同一Python资源，并通过原模块reload使后续Transport使用当前定义。App PID95610、原Factory/Runner、Native/Node/Next、锁定依赖及认证均保留。载入后源码摘要匹配且PATH默认分支已加载；未重启App或访问手机。原完整打包入口仍复制该backend模块。

本轮资源更新预算为约12KiB文件及现有目标的一次Chat提交（max_turns=3）；Mac物理16GiB、memory_pressure报告33%可用、磁盘4.4GiB，本任务重型构建0。本轮最后修复的完整App包构建和安装数量0；现有Xcode3/3为前述资源/Read目录修复的技术资格，最后PATH改动由20项定向回归及当前App实际CLI证明，未扩大该旧Xcode结论。

原Runtime临时诊断模块已按原SHA恢复，诊断文件导出至私有证据后删除；证据`notion-projection-probe-resource.json`记录restored=true。源码仅增加Transport默认PATH交付，诊断逻辑未进入源码候选。当前PRD、iOS正常/异常/状态图和Notion技术设计已同步。

### 最终业务关联与交付核对

正常Admin的最终只读事务按本轮Thread及请求identity取得11条user、11条assistant历史、10份可用process和29条Gateway记录。28条请求为settled；其85条Token流水中的已结算请求全部满足`reserve = capture + release`及`capture = allowance_charged_tokens`。停止请求`req_c6204e72d559400ea5bd3b96644709c3`仍为`CLIENT_CANCELLED / settlement_failed / HTTP502`，保留原reserve及失败记录；结算修复未进入本项范围。证据为`evidence/gateway-final-ecs.json`，Admin生产变更为0，后台页面独立登录资格保留。

同一Simulator的正常历史入口重开本轮Thread，原失败记录、`APP07_NOTION_OK`及`APP07_NOTION_CLI_OK`均在原页面的可访问文本中；滚动至末尾后，截图实际显示最终`APP07_NOTION_CLI_OK`。新模型调用为0，历史删除或改写为0。元数据回执为`evidence/final-history-ui.json`。

最终资源核对退出0：已测host、worker、rg、manifest、COPYING与选择器共6项保持原摘要，临时诊断JS恢复原摘要，Transport资源与当前源码摘要匹配，合计8项通过。当前工作树HEAD观察为`a61268cc`，其他任务提交及未提交修改保留；本轮候选以列出的文件摘要和回执定位。

原反馈APP-07行与已修复页对应段落已精确同步，包含新增PATH根因、20项目标回归、实际CLI搜索、11轮正常历史、29条Gateway、85条Token流水和单列停止结算异常。末段更新首次返回`no_match`，重新读取该段并移除页面包装尾部后更新成功，最终无警告；原截图、其他问题和APP-04暂停状态保留。

本项源码修复及Simulator原账户功能验证完成。最后PATH修复的完整新App包构建、物理iPhone安装及商店发布均为0；普通发送按钮的独立交互资格保留。既有Xcode3/3、最后20项定向回归、单模块候选和真实账户回执按各自范围使用。

并行交付核对：另一任务的总记录已登记Release30安装与启动，本任务手机操作仍为0。只读检查其本地`iphone-handoff-20261103-b30/Payload/InkMemory.app/app/mobile_runtime/ios_claude_transport.py`确认文件存在，摘要与当前源码不同且缺少最后PATH默认分支；build30的rg与Read目录适配采用资格按该任务回执使用，当前PATH修复待后续完整安装包采用。

最终机械检查r6退出0：13份文档存在、162条本地引用、91锚点、72围栏、新增134行禁词0、目录条目8/8；`node frontend/ios/build/claude-notion-20261103/regression/mermaid-app07-parse.mjs`退出0，3/3图由本机Chrome实际解析，自有浏览器已关闭。限定文档`git diff --check`及新测试/本文尾空白和围栏检查均退出0；后续设备状态措辞增补由下一次限定文档检查记录。
