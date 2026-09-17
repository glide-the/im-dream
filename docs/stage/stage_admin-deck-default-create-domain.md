<!-- [Input] Dream Deck create/default routes, local Claude artifact verifier, existing Admin Deck/Voice operations and default policy. -->
<!-- [Output] Prompt-architect plan for closing Dream Deck create/default SQL through one purpose-specific preparation read and existing Admin aggregate writes. -->
<!-- [Pos] Remaining production database-access migration stage; Admin owns Deck transactions while Dream keeps local artifact/CLI verification. -->
<!-- [Sync] 2026-09-15: freeze two-step candidate verification, write receipt recovery and public route behavior before implementation. -->

# Deck 创建与默认插件修复数据接口迁移

## 背景与问题

Dream `backend/routers/voices.py` 的 `POST /api/decks` 和 `POST /api/decks/defaults/reconcile` 仍经 `services/deck/defaults.py`、`database.create_deck`、`database.reconcile_default_screenplay_deck_plugin_ref` 直连 PostgreSQL。Admin 已经实现 `deck.create`、`deck.reconcile-default` 与 `deck.provision-default` 的严格 DTO、Drizzle Repository、actor 锁、插件安装二次匹配和事务回执，但 Dream 无法在不知道安装 ID 的情况下调用它们。现有 `deck-plugin-refs.prepare` 只接受浏览器已经选择的安装 ID，不能用于服务端配置的默认插件查找。

## 目标与边界

- Admin 增加一个只读业务操作 `deck.default-plugin.resolve`：根据 Admin 的 `DREAM_DECK_POLICY_JSON` 精确选择一个 ready 安装，只返回 Dream 本地校验所需的闭合候选 DTO；找不到时返回 `installation: null`。
- Dream 调用该接口后继续在本机共享文件系统验证 artifact digest，并使用本机 Claude CLI 检查 `compatibility_json`。验证通过后只把四字段 evidence 交给已有 `deck.create` 或 `deck.reconcile-default`。
- Admin 写事务再次按安装 ID、配置的 package/version、digest 和 ready 状态锁定并匹配数据库行。候选在读写之间变化时写操作拒绝，不能留下 Deck 或部分 ref。
- 当前用户身份只来自 OAuth actor；浏览器不能提供安装候选、evidence、owner、SQL、表列名或配置值。Dream 不保留 PostgreSQL fallback。
- 保留公开路径、创建响应 `{"deck_id": ...}`、reconcile 响应、默认插件不可用的 409 反馈、Deck/Voice/version/ref 事务和共享文件系统语义。本阶段无 migration。

## 概念与规则

`deck.default-plugin.resolve` 输入为空 strict DTO，输出 nullable 安装候选：`plugin_installation_id`、`package_name`、`marketplace`、`resolved_version`、`artifact_digest` 与 `compatibility_json`。Repository 只使用 Admin typed Drizzle schema，并按 Admin 配置精确过滤 package/version/status；若历史库意外存在多个匹配行，使用已有安装唯一性/排序规则稳定选择，不返回其他安装。

Dream 的 local verifier 不访问数据库，只读取候选指向的 artifact store 并调用现有 CLI SemVer 校验。通过后构造已有 `default_plugin_evidence` 四字段 DTO。`deck.create` 与 `deck.reconcile-default` 使用各自原始 request ID；超时或响应解析失败后仅查询一次对应 operation receipt，committed 返回原结果，absent/未知保持 `outcome_unknown=true`，不得盲目重写。只读 resolve 可沿用统一客户端的有界 transport 行为。

## Optimized Prompt

You are the Admin/Dream Deck default-plugin migration owner. Read both repositories' AGENTS/Agent/folder/rule contracts; Dream `backend/routers/voices.py`, `backend/services/deck/defaults.py`, the exact legacy Deck create/reconcile helpers and tests; Dream `deck_refs_data.py`, `AdminDataClient`, request-auth registration and receipt-recovery patterns; Admin `deckVoiceDto/Service/Repository/Handler`, `deckRuntimeData` installation DTOs, Drizzle plugin-installation schema, operation registry and `adminDeckVoice.contract.ts`. Implement the minimum closed interface needed to remove every production PostgreSQL call from the two public routes.

Add exactly one Admin read operation, `deck.default-plugin.resolve`, with a strict empty input and a nullable purpose-specific installation DTO containing only `plugin_installation_id`, `package_name`, `marketplace`, `resolved_version`, `artifact_digest` and `compatibility_json`. Derive the configured package/version from Admin `DREAM_DECK_POLICY_JSON`; require OAuth `dream:read`, reject Thread/entity delegation, query through a typed Drizzle Repository in the existing UOW and return only a ready exact match. Do not expose installation listing, arbitrary package/version selectors, user IDs, SQL, table or column names. No migration is expected.

