<!-- [Sync] 2026-11-01: 移动应用PRD迁至docs/prd/mobile-app/mobile-app.md，更新现行引用，保留历史回执。 -->
<!-- [Input] 用户授权的iPhone Notion安装提示定位、现有生产入口及当前工作区。 -->
<!-- [Output] 根因、最小修复、设计评审与分项验证回执。 -->
<!-- [Pos] 本轮iPhone Notion执行记录；原历史阶段保留在mobile-app-design-review-20261024.md。 -->
<!-- [Sync] 2026-11-01: 记录构建20真机X_OK拒绝及精确解释执行入口的局部修订。 -->

# iPhone Notion安装提示定位与修复

## 范围与判断

本轮以用户提供的优化提示词为唯一规划依据。读取根合同、直接目录合同、现行移动设计及工作区状态，保留原未提交改动。真实账户、凭证内容、用户文档正文、Schema及服务配置维护增加数为0。测试代理执行确定性检查；主Agent执行真机采证、签名、安装与真实业务前提核对。

- **已确认根因**：构建20的固定`ntn`资源存在且0755，iOS返回`os.access(X_OK)=false`。原`get_notion_cli_installation → resolve_ntn_executable`据此返回`missing`，原生页面显示“先安装 ntn”。该阶段CLI执行和网络业务均为0。
- **执行证据**：`physical-b20-result.json`记录`installation=missing`及`NotionCLIUnavailableError`；`physical-b20-diagnosis.json`记录`configured/absolute/isFile/factoryBound/nativeEndpointBound/runtimeBound/matchesNativeExecutable=true`、`isSymlink=false`、0755、10,930,616字节、`osAccessX=false`及固定SHA256。两份回执PID均为9635，设备安装信息为`com.inkmemory.mobile`、0.1.0/20。
- **网络判断**：本次安装提示发生于本地文件检测。真实Notion上游网络质量继续按实际业务请求结果判断。
- **相邻提示缺陷**：原路由把`NotionCLIUnavailableError`承载的执行失败统一描述为未安装；原iOS页面要求用户在主机执行npm安装。

完整证据目录：[notion-20261101](../../frontend/ios/build/notion-20261101/)。`ntn`为固定npm包0.15.1中的Linux ARM64 ELF，SHA256 `faee5c2227abea0ea401bd27689a9d150d32402d4240f349619710fd621824fc`；MIT许可证SHA256 `ed189d279fa3b5f8e1f139ca583f73693eac31df9619a6a59dd73030c65e19af`。包内位置为`node/notion/ntn`，实际位置为App私有`Library/Application Support/InkMemory/runtime/guest/<rootDigest>/usr/local/bin/ntn`，按现有Node宿主和解释器执行。

## 最小修复与设计评审

