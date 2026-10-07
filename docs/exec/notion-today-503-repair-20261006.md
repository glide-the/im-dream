<!-- [Input] User's connector-list 200/today 503 report, current server configuration and pinned ntn driver. -->
<!-- [Output] Scoped diagnosis, configuration repair, public-route recovery tests and actual execution receipts. -->
<!-- [Pos] Calendar Notion operational repair evidence; isolated tests do not certify real-account availability. -->
<!-- [Sync] 2026-10-06: record the missing explicit API date and preserve the previous implementation/validation evidence. -->

# Notion 今日接口 503 修复记录

## 影响评估与验证边界

- Git 基线：`develop` / `dc5c7723f28bc75efe55f7573182fe857782dbdf`。工作区已有上一轮 Calendar 实现、测试、现行文档及历史稿，保留全部既有改动。
- 用户观察：`GET /api/connectors` 为 200，同一个 connector 的今日读取为 503。仅访问日志不能唯一确定错误码；本轮只读核对发现正常 `backend/.env` 未设置 `INK_NOTION_TODAY_API_VERSION`，当前实现会在 Search 前返回 `NOTION_API_VERSION_UNCONFIGURED`。
- 当前调用边界：既有 router → actor facade → Admin connector 归属/用户 IANA 时区 → 服务器 API 日期校验 → 有效凭证 Provider → `ntn` Search。补齐服务器配置不改变认证、归属、正文读取权限、选择、同步或 schema。
- 本轮文件所有权：本机未纳入 Git 的 `backend/.env` 中该配置键；配置示例、README 中英镜像、`backend/tests/test_notion_today.py` 的回归用例，以及现行 Calendar PRD/正式设计中的版本合同和受影响目录清单。本轮不接管其他未提交文件。
- 业务影响：仅修复今日元数据读取的运行前置条件；原页签、日期、任务安排/结果/编辑/历史、日记、连接器配置和 Chat 导航不改代码。
- 资源边界：验证只用已有真实公开路由及 Admin DTO 内存 fixture；CLI 请求头探测用独立临时 home、明确假凭证及自建 loopback HTTP server，不访问真实 Notion、正文或数据库，不停止既有服务。只清理本轮自建资源。
- 必需回归：缺失/非法版本时列表 200、今日 503且无 Search；显式配置后同一读取入口恢复 200；既有今日分页、时间边界、异常/上下文和原连接器业务流程回归；实际固定 CLI 默认及显式 header 回执；Markdown 清单/引用与 `git diff --check`。
- 页面与构建源码未改变，本轮不重复已通过的浏览器全集或 production build。实际执行结果另行记录，不把先前 39 项浏览器通过算作本轮执行。
- 实际服务边界：诊断时本机 8765、5173、3000 未监听，用户那次响应体未捕获；配置修复和隔离恢复验证不能代替正常服务重启后的真实账户读取。

## 诊断、修复与回执

已补齐本机配置及安装示例，并完成隔离自动化恢复验证；正常服务重启后的真实账户复测尚未执行。

- 实际固定 CLI 版本为 `ntn 0.15.1`。独立 loopback server 捕获默认及显式参数请求，两次均为 `POST /v1/search`、`Notion-Version: 2026-03-11`、退出码 0。该日期来自已安装固定 CLI 的实际 header，而非路径或最新文档推测。
- 本机 `backend/.env` 原来没有 `INK_NOTION_TODAY_API_VERSION`，本轮只追加该键为 `2026-03-11` 及说明。该文件仍被 Git 忽略；没有提交凭证。模板采用同样的显式日期，程序仍保留“缺失或非法配置即失败”的原合同，没有增加隐式默认、runtime DDL 或认证旁路。
- 新增 `TodayPublicRoute.test_missing_api_version_keeps_connector_list_available_and_recovers`：缺失、非日期、非法日期三种输入均验证 connector list 200 / today 503、错误码和上游零调用；随后显式设置 `2026-03-11`，同一公开 today 入口 200、仅调用一次 Search。
- 同步 README 中英镜像、现行 Calendar PRD、正式交互稿、文件头及目录清单。页面骨架、三份 Mermaid 时序/状态图、页面和其他业务行为未改变；本轮未删除或覆盖历史文档。

