<!-- [Input] SUO-422 execute handoff, task_411-01 N1-rollback contract, preserved frontend/dist baseline, and run-scoped Docker smoke evidence. -->
<!-- [Output] Immutable Vite rollback image tag/digest, isolated smoke verdict, cleanup receipt, and parent handoff. -->
<!-- [Pos] Child execute report for SUO-422; it supplements only N1-rollback and does not reopen or rewrite task_411-01 source implementation. -->
<!-- [Sync] 2026-09-05: initialized the checked-out SUO-422 immutable Vite rollback smoke record. -->
<!-- [Sync] 2026-09-06: rebased current Dream source references from the retired frontend/src tree to frontend/app/_dream. -->

# Exec Report: task_411-01 — Immutable Vite Rollback Smoke

## 1. 任务标题与唯一 Execute Issue

- Task ID：`task_411-01`，本 child 仅补 `N1-rollback`。
- Execute Issue：`SUO-422` — `[unblock] Provide immutable Vite rollback image smoke for task_411-01`。
- Parent execute：`SUO-419`。
- Issue 状态 / work mode / priority：执行开始时为 `in_progress` / `standard` / `high`。
- Domain / labels：`frontend` / canonical labels `mcp-apps, dec-005, nextjs, workspace, web-shell, vite-exit`；child 未返回独立 labels，沿用 task 绑定仅用于分类。
- 唯一 assignee：`ExecTaskAgent`（agent id `2a7a15fe-2ebb-4dc5-91a8-48ae2bcc5471`）；`assigneeUserId=null`。
- 正式 checkout：2026-09-05 本 heartbeat 对 `SUO-422` 的 `POST /api/issues/{id}/checkout` 已成功，随后 GET 回执为 `status=in_progress` 且 assignee 与本 Agent 一致。
- 最新 handoff：CEOOrchestrator comment `c5fa83ca-2272-4fdd-89bf-b015f44f8b7d` 明确要求本 Agent 重新 checkout，并把写入闭集缩小为本报告、run scratch 和一个具名 image/container/loopback port；pass 或 fail 都必须将 child 收口为 `done`。

## 2. Task / Requirement / Stage 绑定

### 2.1 唯一来源

- Canonical module：`docs/issue/ISSUES_mcp_apps_system_architecture.md` 的 `MCPAPPS-411-01`。
- Task：`docs/task/task_411-01_frontend_root-web-shell-vite-exit.md`。
- Independent requirement：`docs/task/TASK-REQUIREMENT-task_411-01_frontend_root-web-shell-vite-exit.md`。
- Reusable template：`docs/task/TASK-REQUIREMENT-FORMAT.md`（已在其他 task/stage/design 输入前读取）。
- Stage：`docs/stage/stage_mcp-apps-system-architecture.md` 的 Stage 1；readiness ancestor 为 `SUO-416`（done），stage ancestor 为 `SUO-414`（done）。
- Direct design：`docs/design/claude-agent/dream-frontend-node-framework-migration-assessment.md` §3.2、§6、§9—§11、DEC-005；`docs/design/claude-agent/mcp-apps-system-architecture-execution-checklist.md` §5.1、§10—§12。
- 单一绑定：本报告不合并 `MCPAPPS-411-02/03`，不继承旧 `task_302`、旧 nested Next、旧 lock 或旧 Exec/evidence 的通过结论。

### 2.2 TASK-REQUIREMENT-FORMAT.md 填充摘要

