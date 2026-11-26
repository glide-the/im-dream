<!-- [Input] 用户统一AI/笔记链接改造要求、better-chatbot参考代码和两仓库改动。 -->
<!-- [Output] 需求追踪、源码交付、生成命令、技术验证和服务采用证据。 -->
<!-- [Pos] 2026-11-12统一分享项目执行记录；源码完成与真实验收分别登记。 -->
# AI与笔记统一分享改造

日期：2026-11-12。用户要求参考better-chatbot公开分享工程设计，改造AI和笔记，并在设置中管理和使链接失效。

产品：[外部链接PRD](../prd/sharing/external-links.md)、[笔记分享PRD](../prd/notes/sharing.md)。设计：[统一分享交互](../design/sharing/external-links.md)、[笔记适配](../design/edit-session/note-sharing.md)。参考版本和源文件清单由统一设计所有。

## 需求与交付物

| 工作项 | 源码交付 | 当前状态 |
| --- | --- | --- |
| AI链接分享 | external_shares路由、最终正文投影、Web/Native分享选项 | 后端与客户端协议技术规格通过，Web/Native完整交互待验收 |
| 笔记统一发布 | 原保存屏障、已保存正文摘要、Admin独立快照 | 后端技术规格通过，Web/Native完整交互待验收 |
| 独立公开阅读 | Next `/share/[token]`及匿名API，共用无凭证有界读取器；Markdown/math/Mermaid与文字笔记 | 源码已接入，验证待完成 |
| 设置管理 | Web/Native两类概览、有效/已失效、翻页、复制/打开/原内容/失效、未知结果刷新 | 源码已接入，验证待完成 |
| Admin数据合同 | externalShareDto/Repository/Handler，四个内部操作与回执审计 | 正常Admin制品已采用，精确合同与访问限制检查通过 |
| 共享Schema | 前向0087、Drizzle journal/snapshot、精确capability、现有及新DATA角色授权计划 | 正常ECS已采用，88/88及精确能力/权限核对通过 |
| 历史兼容 | 旧无归属文件token统一404，原文件保留；公开链接独立于原内容删除 | 源码已接入，实际发布影响待复核 |
| 正常服务采用与公开域名 | Admin/Dream制品、数据库能力、公开origin和设备系统分享 | Admin已发布并通过线上只读检查；Dream制品与设备验收待完成 |

Dream工作区为`/Users/dmeck/project/ink-dream-memory`，Admin工作区为`/Users/dmeck/project/ink-admin-memory`。两处均保留原有未提交工作。本次新增表、DDL、权限及capability仅位于Admin；Dream无建表和本地文件回退。早期原型新增的FileStorage namespace扩展已移除，原文件保留。

## 源码生成证据

| 命令/入口 | 退出码 | 输出与范围 |
| --- | --- | --- |
| `pnpm exec tsx scripts/generate-external-share-contracts.ts /Users/dmeck/project/ink-dream-memory/backend/services/admin_data/external_share_contract.json`，Admin工作区 | 0 | Generated four external-share operation descriptors. 精确操作摘要生成，无数据库连接。 |
| `packages/db/node_modules/.bin/drizzle-kit generate --config drizzle.config.ts --name external_shares`，具名临时生成目录 | 0 | 从canonical schema生成0087 SQL、journal及snapshot；随后在新增SQL中追加精确DATA授权与capability。无数据库连接或迁移执行。 |

迁移生成使用独立临时目录，读取0086及之前的原snapshot/journal，打包canonical schema源码供Drizzle加载；输出仅写回本轮0087及新增journal条目。临时目录已清理。首次生成遇到workspace二进制解析与绝对out路径问题；调整为数据库workspace二进制和临时目录内相对路径后完成。上述命令属于源码生成。

## 验证状态

前序源码阶段按用户指令暂停验证；源码生成期间未执行类型检查。[原实现记录](note-sharing-20261112.md)保留历史版本的验证范围。用户随后要求部署Admin并验证，当前技术检查由主Agent执行，luna-test-stage保持暂停。

已新增或更新验证规格；本次执行范围与结果见下方发布阶段：

