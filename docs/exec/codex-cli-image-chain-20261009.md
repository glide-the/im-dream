<!-- [Input] 用户追问上传图片后Codex的实际生成/编辑入口；新提供/Users/dmeck/project/codex；既有API对比与IM设计。 -->
<!-- [Output] 新源码判断、完整执行链、历史保留、影响评估与本次具名验证回执。 -->
<!-- [Pos] 本轮源码/文档补充记录，不新增执行聊天，不实现IM图像功能。 -->
<!-- [Sync] 2026-10-09: 已补齐CLI证据与文稿，独立文档检查复跑exit 0、五图渲染exit 0；修订评审发现的范围措辞，未做真实模型或当前App验收。 -->

# Codex CLI图像完整链路：补充执行记录

目的：回答“生成和编辑究竟使用哪个接口，上传图片后如何执行”，补齐旧稿止于IPC的缺口。复用既有聊天及交付，不创建重复任务；依据用户最新要求不再输出规划提示词。范围为指定CLI的源码调查及相关文档修订，不实现IM图像Tool，不操作账户、数据库或已有服务。

## 源码与结论

2026-10-09读取`/Users/dmeck/project/codex`，HEAD为`a06545b311fe01e51ce855c7aa5d8da21e9e7aaf`，读取时`git status --porcelain`为空。此前调查读取的是`Codex-Original-Functionality-Round52-Delivery`，不能以旧恢复目录的未命中结论代替新CLI源码。

已定位主Agent Responses → namespace function `image_gen.imagegen` → `CodexImagesBackend` → `ImagesClient` → JSON `images/generations`或`images/edits`。默认app-server的本地图片输入转inline图片；编辑用原图路径或当前历史图片窗口；首个图片返回后尝试保存，通知以call ID关联。该路径不同于Responses内置`type:"image_generation"`。正常/失败时序、动态Provider URL与K1–K19文件/符号/行号见[完整执行链](../design/claude-agent/codex-cli-image-generation-chain.md)。

已修订[旧API对比](../design/claude-agent/codex-image-generation-call-comparison.md)的当前结论，原2026-10-07图示及调查保留并标明读取日。同步[源码研究](../design/claude-agent/image-generation-source-research.md)、[实施说明](../design/claude-agent/image-generation-implementation-notes.md)、[正式设计](../design/claude-agent/image-generation-interaction-design.md)、[PRD](../prd/chat/image-generation.md)和三个目录索引。修改前五份原文及SHA/字节清单保存在[history-baseline.json](../../frontend/test-results/codex-cli-image-chain-20261009/history-baseline.json)，源码基线见[source-baseline.json](../../frontend/test-results/codex-cli-image-chain-20261009/source-baseline.json)。原有四份设计/PRD历史稿没有覆盖。

## 影响与验证范围

| 范围 | 本轮处理 | 未验证行为 |
|---|---|---|
| 用户发起/上传 | 定位恢复客户端localImage及CLI turn/start映射 | 当前安装App文件选择接线 |
| Agent与Tool | 确认namespace function与独立Images执行 | 真实模型是否选择工具、生成质量 |
| 消息/事件 | 定位call ID、图片item、started/completed与媒体省略 | 当前App实际收到的通知 |
| 前端状态/展示 | 保留原恢复目录证据，不改变IM三幅业务图 | 当前App渲染与现场状态 |
| 文件/权限 | 定位原图读取与codex_home保存，标明失败仍返回图片 | 真实磁盘保存、文件访问及IM授权能力 |
| 持久化/重开 | 定位rollout策略、history builder及savedPath | App重启恢复、原文件长期可用 |
| 失败/取消/重试 | 定位参数/Provider/空图/保存失败；标明原turn与HTTP重试边界 | 远端取消、费用撤销、实际幂等 |
| 文本/Tool/媒体兼容 | 只修订文档来源判断，保留业务流程与历史图 | IM图像功能完整链路，因未实现而不能验收 |

检查由既有`luna_test_runner`按[luna-test-stage](/Users/dmeck/.codex/skills/luna-test-stage/SKILL.md)执行：Markdown文件头/目录清单/路径行号/JSON、历史字节与源码SHA、修改范围一致性，以及新增两幅CLI图和现行三幅业务图的Mermaid解析与SVG渲染。Chrome只启动一次；只关闭检查自有浏览器及临时Vite进程，不接触已有业务服务。检查分类为文档检查和源码基线一致性，不是功能或真实业务验收。

## 本轮命令回执

执行器为既有`luna_test_runner`。以下是本次已返回的原始回执，见[commands.json](../../frontend/test-results/codex-cli-image-chain-20261009/commands.json)及[一致性评审](../../frontend/test-results/codex-cli-image-chain-20261009/consistency-review.md)。表中省略保存stdout的tee部分，完整命令及cwd在JSON中。

| 命令 | cwd | 退出码 | 关键结果与实际范围 |
|---|---|---|---|
| `python3 frontend/test-results/codex-cli-image-chain-20261009/check-docs.py` 首次 | 仓库根 | 1 | 旧历史清单缺少source键，harness触发KeyError；保留[首次输出](../../frontend/test-results/codex-cli-image-chain-20261009/check-docs.out)。 |
| 同一Python命令，主执行者改为entry.get后复跑 | 仓库根 | 0 | 14目标/14文件头，11清单，193本地链接/66行号，8 JSON；9原文、27源码SHA、原10+3图均保持；errors=[]。见[复跑输出](../../frontend/test-results/codex-cli-image-chain-20261009/check-docs-rerun.out)。 |
| `node test-results/codex-cli-image-chain-20261009/render-mermaid.mjs` | frontend | 0 | Chrome单次启动，新增CLI两图+现行业务三图5/5解析和SVG成功，自有Chrome/Vite已关闭。见[图示回执](../../frontend/test-results/codex-cli-image-chain-20261009/mermaid-receipt.json)。 |
| `git diff --check -- docs/design/claude-agent/.folder.md docs/exec/.folder.md docs/prd/chat/.folder.md` | 仓库根 | 0 | 限定目录索引无空白错误；未把无关工作区改动纳入。 |
| `git -C /Users/dmeck/project/codex rev-parse HEAD`、`status --porcelain` | 仓库根 | 均0 | HEAD与读取基线一致，源码工作区为空。 |

评审未发现主Responses、自定义namespace function、独立Images、图片选择、保存失败或历史边界的事实矛盾。发现旧API对比§17中的“本次”可能包括新CLI范围，主执行者已改成“原2026-10-07交付src及恢复src调查”，并明确新CLI修订见§18。收口再次检查当前文稿；图示未修改，不重复启动Chrome。执行器另有一次macOS `find -printf`产物探针退出1，记录在commands.json，不作为文档或产品失败。

Rust已有隔离测试只作为源码证据阅读，没有运行；不把测试文件存在、旧回执、源码SHA相同或图示通过写成图像功能通过。外部链接只核对引用形式，没有重新访问网络。

## 状态与剩余边界

文稿修订已写入，独立回执已返回，评审发现的范围措辞已修正；收口检查由同一执行器继续记录。本轮不另建目标或递归创建聊天。当前安装App与指定CLI的版本对应、现场界面、真实Provider请求、IM Admin授权图像能力仍未验证；这些不阻碍本轮源码结论，但实施或真实验收前必须取得对应证据。