| 模板字段 | 本次填充值 |
|---|---|
| Execute Issue | `SUO-422`，只执行 `task_411-01 / N1-rollback`，正式 checkout，唯一 assignee，无 blocker edge。 |
| Canonical Issue | `MCPAPPS-411-01`；Vite rollback 必须是一个具名、已验证的 image，且保持 Python API、OAuth/data 和 production-off 边界。 |
| Task / Requirement | 上述唯一 task 与独立 requirement；child handoff 的更窄闭集覆盖 parent task 的广泛源码闭集。 |
| Stage | Stage 1，仅补缺失 rollback receipt；不宣告其余 `N1-*`、Stage 2、P0、standalone 或 production Gate 通过。 |
| Design contract | DEC-005；回滚不得恢复 nested Next、legacy Runtime、第二默认入口或生产 Apps。 |
| Dependencies / blockers | 执行开始无 first-class blocker；本机 Docker daemon 是 harness 前置，失败时归类为 harness fail 并仍交付 fail verdict。 |
| Allowed writes | 仅本报告；`PAPERCLIP_RUN_SCRATCH_DIR` 临时 build context；恰好一个具名 rollback image/tag+digest；恰好一个具名 task-owned container；一次解析的 loopback free port；Issue 评论。 |
| Forbidden writes | 除本报告外全部 repo 路径；尤其 parent source、nested Next、Vite source default entry、locks/old evidence、Runtime aliases、backend/database、production Apps，以及用户已有容器/服务/镜像。未列路径默认禁止。 |
| Delete set | 只允许停止/删除本轮具名 container；不得删除镜像或其他持久对象。 |
| Acceptance | `N1-rollback-smoke-image`、`N1-rollback-smoke-frontend`、`N1-rollback-smoke-api`、`N1-rollback-smoke-boundary`、`N1-rollback-smoke-cleanup`，详见 §8。 |
| Test boundary | 只执行最小容器 smoke；daemon/runner 失败是 harness 前置失败，不冒充页面或 API 缺陷；所有输出脱敏。 |
| Shared owners | `frontend/pnpm-lock.yaml` exclusive writer 为 411-03，本 child read-only；schema/backend/production flag 均 read-only；本 child 只拥有新 rollback image 与具名 container。 |
| Rollback | 保持 `production_apps_effective=false`，停止并删除本轮具名 container；保留唯一 image 供 parent 引用；不触碰数据、OAuth、backend 或用户服务。 |

Fill Gate 结论：`GO`。所有必要字段已具体化；当前唯一可写 repo 路径在执行前不存在且不与 dirty tree 重叠。

## 3. 模型生成的执行任务

本 Agent 以 §2.2 的完整填充结果作为模型输入，生成并通过闭集复核后的执行任务如下：

1. 记录 checkout、single-assignee、执行前 dirty-tree 指纹和 `frontend/dist/` baseline inventory；不修改 baseline。
2. 运行 `docker info`；若 daemon 不可达，使用授权的 Docker Desktop 启动动作并进行有界复检。若仍失败，直接形成 harness-fail verdict 和清理证明。
3. 在 `PAPERCLIP_RUN_SCRATCH_DIR` 创建只复制 `frontend/dist/` 的最小 Nginx build context；固定唯一 tag `ink-dream-vite-rollback:task-411-01-suo-422`。
4. build/select 恰好一个 image，使用 Docker image ID 的 `sha256` 作为本机不可变 digest，并用 inspect 复核 tag→ID 映射。
5. 一次性解析一个 loopback free port，启动唯一 container `ink-dream-vite-rollback-task-411-01-suo-422`，不得使用/停止其他容器。
6. 验证 frontend HTML/runtime config、容器网络/只读静态服务、当前 Python API 的 loopback reachability（若本机公开入口不可达则如实失败）、OAuth/data 无迁移/无写入边界和 `production_apps_effective=false` 的静态/运行时证据。
7. 只停止/删除该具名 container，复核其不存在；保留 image，记录 tag/digest、所有命令退出码、关键脱敏输出与明确 pass/fail verdict。
8. 对照执行前后 Git 状态，确认除本报告外没有本轮 repo 写入；在 Issue 评论提交证据并将 child 标记 `done`。

## 4. 任务目标与责任边界

唯一目标是为 parent `SUO-419` 提供当前工作区 `frontend/dist/` baseline 的一个不可变 Vite rollback image 及隔离容器 smoke receipt。该结果不恢复 Vite 源码入口，不改变 Next 默认入口，不修改 Python API、OAuth、数据、Runtime、lock 或 production Apps，也不表示 `N1-01`—`N1-04`、Stage 1 整体、Stage 2/3 或任何 production Gate 通过。

## 5. 涉及文件路径（允许、禁止、删除集合）

### 5.1 允许