- Dream `backend/tests/test_note_shares.py`：保存正文核对、严格输入、认证及管理接线。
- Dream `backend/tests/test_external_shares.py`：匿名读取无凭证转发、失效/缺失/失败、有界响应和AI最终正文投影。
- Dream `frontend/app/_dream/api/__tests__/ExternalShareApi.test.ts`：稳定key、记录身份和公开URL/DTO范围。
- Dream `frontend/e2e/note-share.spec.ts`、`note-share-boundaries.spec.ts`、`native-share.spec.ts`：新公开路径、状态查询和显式图片选项。
- Admin `app/lib/dream/externalShareHandler.test.ts`：公开成功、缺失/失效、非法token、capability失败和严格DTO。

手工阅读覆盖模块接线、相对导入、账户切换、图片入口、匿名BFF边界、旧文件方案、当前文档及目录索引。手工阅读记录提供源码审阅范围；当前技术检查与真实验收分别登记。

## 采用依赖与风险

1. 具名可删除隔离PostgreSQL已完成migration replay、旧版兼容、权限、归属、终态及回执技术验证，正常服务与真实账户验收单列。
2. Admin先发布0087与精确`dream.external-share.v1`、对应四个内部操作及匿名读取；Dream随后采用。缺少能力时分享创建、管理及读取fail closed。
3. 发布前复核旧无归属文件token统一404的兼容影响，保留原文件；后续归属映射须使用独立证据和显式迁移工作项。
4. 配置公开应用origin，确认外部访客可达、Admin/Dream读取同一份记录，再验收Web与实体设备的复制、公开阅读和单条失效。
5. 应用回退须继续保留新增表、快照、回执、已失效终态和逐次状态检查；回退版本不得恢复旧文件token直接读取。

前序源码阶段未执行正常数据库迁移、业务数据写入、服务重启、发布、提交或PR。后续部署阶段单列证据。

## Admin部署与验证阶段

用户授权部署Admin并验证，Dream服务保持原状态。Admin从远程main建立独立发布工作树，保留原工作区其他未提交改动。

| 验证命令或入口 | 退出码 | 结果与范围 |
| --- | --- | --- |
| Admin `pnpm --filter @ink-memory/db build`、`pnpm exec tsc --noEmit --pretty false`、`pnpm lint` | 0 | 数据库package构建、完整类型和lint通过。 |
| Admin `pnpm test:config`、`pnpm test:release-receiver` | 0 | 35项配置与15项发布接收器规格通过。 |
| Admin Node20 `node node_modules/vitest/vitest.mjs run --exclude '**/*.integration.test.ts' --reporter=dot` | 0 | 2641 passed、37 skipped。 |
| Admin `pnpm exec tsx scripts/validate-external-share-contract.mjs` | 0 | 具名隔离PG完整88条迁移、并发/重复/漂移、DATA权限、归属、回执、列表、快照与失效验证通过；原Next公开路由的4项HTTP规格通过。 |
| Dream backend `.venv/bin/python -m pytest tests/test_note_shares.py tests/test_external_shares.py -q` | 0 | 16 passed，Provider-free技术验证。 |

Node26完整单元出现一项原有model-egress CONNECT的undici dispatcher协议差异；对应main生产代码保持，Node20完整单元通过。隔离harness首次使用JSON属性顺序比较导致断言失败，改为结构比较后通过，正常数据保持。

