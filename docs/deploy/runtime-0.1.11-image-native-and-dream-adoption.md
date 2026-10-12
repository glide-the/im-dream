<!-- [Input] Runtime 0.1.11 same-source CI, immutable public npm bytes and normal Dream adoption evidence. -->
<!-- [Output] Publication, installation, runtime adoption and remaining image business acceptance states. -->
<!-- [Pos] Current Runtime image-native release receipt; earlier versions remain historical records. -->
<!-- [Sync] 2026-10-11: round29 两条正常本机图片链路、展示稳定及历史恢复实际通过；unknown usage、原路由与技术故障验证边界单列。 -->

# Runtime 0.1.11 图片原生依赖发布与 Dream 接入

## 背景与问题

正常 Runtime 0.1.10 在处理 2400px 图片时缺少目标平台 sharp 原生依赖，
在 Gateway POST 前失败。0.1.11 在四个平台 npm 包中补充精确 sharp/libvips
依赖，并由实际 Bun 在 stage、prepack、归档和全新安装门禁中校验。
原始 1,902 个源码文件、SDK 0.2.145、CLI compatibility 2.1.241、权限、
精确 thread 临时目录及 session/resume/cancel 合同均保持。

## 目标与边界

用户明确要求 Runtime 验证后走生产发布。本轮只通过现有 CI 发布五个 npm 包，
更新 Dream 精确 pin 和本机正常安装/采用；Docker 和 AutoDL 只同步源码合同，
没有构建镜像或操作远端。Dream metadata 仍为 backend 0.1.4 / frontend 0.0.4，
Python SDK 和 API schema 不升级。旧 0.1.10 包与历史回执不重制、不覆盖。

Runtime 生产发布不等于图片专项的真实账户/模型验收。首轮历史限制是正常库缺少
`dream.image-turn.v1`、Dream邮箱入口后的OAuth scope校验失败及尚未建立本机会话；
这些前置已由末节的受控发布、正常采用和同账户登录解除。此前Admin管理表单拒绝
仅证明管理身份登录失败，不能判定Dream密码无效；未绕过边界、在Dream补建Schema、
修改账户或创建替代账本。最新真实模型限制以末节及专项执行记录为准。

## 概念与规则

源码 CI、四平台资格、公开五包完整性、安装、运行进程采用与真实图片业务
分别验收。CLI 的 `2.1.241` banner 不能代替 npm package version 0.1.11。
Dream 默认 resolver 验证 package-root cli.js、相邻 manifest、digest 和
必需 capability，不使用临时 CLI 路径或 ambient official CLI 回退。

## 实际发布与安装