| 路径 / 对象 | 动作 | 说明 |
|---|---|---|
| `docs/exec/exec_task_411-01_immutable-vite-rollback-smoke.md` | create/update | 唯一 repo 写入。 |
| `$PAPERCLIP_RUN_SCRATCH_DIR/**` | create/update | 临时 build context/evidence；由 Paperclip run 清理。 |
| `frontend/dist/**` | read-only | 保留 baseline，仅作为 image 输入。 |
| `ink-dream-vite-rollback:task-411-01-suo-422` | create/select/inspect | 恰好一个 image/tag；完成后保留。 |
| `ink-dream-vite-rollback-task-411-01-suo-422` | create/inspect/stop/remove | 恰好一个 task-owned container。 |
| 一次解析的 `127.0.0.1:<free-port>` | bind/probe/release | 只绑定本轮 container。 |

### 5.2 禁止与删除集合

- 除本报告外的全部 repo path 均禁止写入；`frontend/**`、`backend/**`、`deploy/**`、其他 `docs/**` 全部只读。
- 禁止恢复 nested Next、source-built Vite 默认入口、old lock/evidence、Runtime alias、schema 或 production Apps。
- 禁止停止、删除、重启或修改用户已有容器、服务和镜像。
- 精确删除集合只有 `ink-dream-vite-rollback-task-411-01-suo-422` container；image 不删除。

## 6. 输入 / 输出说明

- 输入：当前 preserved `frontend/dist/`（执行前 `121` files、`48,857,088` bytes）、N1 rollback contracts、本机 Docker daemon/API 可用性。
- 输出：一个 tag→immutable `sha256` image ID 映射、一个隔离容器 smoke verdict、cleanup receipt、本报告和 Issue comment。

## 7. dirty-tree、checkout 和 single-assignee 证据

- 执行前命令：`git status --porcelain=v1 --untracked-files=all`，exit `0`。
- 执行前 dirty path 数：`1123`；完整输出 SHA-256：`3936d13dc6072b44580fb8ffdb19e6a8bd12af753ed51960cb19e7814fa541ee`。
- 顶层分布：`README.md=1`、`README.zh.md=1`、`backend=18`、`deploy=1`、`docs=60`、`frontend=1042`。这些均是继承的用户/其他 Agent 改动，本 child 全部保留。
- `git status -- ...report frontend/dist` 在创建报告前无输出：报告不存在，`frontend/dist/**` 不在 dirty tree，故没有写入冲突。
- Checkout / assignee：见 §1；无第二 agent/user assignee，无 unresolved blocker。

## 8. 验收矩阵与测试策略

| 验收 ID | 可观察条件 | 命令 / 方法 | 通过标准 | 失败 owner / action |
|---|---|---|---|---|
| `N1-rollback-smoke-image` | 唯一 tag 映射到 immutable `sha256` | `docker build`、`docker image inspect` | build/select exit 0；tag 唯一；image ID 为 `sha256:*` | Docker harness owner 恢复 daemon；parent 不把失败当产品缺陷。 |
| `N1-rollback-smoke-frontend` | 隔离容器返回 Vite HTML 和 runtime config | `docker run`、loopback `curl` | HTTP 2xx；HTML 指向 Vite assets；runtime config 可读 | ExecTaskAgent 记录 image/container 日志；不得改 source。 |
| `N1-rollback-smoke-api` | rollback UI 的 Python API boundary 可达 | loopback/current configured API probe | API health 可连接且无容器内数据迁移 | Parent/backend owner 处理既有 API 不可达；本 child 不改 backend。 |
| `N1-rollback-smoke-boundary` | OAuth/data 不迁移、不写入，production Apps 保持 false | 静态 config/route probe、容器 mount/inspect、前后状态对比 | 无 DB volume/写入；OAuth/API endpoint 保留；明确 `production_apps_effective=false` | Parent owner 保持 No-Go；不得启用 Apps。 |
| `N1-rollback-smoke-cleanup` | 只清理具名 container | `docker stop/rm` 或 `docker rm -f` 精确名、inspect negative | container 不存在；其他容器未触碰；image 保留 | ExecTaskAgent 立即停止，报告实际残留与精确清理动作。 |

## 9. 实现变更记录

| 文件 / 对象 | 操作 | 说明 |
|---|---|---|
| 本报告 | create/update | 执行上下文、证据、verdict 与回滚建议。 |
| `$PAPERCLIP_RUN_SCRATCH_DIR/docker-desktop-status.out` | create | Docker Desktop 状态命令的 run-owned 临时输出；不含凭证。 |
| `ink-dream-vite-rollback:task-411-01-suo-422` | not created | daemon 不可达，未 build/select/tag；因此不存在可记录的 image digest。 |
| `ink-dream-vite-rollback-task-411-01-suo-422` | not created | daemon 不可达，未创建或启动 container。 |