Admin [PR50](https://github.com/glide-the/dream-im-platform/pull/50)已合并，CI完整检查通过。原297项operation前缀及摘要保持，目录追加至301项。正常ECS通过原编译迁移入口应用0087，88/88、pending为空，精确`dream.external-share.v1`版本1已登记；有限DATA角色拥有SELECT/INSERT/UPDATE，DELETE保持关闭。迁移前后users/threads/messages计数为37/1655/4363，新增分享0条，私有配置指纹和数据库目录inode保持。

迁移前Schema与迁移/capability元数据备份位于服务器服务账户私有维护目录，已校验归档目录及SHA-256。首轮Actions完成Node22检查与完整Linux制品构建；上传速度约180KB/s，服务切换前取消该轮上传，并清理其不完整候选目录。[PR51](https://github.com/glide-the/dream-im-platform/pull/51)将发布期限改为显式按次选择，默认20分钟保持，重试采用40分钟。发布与部署后证据继续登记。

本阶段完成技术验证与正常Schema采用，Dream制品发布、Web/Native完整交互、现有真实账户的内容分享和实体设备系统分享分别验收。

补充技术验证：Dream frontend使用安装的Playwright执行`ExternalShareApi.test.ts`，显式临时source/unit配置，无浏览器和服务，4 passed、退出码0。收尾文档验证覆盖9份现行稿、29项相对引用、两节发布指南引用与目录索引；使用已安装Chrome加载仓库Mermaid，9幅图均parse通过，退出码0。文档检查仅提供结构与语法证据。

发布期限补充：第二轮run43172651863完成Node22检查与构建，上传实测约90KB/s，40分钟预算不足，切换前取消，原服务200。PR51与[PR52](https://github.com/glide-the/dream-im-platform/pull/52)均通过CI并合并；第三轮[run43175197174](https://github.com/glide-the/dream-im-platform/actions/runs/43175197174)使用源码`be88fc368e2e9c2db70422e645a415b64cf9d4f2`和90分钟按次预算。默认20分钟、构建和运行资源预算保持。

## Admin部署后回执

[run43175197174](https://github.com/glide-the/dream-im-platform/actions/runs/43175197174)于2026-11-12 08:28:30 UTC完成，build与deploy均success。运行源码`be88fc368e2e9c2db70422e645a415b64cf9d4f2`，BUILD_ID为`d2OpEL3UKUbpKAIoDrkCq`，Node22.23.4，原完整版本保留。

`python3 /tmp/ink-admin-external-share-postcheck-run-20261112.py be88fc368e2e9c2db70422e645a415b64cf9d4f2`退出码0。真实服务OAuth目录200、301项operation、四个分享操作及精确能力匹配；88/88、pending为空。DATA读/创建/更新开放、DELETE关闭。缺失/非法公开token404，匿名内部目录401，缺少用户身份的管理请求403，ECS与本机公网登录200。分享记录0条，正常库保留原业务内容；私有配置指纹、数据目录inode1056781与owner/mode保持，swap/zswap继续关闭。

临时综合脚本补齐安全阶段诊断与有界清单读取后，定位到HTTPS连接ETIMEDOUT；最终检查包含2次有界传输重试，所有业务断言通过。原服务源码与权限保持已发布合同。具体尝试、备份、原制品与回执路径见[Admin发布记录](https://github.com/glide-the/dream-im-platform/blob/main/docs/verification/external-share-release-20261112.md)。

本轮完成Admin部署与技术验证。Dream服务未重启或发布，真实账户创建→外部阅读→失效、Web/Native完整交互及实体设备系统分享仍待验收。luna-test-stage保持暂停。

## PR交付验证

交付分支为`codex/unified-external-shares-20261112`，目标为仓库默认主分支`develop`。独立工作树只整理分享源码、文档与验证规格，原工作区的音频工具、MCP卡片、聊天加载和本地配置继续保留。Admin发布回执由其PR53合并至main。

| 命令 | 退出码 | 结果与范围 |
| --- | --- | --- |
| backend `.venv/bin/python -m pytest tests/test_note_shares.py tests/test_external_shares.py -q` | 0 | 16 passed。 |
| frontend `pnpm exec tsc --noEmit --pretty false` | 0 | Web完整类型检查通过。 |
| frontend `pnpm run native:typecheck` | 0 | Native完整类型检查通过，保持原InkLabel单字符串合同。 |
| frontend `pnpm exec playwright test --config e2e/external-share.config.ts` | 0 | 20 passed：客户端、公开AI/笔记阅读、正文隔离、图片捕获、复制/保存恢复及原生句柄清理；复用本机Chrome和具名隔离夹具。 |
| frontend定向`pnpm exec eslint` | 0 | 44个文件，0 errors、22 warnings；旧native-share夹具与基线均为17项既有lint错误，新增错误0。 |

首轮补充检查发现Native标签将数字或多段JSX传给InkLabel，已在调用方格式化为字符串。隔离夹具补齐UTF-8、原生模块预解析及异步复制完成断言，Vite缓存与测试结果限定在本轮工作树。真实账户、真实模型和实体设备验收继续单列。

当前正式设计的9幅业务图保持已解析版本，PRD桌面/窄屏骨架及历史稿保留。CI构建与合并结果由GitHub PR回执登记。