| 阶段 | 本轮结果 |
|---|---|
| Scoped PR | [Runtime #28](https://github.com/glide-the/ink-claude-code-dream/pull/28)，合并 SHA `a60eb7f3b5e4af39479b07eac7aef93b538c7723` |
| PR 源码 CI | [38081614548](https://github.com/glide-the/ink-claude-code-dream/actions/runs/38081614548)，success |
| main 源码 CI | [38081686094](https://github.com/glide-the/ink-claude-code-dream/actions/runs/38081686094)，同 SHA success |
| 四平台资格与五包聚合 | [38081685997](https://github.com/glide-the/ink-claude-code-dream/actions/runs/38081685997)，五 jobs success；每 host 59 pass / 3 skip / 0 fail，独立实际 SDK/MCP 流程和 native smoke 均通过 |
| 自动发布 | [38082683882](https://github.com/glide-the/ink-claude-code-dream/actions/runs/38082683882)，同 SHA success，平台先于 selector |
| Public identity | 五个 registry 下载归档均与上述资格归档逐字节相同，版本、依赖、SHA-512 和 SHA-256 检查 exit 0 |
| 正常安装 | Node 24.13.0/npm 11.6.2 精确 global install，exit 0；使用本轮独立 npm cache |
| 正常 resolver/native | 默认 PATH、相邻 manifest、Bun 1.4.0、sharp 0.34.5、libvips package 1.2.4 / library 8.17.3，exit 0 |
| 正常后端进程采用 | 原PID 79939无活动子进程，正常env内预检通过后SIGTERM并以原server.py/cwd启动PID 35255；打印默认Runtime 0.1.11 / SDK 0.2.145身份，health 200；另三服务PID未变，exit 0 |
| 正常图片业务 | 未完成：Dream OAuth客户端拒绝images:create scope，且图片capability独立缺失 |

四平台单测的三 skip 为两项 comparator fixture 前置及旧 Dream pin 的
production manifest 验收；后续实际 differential 流程成功，旧 pin 的 skip
仍不能代表本机 Dream 0.1.11 已采用；本机采用由上表独立正常进程身份回执证明。

公开 selector SHA-256 为 `88ae16a19b7f92aa1fea92b7522daf182faeca89c9b1818de53ca91d796e4f2a`。
四个平台 SHA-256 分别为：

| 平台 | SHA-256 |
|---|---|
| darwin-arm64 | `515c92ba0d6883f5da5ece476983a6f216de60c1215af0cf88877182309d6276` |
| darwin-x64 | `f211c203455b46d37e1fad0e957136cb0d74b63b4cbd2c0c087f22eddce8f48c` |
| linux-arm64 | `5d5579a9e4591dd41b724be68c94eeac2a778b37f5787802c86a3ce0926545f1` |
| linux-x64 | `abfdbda903d8d2c75cd0036b109b96e72554432228fd8d8450b1ac5475a622ee` |

完整命令、原始 CI 输出、公开 integrity 和本机结果保存在
[round23 回执](/tmp/im-image-model-split-20261010/validation-round23)；主专项的
状态见[执行记录](../exec/image-model-call-division-20261010.md)。

## 采用、失败与恢复

确认 backend listener、cwd、启动入口及活动 Runtime 子进程后，只对明确的
Dream 后端执行原有正常重启，保留 Admin、前端及 PostgreSQL。
新进程必须打印默认 Dream Runtime 0.1.11 的安全启动身份；健康检查不能
代替身份。安装或 manifest/native 校验失败时停止采用，保留失败回执；
回退只使用已验证的 0.1.10 安装及匹配 pin，不能覆盖 registry 或扩大权限。

大图 new/resume fixture 使用已发布实际 CLI 和 SDK、独立 home/workspace、
loopback fake Gateway，并复用原协议 probe；结果只说明技术行为，不能计入
正常账户 Run、Gateway request 或 Token 结算验收。

## 首轮发布后检查与当时限制（历史；最新状态见下文）

| 命令 | exit | 实际结果 |
|---|---|---|
| `python3 verify-public-runtime.py` | 0 | 五个公开精确包版本/平台/依赖/SHA-512/SHA-256及资格归档逐字节一致 |
| `npm install --global @glide-the/ink-claude-code-dream@0.1.11 …` | 0 | 本机原Node24正常安装；四平台fresh install由CI执行 |
| `.venv/bin/python -m pytest tests/test_sdk_env.py tests/test_dockerfile_claude_contract.py tests/test_verify_claude_registry_release.py tests/test_claude_plugin_cli.py -q -p no:cacheprovider` | 0 | 66 passed，13 subtests passed |
| `.venv/bin/python -m pytest tests/test_server_claude_agent.py -k startup -q -p no:cacheprovider` | 0 | 4 passed / 92 deselected；25项现有FastAPI生命周期警告 |
| `python published-cli-image-probe.py`（完整命令见round23 command） | 0 | 已发布实际CLI/SDK新建和同session resume均success；2 Messages POST，2400→2000px；fixture已清理 |
| `python3 adopt-normal-dream-runtime.py` | 0 | 保留原进程env（仅内存）；默认manifest预检、明确后端平滑重启和新身份通过；正常服务保留运行 |

Luna执行确定性/隔离检查，主执行者已读取原始command/out/exit；安装、
公开制品、正常进程采用由主执行者完成。最初进程检查因未安装psutil在读取前
退出，改用macOS原生只读接口后完成，没有为harness新增运行依赖。启动日志
只在本机权限0600保存，对外交付仅包含安全身份JSON。

round23正常本机Admin邮箱表单显示“The email or password is invalid”，只属于
独立Admin管理身份的拒绝。round24从正常Dream页面实际邮箱表单提交，沿配置
公开authority返回本机`/auth/callback`，观察到`invalid_scope` / “The following
scopes are invalid: images:create”，BFF为`BFF_OAUTH_CALLBACK_INVALID`。公开和
内部transport的OpenID metadata都声明支持images:create；实际OAuth客户端的
scope校验先于用户Session处理，不能判定Dream密码已通过或无效。正常Dream
会话未建立，未读取已有实体或模型，真实模型调用0；[新安全回执](/tmp/im-image-model-split-20261010/validation-round24/dream-account-login.json)
保留表单与错误事实，旧Admin拒绝回执不覆盖。目录同步属于现有Admin发布操作，
本轮未执行；不能按Schema缺失改变scope或绕过授权。
正常ink-memory / ink_memory只读生产边界检查为
`dream.image-turn.v1`存在false、匹配false、imageTurnCapabilityAvailable=false，
期望version 1 / hash `2f7e1eedb84d974b6bf203611acaf22b00d1cb82e377276a73822e73253f96e2`。
缺行不能证明角色grant状态。

因此普通Responses生成/编辑、显式Images生成/编辑、真实意图分工、
草图理解、正常Run/Thread/文件/历史/结算及真实断线取消重试均未完成业务验收。
源码及完整隔离浏览器矩阵的证据在专项执行记录；本轮没有远端部署、
Docker镜像构建或正常库DDL/grant，图片专项目标仍未完成。


## 2026-10-11 受控发布与正常采用更新

以上round23/24认证、scope及schema缺失为当时真实回执，保持原文。用户授权后，主执行者使用Admin唯一Drizzle migration入口发布至0080 image-turn capability，strict81/81无pending，并核对正常ink-memory及原角色权限。原OAuth publisher已同步实际browser/device clients的images:create；只向原Browser clients定向追加本机与公网已登记callback，其余secret、scope、PKCE、DPoP、resources及links未改。没有Dream runtime DDL、SQLite或替代账户。

登录导航由实际单值请求地址选择：本机页面进入本机中心，NATAPP公网页面进入公网中心。仍使用相同confidential service及自己的browser client；后台transport、issuer、resource稳定。两个/auth/options实际200且返回对应中心，本机现有账户可见登录和既有Thread重开成功；公网Chrome页面在react-dom脚本502/HTTP2失败时为空，不能声称公网完整登录已通过。

round26采用阶段历史：正常Admin当时采用r6构建p6VExBST7NFDcAnsStT5k。源码快照1718文件、manifest d52c0e7cd045a513095b683d72837d4da4994832dc6fbd6998c0525d51106d4d；910非cache制品hash7c08d8bdccfa43cd4c5f89602d0c34cd1a7a8436bf8857c393e3612eeeeefaaa。采用前源/.env/正常PG/HBA/空闲门禁通过，按本轮已识别frontend→backend→Admin supervisor优雅停止并逐项确认退出，原.next已备份。原入口、原配置和正常PG重新运行，backend安全启动身份仍为Runtime0.1.11、SDK0.2.145。采用后文档状态同步不属于发布代码变更；不声称全工作树hash永久不变。

round26业务阶段历史：r6修复实际CLI失败后user合并的完整当前素材块定位，独立设计和源码评审无P1/P2；严格pair/tail/解码和身份、能力、认领不变。采用后同账户既有Thread真实文字回复OK；普通图片请求明确提示选择支持图片的AI，显式image_gen明确提示先选择Image，没有图片接口执行。最新正常模型目录仍没有可调用native模型，该账户Free无Images entitlement，正向生成、编辑、返回新图与下载/重开尚不能通过真实模型验收。最终实际矩阵和命令回执以[专项执行记录](../exec/image-model-call-division-20261010.md)为准。


2026-10-11 round27：用户明确取消后续公网验收门禁，只使用本机正常业务链。受限只读传输检查观察到公网/边缘到NATAPP波动，完整返回时静态资源SHA与本机一致；没有建立页面代码缺陷，也没有修改边缘配置或重启正常服务。该调查不代表公网登录通过，后续不继续公网测试。本轮重新执行正常服务capabilities读取，image-turn精确version/hash、三个operations及实际OAuth browser images:create再次ready：[独立capability/scope回执](/tmp/im-image-model-split-20261010/validation-round27/actual-image-capabilities.json)。另一次正常库BEGIN READ ONLY只核对原角色权限与模型/账户资格，Responses图片声明为0、该账户Images entitlement=false：[独立资格回执](/tmp/im-image-model-split-20261010/validation-round27/normal-image-prerequisite-audit.json)。两份回执分别归属，不把数据库模型核对当成OAuth证明，仍不能标记正向图片验收完成。

## round29 最终本机正常采用及真实图片流程

2026-10-11 round29：两条图片链路已在指定现有账户、本机正常 Dream/Admin/Gateway/PostgreSQL 上完成实际生成、编辑、查看、下载、后续引用及历史重开；草图实际绘制并完成理解和内置编辑，显式 image_gen 在支持内置图片的 AI 下仍仅执行所选 Image 模型。闪烁修复后同图持续39秒稳定，后续真实SSE更新保持原Blob。最终AI恢复 gpt-6.1-sol，Image保留 codex-gpt-image-2；原多来源路由保持不可调用，用户自行选择已核实的非路由AI后才能执行内置图片。内置交付成功，但完整图片用量未报告，保留 RESPONSES_IMAGE_USAGE_UNKNOWN，不能称实际费用已知。故障注入与37项既有跳过的边界见执行记录；独立复核与文档、图示检查已通过；真实故障、跳过和未知用量的边界保持单列。

Runtime仍0.1.11、SDK0.2.145、CLI2.1.241，前轮生产发布事实保持；本轮不重新宣称四平台发布验证。最终r5正常Admin Build `Y-FUvVlfmQX52_mp077xs`，1721源文件SHA `c4ce4bd016cc3fa29ccf935670f0e706f7003716c2fecfafb37e4382cb8dadfd`，910非cache制品SHA `48e31a9a9ca77d78ef07715323767b35a5bc531d872c144e675b2ec595dee8ff`。原env、PG/HBA、空闲门与实际身份核对后，原frontend→backend→Admin supervisor优雅采用并重新运行原入口；未增加环境路径或临时账户。采用回执与真实单次调用关联见[专项执行记录](../exec/image-model-call-division-20261010.md)；正常Run/Thread/日志保留，公网按用户要求未测。