未修改 `frontend/dist/**` 或任何 parent source；未创建 Docker build context，因为 daemon gate 在 packaging 前已 fail closed。

## 10. 测试结果与验证证据

### 10.1 Baseline 与静态边界

| 命令 / 方法 | Exit | 脱敏关键输出 | 结论 |
|---|---:|---|---|
| `find frontend/dist -type f` + size inventory | `0` | `121` files；`48,857,088` bytes | preserved baseline 存在且在执行前不属于 dirty tree。 |
| 每文件 SHA-256 排序后再 SHA-256 | `0` | manifest digest `66322acd4b9817808a05785d879063e134c3814a8c81f4983cfff22e771467b8` | 只读 baseline 指纹；这不是 Docker image digest。 |
| `rg` 读取 `frontend/dist/index.html` asset refs | `0` | `/runtime-config.js?runtime=1`、`/assets/index-B0ZdeL1J.js`、`/assets/index-DPjEMJl3.css` | baseline 是现有 Vite 静态产物。 |
| `sed` 读取 `frontend/dist/runtime-config.js` | `0` | `apiBaseUrl: ''`、`wsBaseUrl: ''` | 默认使用 same-origin API/WS，不需要改写 source。 |
| bundle production-off gate 定位 | `0` | `fetch('/api/mcp-apps/phase1-status')` 后明确要求 `productionAppsEffective === false` | 仅证明 baseline bundle 的静态 fail-closed gate；因容器未启动，不冒充 runtime 验证。 |

### 10.2 Docker daemon 恢复与 smoke

| 命令 / 方法 | Exit / 结果 | 脱敏关键输出 | 分类 |
|---|---:|---|---|
| `docker info --format '{{.ServerVersion}}'` | `1` | cannot connect to `~/.docker/run/docker.sock` | Harness prerequisite fail。 |
| `open -a Docker` | `0` | 启动请求被 macOS 接受 | 不是 daemon-ready 证明。 |
| 最多 15 次、每次间隔 3 秒的 `docker info` | final `1` | `docker_ready=0`；socket 不存在 | 45 秒有界恢复失败。 |
| `docker desktop status` | `1` | `Could not retrieve status. Is Docker Desktop running?` | 官方 CLI 确认 Desktop 不可用。 |
| Docker host log 只读诊断 | `0` | `com.docker.backend` 多次 `unmarshaling start request: unexpected EOF` 后退出 | daemon bootstrap/harness 故障，不是 Dream 页面或 API 缺陷。 |
| `docker desktop start` | bounded call interrupted after no ready state | 命令未返回成功；随后 `docker info` 仍为 `1` | 避免无限阻塞；未取得 daemon。 |
| 最终 `docker info` / process / socket 复核 | `1` / `0` process / absent | daemon 仍不可达 | packaging、run、HTTP/API probe 均无法合法执行。 |

环境中未发现 `podman`、`colima`、`lima`、`nerdctl` 或 `finch`；更重要的是，Issue 未批准任何替代容器 harness，因此没有用非 Docker 路径冒充验收。

### 10.3 验收结果

| 验收 ID | 结果 | 证据 / 未运行原因 | 失败 owner / action |
|---|---|---|---|
| `N1-rollback-smoke-image` | **FAIL** | daemon gate 失败，无法创建唯一 image，故 tag 无 immutable `sha256` image digest。 | Local Docker harness owner：修复 Docker Desktop backend 的 `unexpected EOF` 启动失败后，由 parent 新建/复用专门 child 重跑相同闭集。 |
| `N1-rollback-smoke-frontend` | **NOT RUN** | 没有 image/container；不能执行 loopback HTTP probe。 | 同上；不得据此判定 frontend 有缺陷。 |
| `N1-rollback-smoke-api` | **NOT RUN** | 隔离容器未启动，无法验证从 rollback UI 到 Python API 的 reachability。 | 同上；不得据此判定 Python API 有缺陷。 |
| `N1-rollback-smoke-boundary` | **PARTIAL / FAIL** | 静态 bundle 要求 `productionAppsEffective === false`，且 baseline 未被修改；OAuth/data/runtime preservation 未经容器 smoke，不能宣布通过。 | Parent `SUO-419` 继续保持 N1-rollback No-Go；daemon 恢复后补运行时证据。 |
| `N1-rollback-smoke-cleanup` | **PASS (vacuous)** | daemon 从未可用，build/run 均未发生；具名 image/container 未由本轮创建。最终 process count `0`、socket absent。 | 无清理对象；不得删除用户镜像/容器。 |

