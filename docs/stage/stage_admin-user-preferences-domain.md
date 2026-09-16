<!-- [Input] Original get_preferences/save_preferences, public consumer fields and explicit domain ownership. -->
<!-- [Output] Strict two-operation DTO/ORM implementation and original atomic merge verification. -->
<!-- [Pos] Coordinator-owned Admin domain; Dream product config remains consumed through its unified client. -->
<!-- [Sync] 2026-09-15: preserve five closed fields, raw config JSON, NULL merge and first-login/system isolation. -->

# 用户 Preferences 数据接口迁移

## 背景与问题

Dream `database.get_preferences/save_preferences` 仍直连 PostgreSQL。原保存操作通过一次 ON CONFLICT 合并五个字段，NULL 表示保留旧值；拆成读后写 HTTP 会丢失并发更新。已有 Preferences 是产品配置，不是查询任意用户或修改任意数据库字段的接口。

## 目标与边界

协调任务独立拥有 Admin `userPreferencesDto/Repository/Service` 和相应 unit/public harness；Admin 任务拥有薄 Handler、Registry、Receipt、共享文档和唯一 Drizzle schema；Dream 任务拥有消费者与公开路由。此前 Run5 公开检查窗口已结束，共享注册表由 Admin 任务继续维护。复用现有数据库表、actor、capability、UOW、receipt 和原始 JSON helper，不新增 schema 或第二套客户端。

## 概念与规则

- 只暴露 voice_configs、meta_prompt、state_config、selected_state、timezone 五个保存字段；外部 actor/user_id、first_login_completed、system_config 不进入写入 DTO。
- Admin 从已验证 OAuth 主体取得 canonical ID；用户级 Preferences 不允许 Thread/Run/Editor 委托访问。
- 配置对象以原始 JSON 文本跨接口传递，避免 JS Number 重编码 bigint/float；沿用现有配置结构，不增加业务限制或时区名单。NULL 保留、空字符串按原值写入。
- 单条 Drizzle INSERT ON CONFLICT COALESCE 完成首次并发插入和后续合并；receipt/audit 同 UOW，重放不更新时间，冲突不产生部分写入。原 first_login 和 server system_config 不受影响。
- 查询返回 nullable 严格投影、原 first_login 数值和精确 nullable 时间；Dream 解析 raw JSON 后保持原公开 `{}`/配置对象和 `{success:true}` 行为。Admin 不可用时明确失败，不回退到数据库。

## Optimized Prompt:

You own only Admin userPreferencesDto.ts, userPreferencesRepository.ts, userPreferencesService.ts and focused/public contract files. Admin task explicitly transferred these two original callables and retains Handler/Registry/Receipt/shared docs/schema ownership; Dream task consumes through its existing strict Pydantic client. Read repository/folder rules, baseline Dream database.get_preferences/save_preferences and preferences route/frontend config fields, actual user_preferences schema and existing raw JSON/actor/UOW/capability helpers. Implement two named closed operations user-preferences.get/save using strict Zod DTOs, verified canonical OAuth subject, typed Repository and Drizzle ORM. Reuse the existing schema and exact identity/unified capability; no new migration. Keep five allowed fields only, raw object JSON without JS numeric reserialization, original NULL COALESCE semantics, blank strings, last-write ordering and nullable timestamp/first-login projection. Never expose actor selectors, first_login or system_config writes or accept entity grants for a user-level operation. Whole merge, original request receipt and audit share the caller's UOW; same request replay cannot touch time, different input conflicts and failed requests roll back. Prove normal/absent/partial/concurrent first-login merge/precision/permission/strict-field/error/recovery through focused tests and a frozen public harness against a primary-prepared proven disposable database with restricted AUTH/DATA credentials. Luna runs deterministic/public non-destructive assertions; primary owns fixture/fault SQL only. Do not touch other agents' edits or public Run5 shared window. Update affected headers/folder docs/contracts and exact owned coordinator mirror, then hand registered hashes to Dream with actual command/cwd/exit evidence. No normal DB/account/model/Google/Runtime/FS action or completion claim while other production domains remain open.

USER REQUIREMENT:
数据库访问改造成接口要遵从 DTO/ORM 设计，保留 Preferences 配置与并发合并、权限和重放语义，提供可核验项目实现与回执。

## 验收与风险

验证命令由现有 pnpm/Vitest、tsc、ESLint 及公开 operation/receipt harness 运行；实际回执后记录命令/退出码/关键输出。风险：误将 NULL 改成清空、并发读后写丢失字段、JSON 大整数精度丢失、first_login/system_config 被外部覆盖、复用失效凭据或非本轮数据库。禁止这些回退和替代路径。

当前状态：两操作已实现，focused19、公开78及type/lint均通过；Dream消费与正常真实验收仍独立推进。


## 当前实现与准备证据

Admin4个独立DTO/Repository/Service/unit已写入，原单条ONCONFLICT COALESCE/rawJSON/5字段/firstlogin和serverconfig隔离保持。Luna19/19 focused、wholetsc及指定lint均退出0；公开2harness已写入且type/lint通过。主任务已在具名_workflow60验证ledger60/既有2actor/无先前Preferences，只插入1个firstlogin/server-config保护fixture，另一actor保持absent供公开并发首次insert；私有freshOAuth和实际Thread grant仅用于拒绝验证，未导出私钥或操作normal数据。[focused19](../exec/admin-auth-data-verification/user-preferences-focused19.md)、[fixture事实](../exec/admin-auth-data-verification/user-preferences-fixture-proof.json)。Admin已注册实际Registry60中的2新操作；后续公开2验证的78项结果见下方交付记录。


## 公开验证通过与消费交付

Admin实际Registry60：user-preferences.get hash `757b12445ab664d26be82ade16e791d4331de348a4854403ff3c5a77f5b98d70`，save hash `0e0dbd5bdd90404b44fe10fe65e1b67ebdea2a55496751e45140e5166c0bca56`；仅identity+unified0033，不增加DDL。Luna `python3 /private/tmp/ink-auth-migration-validation/run-user-preferences-contract.py` cwdAdmin729f退出0，2ops/78断言通过：原五字段/NULL/blank/rawprecision、owned/current主体和strict字段、readscope与idg403、invalid部分失败rollback、并发首次insert不丢字段、原request同结果/不touch/不同input409、firstlogin/systemconfig保持、receipt/audit单次和owned恢复。见[78原回执](../exec/admin-auth-data-verification/user-preferences-public78.md)。

Dream任务已收到两个实际hash、DTO/NULL/对象还原和公开响应保持合同；尚未据此声明Dream路由与全部生产SQL已关闭。provider-free技术验收通过，正常本机Google/现有账户实体/模型与其他域仍未完成。