[正式交互与技术设计](../design/multi-platform/react-native-web-project-structure.md#iphone-notion安装提示与恢复2026-11-01)直接包含正常、异常与恢复时序及状态图；[移动产品需求](../prd/mobile-app/mobile-app.md#设置资源详情与恢复骨架)复用原桌面和窄屏骨架，补充原反馈区规则。

| 文件 | 本轮修订 |
| --- | --- |
| `backend/notion/auth.py` | 原进程工厂绑定精确解释执行文件；该文件采用R_OK检测，普通主机及其他文件继续采用X_OK，重复绑定拒绝更换入口 |
| `backend/mobile_runtime/ios_notion_runtime.py` | 将已校验摘要的既有暂存路径传给原绑定函数；私有端点与实际argv保持 |
| `backend/notion/errors.py`、`backend/routers/notion.py` | 准确描述已有异常范围，执行不可用503返回安全命令失败提示 |
| `ConnectorNotionDetailPage.native.tsx`、`notionConnectorPresentation.ts` | iOS组件缺失显示暂不可用，保留原重新读取且读取期间禁用；主机Web默认标签与安装规则保持 |
| 原认证/路由测试与`native-notion-resources.spec.ts` | 覆盖精确绑定、权限检测差异、失败脱敏及原页面无重复授权/资源写入 |
| 相关设计、产品稿、索引及目录合同 | 对齐根因、恢复行为、图示及验收范围 |

| 评审项 | 发现 | 处理方式 | 修订结果 | 剩余依赖 |
| --- | --- | --- | --- | --- |
| 提示实际触发 | 真机文件有效，原生执行权限检查失败 | 仅原解释器绑定文件采用可读检查 | 最小代码修复完成 | 修复包同机回执 |
| 资源、检测与执行 | 固定摘要与实际暂存路径一致 | 复用原准备/资源阶段、工厂、Worker | 新框架与平台依赖增加数0 | 最终签名制品核对 |
| 认证及权限 | 原actor凭证、网页授权、私有端点及cwd门禁齐备 | 保留原模块，原主机权限检查保持 | 业务接口与Schema变更数0 | 有效Notion授权及资源读取 |
| 失败恢复与重复点击 | 原生安装说明不适用，执行失败被标为安装缺失 | 修订原反馈，重新读取仅GET，认证沿原门禁 | 原七节及页面结构保持 | 真机页面与网络恢复观察 |
| 图示与验收 | 平台和制品证据需要独立记录 | 三类图直接入现行设计，验证分项登记 | 设计完成 | 真机业务及发布资格 |

评审结论：局部修复满足当前问题边界。新增安装页、通用安装器、远程执行、自动业务重试、额外确认及新认证协议增加数均为0。

## 实际命令与技术验证

| 命令或回执 | 退出码 | 结果 |
| --- | --- | --- |
| `xcrun devicectl list devices`、`device info apps`、`device info lockState` | 0 | 当前iPhone16可连接，构建20，系统口令允许 |
| 初次`process attach --pid 9506` | 1 | platform未连接，命令未派发 |
| 改用`device process attach --pid 9506` | 外层0 | 旧进程无有效停止状态，后续为no such process，资格门禁未派发 |
| `devicectl device process launch … com.inkmemory.mobile` | 0 | 原构建20普通启动，PID9635 |
| `device process attach --pid 9635`与原CPython C ABI调度 | 外层0，表达式未知错误 | 目标stopped后detach成功；独立设备结果文件确认Python实际执行，命令派发结果单独判定 |
| `device copy from`本轮两个脱敏结果文件 | 0 | 原安装检测missing及X_OK拒绝证据；过早读取一次返回7000/文件未生成，随后取得原文件 |
| `PYTHONPATH=backend backend/.venv/bin/pytest -q backend/tests/test_ios_notion_runtime.py backend/tests/test_notion_auth.py backend/tests/test_notion_capabilities.py backend/tests/test_notion_connector_router_flow.py`，r2 | 0 | 29 passed；初轮缺PYTHONPATH退出4，补明确导入路径后通过 |
| `pnpm -C frontend native:typecheck`，r2 | 0 | 原生TypeScript检查通过 |
| `pnpm -C frontend exec playwright test -c e2e/web-rnw-regression.config.ts e2e/native-notion-resources.spec.ts --reporter=list`，r2 | 0 | 本机Chrome，4 passed；缺失恢复、执行失败、原资源流程及无重复写入 |
| `node frontend/ios/scripts/check-notion-staging-paths.mjs`，r1 | 0 | 5项通过，无CLI、网络及凭证操作 |
| `node frontend/ios/scripts/check-guest-resolver.mjs`，r1 | 0 | 6项通过，无网络请求 |
| 原构建20IPA资源审计，r1 | 0 | ntn、manifest、许可证及六项执行适配与审计时源码匹配 |

r2检查覆盖反馈修订；R_OK根因修复后的r3后端合同退出0、30 passed，构建21再次成功。原制品20保留，覆盖安装使用同一bundle ID与原账户配置。

## 修复包与同机入口检查

[构建21开发IPA](../../frontend/ios/build/InkMemory-Notion-Release-device-20261101-b21.ipa)为142,640,647字节、0600，SHA256 `4a507ab5d66793ca1639a713e5440c38416f3391332f34bddd8de45d972ca2fb`。83个framework与主应用沿原开发身份签名；逐项strict及主应用deep/strict验证退出0，归档CRC通过。沿原构建20保留两份生效配置字节和原profile，源环境文件写入数0；开发profile有效至2026-11-08 01:03:45（Asia/Shanghai）。

| 命令或回执 | 退出码 | 结果 |
| --- | --- | --- |
| 原四份`pytest`，r3 | 0 | 30 passed in 1.45s，包含真实iOS权限差异回归 |
| `env -u SKIP_BUNDLING xcodebuild -workspace frontend/ios/InkMemory.xcworkspace -scheme InkMemory -configuration Release -sdk iphoneos -destination generic/platform=iOS -derivedDataPath frontend/ios/build/rebuild-iphone-20261031/DerivedData -jobs 3 CURRENT_PROJECT_VERSION=21 CODE_SIGNING_ALLOWED=NO build`，r3 | 0 | BUILD SUCCEEDED，沿原依赖及RN资源阶段 |
| `python3 frontend/ios/build/notion-20261101/package21.py` | 0 | 83个framework及主应用签名、原配置保留、固定资源与四份修订Python源码匹配；归档与摘要见package21-receipt.json |
| `xcrun devicectl device install app --device F615EA70-0AFD-5E1A-9373-AECBD061688D frontend/ios/build/notion-20261101/release21/Payload/InkMemory.app` | 0 | 同一iPhone接受构建21，原安装20覆盖升级 |
| 普通启动及console启动 | 0 | 首次PID9692后续附加返回no such process；第二次PID9701有效stopped后detach成功；首次原因保持未知 |
| `physical-b21-result.json`经`device copy from` | 0 | 同一App原Python工厂检测installed；`--version`退出0/58ms、`--help`退出0/49ms；标准错误均0，输出分别11/1,584字节，合计211ms |
| 本轮文档链接、锚点、目录及Mermaid检查 | 0 | 13文件254链接、100锚点无缺失；9份合同16条目齐备；本机Chrome解析3图成功 |

本轮手机CLI检查调用原`notion.auth._run_ntn_command`和同一已绑定工厂，无副作用参数仅`--version`与`--help`，Notion API、真实凭证读取和模型请求均为0。临时空home已移除。调试器C ABI表达式返回unknown error，独立设备结果文件确认两条命令实际完成；原调度器状态与命令状态分别保存。纯Node Mermaid解析首次使用core入口返回Unknown diagram type，改用已安装完整Mermaid在本机Chrome解析，未安装依赖。

## 原公开入口与真实业务前提

同一构建21、App进程9701使用原`URLSession.shared`读取原本机BFF公开入口；调度表达式成功，detach成功。五项结果仅保存HTTP状态、形状和数量，Cookie、凭证与用户资源正文输出数均为0。

| 原入口 | HTTP | 实际结果 |
| --- | --- | --- |
| `GET /auth/session` | 200 | 原账户已认证，2,573ms |
| `GET /api/system-config` | 200 | 原配置形状有效，1,610ms |
| `GET /api/connectors/notion/capabilities` | 200 | `cli_installation.status=installed`，2,850ms |
| `GET /api/connectors` | 200 | 原有Notion连接1项，记录状态authenticated，1,544ms |
| `GET /api/connectors/{id}/databases` | 401 | 原资源读取未通过，2,752ms；当前手机需要有效Notion授权 |

正常账户登录会话与Notion连接记录均可读取；资源接口的401沿原Notion授权边界返回。原连接记录的authenticated状态与当前手机可用凭证分别记录。后续前提为在当前手机的原Notion页面完成或恢复有效授权，再沿原资源入口读取。当前工具未取得手机Notion网页确认的操作能力，本轮授权新会话、浏览器确认、资源选择保存及同步均未派发。保留原连接状态及范围，业务写入、模型调用和额外密码提交均为0。

安装检测、版本/帮助和公开能力目录均已通过；本轮真实Notion资源操作保持未通过，真实网络故障恢复及完整可见页面保持待验收。通过GET会话与配置取得相邻账户协议回执；完整网页登录弹窗及权限变化继续按原验收项记录。

最后`device info apps`退出0，读回0.1.0/21及安装路径`/private/var/containers/Bundle/Application/657C3B49-1F7C-432F-9354-C0186D3F60FD/InkMemory.app/`。包内入口为该路径下`node/notion/ntn`，实际暂存入口为App数据根下`Library/Application Support/InkMemory/runtime/guest/f1aade8ca84f7f3b47715caaa2a0fdb6ef4b2cae265284070c8d707e7c0c6766/usr/local/bin/ntn`。本轮console观察进程已移除，原App进程9701随后经`device info processes`读回仍运行；临时CLI home已移除，构建与脱敏回执保留供复核。

## 最终制品与相邻Web检查

测试代理对最终签名IPA执行只读审计，版本0.1.0/21、固定ntn/manifest/MIT及本轮五份Python、三份Node执行文件均匹配锁或当前源码，全部比较命令退出0。未读取应用配置或凭证文件。

相邻Web登录恢复技术回归取得6 passed，覆盖桌面和390px窄屏的登录选项、会话恢复与原表单反馈。Notion Web保存恢复首轮为3 passed、7 failed；7个主用例依赖`E2E_WEB_BASE`指向的Next，默认`127.0.0.1:55173`；最后3个standalone用例使用独立Vite。主用例的`ERR_CONNECTION_REFUSED`归测试服务前置故障。首轮tee外层退出0，Playwright实际退出码未捕获，整项保持未通过。

有界排查沿既有命令`cd frontend && pnpm exec next dev --hostname 127.0.0.1 --port 55173`启动独立服务，由`subprocess.run`记录实际退出码1；原5173 Next占用`.next/dev/lock`。原服务保持运行，未移除锁、未修改现有配置，7项主用例未重跑，55173最后无监听。3项standalone通过与6项登录恢复通过保留对应技术范围。原手机资源401作为真实业务授权前提独立记录。

最终文档检查为16份文档、309个本地链接、126个语义锚点，缺失均为0；三份新增业务图已在本机Chrome解析成功。完整命令和失败回执分别见`runner/r3/receipt.md`及`runner/r4/receipt.md`。

## 当前交付状态

- **设计完成**：现行设计、三类业务图、产品规则及评审表已补充。
- **技术验证**：30项后端合同、原生类型检查、4项原生页面回归、6项Web登录回归、11项暂存/DNS合同、构建21资源与签名通过；同一iPhone原工厂版本/帮助执行通过。额外Notion Web主用例因Next服务锁前提未完成，失败保持独立记录。
- **真机业务验收**：构建20原故障已复现，21安装检测与CLI无副作用检查通过；原会话、配置、能力目录及连接记录均200；原资源读取401。有效Notion授权、资源读取、真实网络失败恢复及相邻可见页面继续待验收。
- **发布状态**：开发签名构建21已打包并安装至原iPhone；App Store和TestFlight发布未执行。