### 10.4 Repo 闭集验证

| 命令 | Exit | 关键输出 |
|---|---:|---|
| `git status --porcelain=v1 --untracked-files=all -- docs/exec/exec_task_411-01_immutable-vite-rollback-smoke.md frontend/dist` | `0` | 只有本报告为 `??`；`frontend/dist/**` 无状态变化。 |
| Report header/section/path/trailing-whitespace validation | `0` | 4-line file header；required sections/path inventory `ok`；trailing whitespace `0`；未决项 `0`。 |
| 执行后完整 `git status --porcelain=v1 --untracked-files=all` | `0` | `1124` paths；SHA-256 `9c6481922da853574fd07481ee96d72baa13e22678e41c81ab34f76307eb84af`；相对执行前只增加本报告一个 untracked path。 |
| 具名进程与最终 daemon 复核 | `0` / daemon probe `1` | 具名进程数 `0`；Docker daemon 仍不可达。 |

未执行 `docker build`、`docker image inspect`、`docker run`、container inspect/logs、HTTP/API/OAuth/data runtime probes 或 named-container stop/remove，因为这些命令均依赖未取得的 daemon；跳过项已明确归因于 harness prerequisite。

## 11. 风险、阻塞与 owner/action

- Docker daemon harness 不可达；该情形形成明确 `FAIL` verdict，但不得判断 Dream 页面、Python API、OAuth 或数据边界存在产品缺陷。
- `frontend/dist/` 是只读 baseline；若在 build 前发生漂移，停止并由 parent owner 重新确认 baseline。
- 本 child 不拥有真实 OAuth 会话或业务数据写入权限；preservation 通过无数据卷/无迁移、公开入口可达性和 production-off 负向证据判定，不执行真实用户数据变更。
- 后续 owner/action：本机 Docker harness owner 修复 Docker Desktop backend 启动；parent `SUO-419` 在新的正式 checkout 中重新派发同一 N1-rollback smoke。当前 child 按 handoff 要求以 fail verdict 结束，不保留伪 `in_progress` continuation。

## 12. 完成标志、Stage handoff 与回滚步骤

- [x] 唯一 image/tag/digest 未能生成，并以 daemon harness fail 明确记录。
- [x] 隔离 frontend/API/OAuth/data/production-off probes 以 harness 前置 fail 明确收口；未冒充产品缺陷或通过结果。
- [x] 本轮未创建具名 container，故无 container 可停止/删除；未触碰用户资源。
- [x] repo 写入闭集复核完成。
- [x] fail verdict 已写明，child 可按 handoff 标记 `done`。

回滚/清理顺序：保持 `production_apps_effective=false` → 精确停止并删除本轮具名 container → 释放本轮 loopback port → 保留唯一 image/tag/digest 供 parent 手动选择 → 不修改 Python API、OAuth、数据、nested Next、Vite source、lock、Runtime 或用户服务。

## 13. 执行完成报告

最终 verdict：`FAIL — HARNESS PREREQUISITE`。

- 缺失的必需证据：immutable Docker image digest、隔离 frontend response、Python API reachability、OAuth/data runtime preservation、`production_apps_effective=false` runtime probe。
- 已证明：baseline 存在且未修改；静态 bundle 保持 production-off fail-closed gate；本轮没有创建/删除任何 image/container，没有修改 parent source 或用户服务。
- Parent handoff：`SUO-419` 不得将本 child 当作 `N1-rollback` 通过；修复 Docker Desktop backend 后需要新的 checkout 和一次完整重跑。
- 回滚建议：无需 repo 或 container 回滚；本轮唯一持久变更是本报告。run scratch 由 Paperclip 清理。
- 文档维护：`docs/exec/.folder.md` 已用 `exec_*.md` 泛型条目覆盖本文件，因此无需越权修改 folder inventory。
