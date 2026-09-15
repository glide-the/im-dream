<!-- [Input] Current Admin-authenticated Dream Product routes, Product API JWT contract and legacy Dream PostgreSQL identity lookup. -->
<!-- [Output] Executable plan and receipt for removing Product BFF database access while retaining Admin Product authority. -->
<!-- [Pos] Cross-project database-access closure stage; Product policy and persistence remain in Admin. -->
<!-- [Sync] 2026-09-16: plan the Product BFF PostgreSQL closure before implementation. -->

# Product BFF 数据边界收敛

## Optimized Prompt

You are an Expert Prompt Architect and senior Python, Next.js, authentication,
DTO and PostgreSQL engineer. Refactor the Dream Product BFF so it never opens
PostgreSQL. Verified evidence shows every public Product route already uses
Dream's shared Admin OAuth dependency, which validates an active canonical
principal and rejects missing scopes. The existing `ProductBffService` then
performs a second `users` lookup through `PostgresCanonicalUserRepository`
before issuing a short-lived, subject-bound Product JWT. Admin Product verifies
that JWT, resolves the same canonical subject through its authoritative data
repository and checks the active platform projection before any plan,
subscription, usage, model or payment operation.

Remove the redundant Dream PostgreSQL pool, identity Repository and runtime
cleanup. Keep strict subject syntax validation in Dream, but derive the subject
only from the already authenticated Admin principal; continue to reject all
identity override headers. Preserve the existing Pydantic request/response DTOs,
Product JWT issuer/audience/scope/TTL, one upstream request per BFF request,
idempotency rules, origin checks, response field firewall and Admin-side
authoritative active-user validation. Missing Admin Product configuration or an
inactive/missing subject must fail closed through the existing safe error
mapping. Do not add a generic data API, caller-supplied user selector, local
cache, retry or database fallback.

Update file headers, the `admin_product` folder contract, Product architecture
text and the production database migration inventory. Replace Repository tests
with source/runtime tests proving the Product composition imports no PostgreSQL,
passes only the authenticated decimal subject into the Product client and
preserves mismatched Admin response rejection. Run focused Product client/BFF
route tests, syntax compilation, source-only closure scan, Markdown reference
validation and `git diff --check`. Preserve unrelated dirty files.

USER REQUIREMENT:

继续完成 Admin 统一认证与数据库访问服务；数据库改造成接口遵从 DTO/ORM，
Dream 生产运行路径不得保留 PostgreSQL 访问或 fallback。

## 目标、依赖与边界

| 项目 | 当前证据 | 本阶段责任 | 保持不变 |
|---|---|---|---|
| Dream | `routers.deps.get_current_user` 已通过 Admin `/principal` 和 strict DTO 校验 current actor | 删除 Product BFF 的 PG pool/Repository；只把该 actor 的 canonical ID交给现有 Product client | 路由、Pydantic DTO、origin、幂等、错误和响应字段防火墙 |
| Admin | `app/lib/product/auth.ts` 在 Product JWT 后再次查询并验证 active canonical/platform identity | 继续拥有 Product ORM/持久化、订阅与支付事务；本阶段无需新 schema 或 migration | Product JWT 合同与所有业务策略 |

Dream 修改 `backend/services/admin_product/{runtime,service,__init__,.folder}.py`
与相关测试；若 `identity.py` 已无调用者则删除该生产数据库模块。Admin 本阶段
只读核验既有 Product 权限链，不制造重复接口。验收要求 Product 相关测试通过、
source fence 无 `PostgresPool`/persistence import/SQL，新的全仓 AST 回执如实保留
其他未关闭模块。真实支付、真实账户和浏览器验收仍与确定性技术验证分开记录。

## 实施与验收回执

- Dream 删除 `backend/services/admin_product/identity.py`，`runtime.py` 不再创建
  `PostgresPool`；`ProductBffService` 只校验 Admin principal 中 canonical ID 的
  PostgreSQL bigint 文本边界，再交给既有 Product client。
- `backend/routers/product.py` 修正旧同步认证调用，复用异步
  `get_admin_current_user` 与同一个 `AdminRequestAuth` owner。缺少 bearer、Admin
  配置或 principal 校验失败仍映射为 `PRODUCT_AUTH_REQUIRED`，请求头和 DTO
  不能覆盖用户主体。
- `PYTHONPATH=backend /Users/dmeck/project/ink-dream-memory/.venv/bin/python -m pytest -q backend/tests/test_admin_product_client.py backend/tests/test_product_bff_routes.py`
  实际 `exit 0`，`21 passed`；包含严格 DTO、origin、幂等、错误字段防火墙、
  canonical subject 绑定、Admin 响应主体不一致 fail closed 与 composition source
  fence。
- `python -m py_compile` 对 Product router、service、runtime、测试实际 `exit 0`。
- dirty-safe AST 扫描实际 `exit 0`、`parse_errors=[]`；Product 目录在数据库访问
  entries 中为 `[]`。全仓仍有 78 个生产候选、44 个 SQL 模块与 17 个 driver/
  database import 模块，详见
  `../exec/admin-auth-data-verification/dream-db-closure-after-product-bff-source-only.json`，
  因而本回执只声明 Product BFF 数据边界关闭。