| 实际检查 | 退出码 | 关键结果 / 证据 |
| --- | --- | --- |
| 原公开路由缺配置复现 | 0 | 503 / `NOTION_API_VERSION_UNCONFIGURED` / upstream 0；[初始探测日志](../../output/notion-today-503-20261006/public-route-missing-version.log)，fixture 结果不等同用户那次真实响应体 |
| 最后源码四文件后端回归 | 0 | **38 passed, 3 subtests passed in 2.00s，0 failed，0 skipped**；[最终原始日志](../../output/notion-today-503-20261006/backend-regression-final.log) |
| 固定原生 CLI 版本与 API 请求头 | 0 | 默认/显式 header 均为 `2026-03-11`；[可重放脚本](../../output/notion-today-503-20261006/verify_cli_contract.py)、[命令回执](../../output/notion-today-503-20261006/cli-contract-command.log)、[原始 JSON](../../output/notion-today-503-20261006/cli-contract-final.json) |
| Markdown 清单、头部、引用、历史 | 0 | 51 changed Markdown、目录/头部/引用零缺口、5/5历史一致；[文档原始日志](../../output/notion-today-503-20261006/doc-validation.log) |
| `git diff --check` | 0 | 无输出；[diff 原始日志](../../output/notion-today-503-20261006/diff-check.log) |
| 页面浏览器全集 / production build | 本轮未重复 | UI 与生产模块未改动；前轮回执保持，不计作本轮执行 |
| 正常服务 / 真实 Notion 账户 | 未执行 | 诊断时本机 Dream 8765 无监听，未取得用户真实请求响应体；无法报告真实读取已恢复 |

实际命令：

```bash
# 工作目录：backend；使用 conftest 中已有 provider-free Admin OAuth fixture。
PYTHONPATH=/Users/dmeck/project/ink-dream-memory/backend .venv/bin/python -m pytest tests/test_notion_today.py tests/test_notion_operations.py tests/test_notion_connector_router_flow.py tests/test_admin_notion_connector_data.py -q
# 工作目录：仓库根；独立 home、fake token、自建 loopback server。
backend/.venv/bin/python output/notion-today-503-20261006/verify_cli_contract.py
# 工作目录：仓库根；最终文档检查。
python3 output/playwright/calendar-tabs-20261005/doc_checker_all_20261005.py /Users/dmeck/project/ink-dream-memory
git diff --check
```

## 首次前置失败、清理及剩余动作

- 初次直接使用 `unittest`，未加载项目 pytest 的 `conftest.py` provider-free token fixture，8 tests 中 5 个因 fake Admin 的 OAuth 请求缺 `x-request-id` 失败。这是执行入口导致的 harness 问题；改用现有标准 pytest 后38项及3子测试全通过，没有为它改变生产认证代码。[首次失败回执](../../output/notion-today-503-20261006/initial-harness-failure-receipt.md)为实际工具回执转录，明确不冒充原始 stderr。
- 初次 CLI 探测带 `--json`，固定 CLI 报不支持，exit 2；去掉该参数后两次请求 exit 0。生产 `NotionOperationClient._run_endpoint` 本来就不传 `--json`，因此这不是用户 503 的实现原因。[保留的初次 CLI 日志](../../output/notion-today-503-20261006/cli-probe.log)未覆盖。
- 已关闭本轮自建 HTTP server、删除本轮临时 Notion homes；不访问真实凭证、正文、数据库或模型，不停止用户已有服务。仅保留具名验证脚本、原始日志及报告。
- Git 仍为 `develop` / `dc5c7723f28bc75efe55f7573182fe857782dbdf`；本轮没有 commit 或 PR，没有回退原有未提交改动。
- 需要由正常 Dream 后端启动/重启加载现已补齐的 env，然后原日历今日入口刷新。若仍为503，应以该请求 `detail.error_code` 区分时区、Admin能力等其他来源；本轮不会把隔离恢复结果冒充真实上游通过。
- 今日资源范围仍为用户已接受的 **Search 可发现页面**，严格授权全集的 API 能力边界未改变。

前轮实施与原始失败历史见[日历实施记录](./calendar-right-panel-tabs-implementation-20261005.md)。本轮不覆盖其中的历史命令或验证状态。