In Dream, extend the typed Admin Deck consumer with the exact new read hash plus existing `deck.create` and `deck.reconcile-default` hashes. Resolve the candidate server-side, locally reuse `PluginInstallService.verify_installation_artifact` and `check_cli_compatibility`, then reduce it to the existing four-field `default_plugin_evidence`. A browser request must never supply or override that evidence. Execute each Admin write with one original request ID and recover an unknown final result by reading that operation's receipt once; never retry the mutation. Refactor `services/deck/defaults.py` so it has no database import or helper call and only owns local artifact/CLI verification, or remove dead wrappers after proving no call sites remain.

Make both public routes async and route them through the shared Admin request-auth/client boundary. Preserve current request fields, nullable mapping, successful response shapes, 409 default-plugin-unavailable feedback, ownership, ordering, default-deck actor lock, missing-ref repair and refs-preserved behavior. Admin remains the sole SQL/transaction authority; Dream retains shared filesystem and CLI access. Admin unavailable, capability mismatch, malformed candidate, missing artifact, CLI incompatibility, candidate race and unknown write outcome must fail closed without Dream PostgreSQL fallback.

Add Admin DTO/service/repository/registration and restricted-role integration coverage for exact configured candidate, absent/unready/mismatched candidate, duplicate historical ordering, wrong scope/entity grant and closed input. Add Dream provider-free route tests that force `database.get_db`, `database.create_deck`, `database.auto_fork_system_decks` and `database.reconcile_default_screenplay_deck_plugin_ref` to raise while create/reconcile still pass through fake Admin; cover local artifact and CLI failures, browser evidence rejection, capability failure, create/reconcile unknown receipt recovery and response compatibility. Update headers, `.folder.md`, architecture/operation maps and closure evidence. Run focused Vitest/pytest, restricted-role integration, typecheck/compile/lint, AST closure scan and `git diff --check`. Commit Admin first, freeze commit/tree and exact operation hashes, then commit Dream against those immutable values. Do not push, modify the normal PostgreSQL database or touch existing Plugin work.

USER REQUIREMENT:
将 Dream 全部生产数据库访问迁入 Admin，数据库接口严格遵从 DTO / ORM 设计；保留 Dream Runtime、产品交互和共享文件系统校验。

## 项目、责任与依赖

| 项目/责任人 | 责任 | 依赖 |
| --- | --- | --- |
| Admin 任务 | `deck.default-plugin.resolve` strict DTO、Service、typed Repository、Handler/Registry 与隔离合同 | 图片历史 Registry103 先独立提交；复用现有 unified/deck schema capability |
| Dream 任务 | 候选 DTO、local artifact/CLI verifier、create/reconcile consumer、两条公开路由替换 | Admin 新 read hash 与已有 write hashes冻结 |
| Root | 源行为核对、候选竞态/回执验证、AST 关闭证据 | 两侧提交和具名隔离目标 |

## 正常流程与状态转换

1. Dream 从当前 OAuth 请求取得 actor，不读取或接受浏览器 evidence。
2. Admin 根据服务端 policy 查询 ready 的默认插件安装；无匹配返回 null。
3. Dream 本机验证 artifact digest 与 CLI 兼容；失败映射现有 409，不执行写入。
4. Dream 调用 `deck.create` 或 `deck.reconcile-default`；Admin 在同一事务再次验证安装、owner 和默认策略，再创建 Deck/ref 或返回默认 Deck 当前状态。
5. 写响应丢失时 Dream 读取原 operation/request receipt；committed 恢复原 ID/结果，其他状态保持未知。

## 验收与风险

- `voices.py` 与 `services/deck/defaults.py` 对这两个流程零 Dream database import、零 legacy helper；运行时 fence 抛错时公开路由仍通过 Admin fake。
- Wire 输入不含 actor、配置、候选 evidence 或物理选择器；Admin DTO → Service → typed Drizzle Repository → UOW 清晰可检验。
- 读写竞态、foreign actor、缺失/非 ready/篡改 digest 均不产生 Deck 或 ref；重复 request ID 只产生一次效果。
- 共享 artifact store、CLI 版本解析和用户可见产品路径保持 Dream 所有；Agent Runtime、SSE、EventBus、线程 workspace 不受影响。
- 风险是 Admin policy 与 Dream 展示配置暂时并存。Admin policy决定真实选择与写入；Dream配置只允许用于既有错误文案，不能参与数据库选择。后续配置收敛需单独变更产品文案与部署契约。
