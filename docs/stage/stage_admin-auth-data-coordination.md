<!-- [Input] User cross-project authentication/data migration requirement, repository rules and published Git baselines. -->
<!-- [Output] Cross-project execution ownership, dependency gates, review and acceptance plan. -->
<!-- [Pos] Coordinator plan; project implementation contracts remain owned by the Admin and Dream tasks. -->
<!-- [Sync] 2026-09-14: establish verified baseline releases and actual implementation tasks before formal changes. -->

# Admin 认证与 Dream 数据访问迁移协调计划

## 背景与问题

Dream 现行认证文档与代码采用 Python/Authlib；Admin 基线依赖中没有 Better Auth。
共享 Drizzle 权威已经存在，但这没有移除 Dream 的 PostgreSQL 访问。
本轮目标要求 Admin 提供认证和全部数据库业务接口，Dream 保留产品交互、业务执行、Runtime 与共享文件系统操作。

基线中的 Admin `Agent.md`、`CLAUDE.md`、`docs/rules/README.md` 不存在。
已读取实际 `AGENTS.md`、根目录合同、README 与 Cursor rules；实现任务负责修复受影响的维护指针。
实际 Git 远程为 `glide-the/im-dream` 和 `glide-the/dream-im-platform`，发布使用这两个核验过的仓库。

## 目标与边界

- SQL、ORM、连接池、事务、数据权限与持久化移入 Admin；Dream 生产服务不持有 PostgreSQL 凭据，也不保留数据库访问后备路径。
- Admin Drizzle 保持唯一 schema 来源，API capability、schema capability 与部署版本分别定义。
- Runner、ThreadFactory、service、EventBus、SSE、turn/resume/cancel、admission 比较顺序、算法与既有 lease 保持原语义。
- 保留 resource-policy default/desired/effective/revision 与 LKG，后台 Admin API 失败不传播 Agent turn，turn 不新增远程策略读取。
- 保留共享文件系统、真实线程 workspace、`.claude-tmp` 的 `0700`、符号链接限制与 sandbox 精确路径。

## 概念与规则

认证主体、Dream 产品权限、Admin 管理权限、数据实体权限、服务身份与用户委托分别校验。
登录 Dream 不授予 Admin 管理权限；Google token、OIDC ID token 和外部任意用户 ID 不作为 Dream API 凭据。
数据库方案须比较同实例分库与同库 schema，依据现有跨域外键和事务选择，不能以改名声明完成。
Admin API 以领域操作保留原事务，非幂等写入不得盲目重试，未知提交结果必须通过原请求标识恢复。

## Optimized Prompt: 本轮协调与分析

You are the cross-project coordinator. Establish verifiable Admin and Dream baseline releases before any formal changes, create independent project tasks and goals, then review actual production database entry points and authentication ownership. Evidence: Dream baseline 7d38715c, Admin baseline 017f3acc; both remote refs and published prereleases verified. Owner: coordinator; implementation owners: Admin and Dream project tasks below. Read repository rules, affected folder contracts, manifests/locks, auth routes and clients, persistence pools/UoW, resource policy, filesystem modules, Drizzle schema and official Better Auth Google/Device/OAuth Provider/JWT documentation. Change only this coordination plan and its execution record in this branch. Admin owns the canonical API/schema/auth contract; Dream consumes it and closes the complete access inventory. No API/schema/config change is performed in this coordinator round. Preserve Runtime, streaming, leases, LKG and filesystem semantics. Track normal and failed authentication/data calls, expired/revoked credentials, denied scopes, unavailable Admin, missing capabilities and unknown write results. Acceptance requires actual files and command receipts for every stage, full production-entry review plus runtime evidence, deterministic validation by Luna, and separately identified real-user/Google/model acceptance. Risks: incompatible package APIs, cross-domain FK/transactions, missing secrets/account selection, dependency gates and task worktree drift. Do not claim completion while downstream work remains.

USER REQUIREMENT:
Execute the complete cross-project authentication and database-access migration with immutable baseline releases, actual tasks/goals, reviewed contracts, implementation and full business validation.

## 发布基线与任务

| 项目 | 基线 commit | 基线 tag | 实现分支 | 实际任务 ID / worktree |
| --- | --- | --- | --- | --- |
| Admin | `017f3acccc57991f0b3771c1c9bb9dd765255b07` | `v0.1.0-pre-admin-auth-data.20260914` | `codex/admin-auth-data-provider` | `01a0a03d-f058-7130-bfa9-71d2bb0bc1c9` / `/Users/dmeck/.codex/worktrees/729f/ink-admin-memory` |
| Dream | `7d38715c1a8f74cb5fb3dcb114320156eaf6b3e6` | `v0.1.3-pre-admin-auth-data.20260914` | `codex/dream-admin-auth-data-client` | `01a0a03e-02f7-7221-9118-8bf3f6a91cb3` / `/Users/dmeck/.codex/worktrees/ef6e/ink-dream-memory` |

发布回执见 [协调执行记录](../exec/exec_admin-auth-data-coordination.md)。
协调任务 `01a0a039-5eff-7ac1-90bd-2198f14766e7` 已通过真实 `create_goal` 设置目标，保持 active。
两个实施任务已分别报告实际 goal active；最终仍以实现、文档与验证回执决定完成状态。
未跟踪的 `repomix-output.xml` 未暂存、未提交、未进入基线。

## 依赖与阶段状态

| 阶段 | 责任 | 依赖 | 当前证据 / gate |
| --- | --- | --- | --- |
| 基线发布 | 协调 | 规则与远端核验 | 两个 tag 推送、Release 发布、远端 peeled SHA 核验成功 |
| 现状扫描 | 两个项目 | 基线发布 | 执行中，不能以初步关键词清单替代完整入口分析 |
| 规范契约与数据库决策 | Admin，Dream 反馈 | 完整扫描 | 等待实际文件与评审 |
| 架构/交互设计评审 | 两项目，协调 | 规范契约 | 待执行 |
| Admin schema/auth/data | Admin | 设计通过 | 待实际实现与发布 capability 证明 |
| Dream 客户端及入口替换 | Dream | 已核验 Admin 契约 | 可并行扫描，依赖就绪后实现 |
| 技术验证 | Luna runner，主任务修复 | 相应实现 | 待执行；迁移/破坏/真实用户由主任务处理 |
| 完整真实验收 | 协调与项目主任务 | 正常本机服务、指定账户与已有实体/模型 | 用户授权现有账户 `dmeck@suoxya.com`，可通过公开入口选择已有实体与正常模型；Dream 当前入口未启动 |

## 冲突登记

| 旧规则或说明 | 最新目标 | 调整范围与负责人 |
| --- | --- | --- |
| Dream auth.md 采用 Python/Authlib Token Authority | Admin Better Auth 为唯一应用认证中心 | Dream 保存历史原文、更新现行认证和兼容退役方案；Admin 实现主体映射与会话 |
| Admin database-schema-authority.md 保留 Dream repository/事务写入 | Dream 不执行任何生产 SQL/ORM/事务 | Admin 修订现行 schema/数据访问合同，Dream 将 repository 执行迁为领域 API |
| Admin Cursor rules 仍称 app/lib/db/schema.ts 是 schema 来源 | 实际 packages/db/src/schema/** 为唯一来源 | Admin 修正规则指针，保持历史 Drizzle 永久不变 |
| Admin 当前唯一 UI 是 /admin | 需要 Admin 登录与 Device 授权页面 | Admin 仅新增认证授权产品页面，管理 RBAC 不降低 |
| Dream root/folder 文档保留 Python 身份/数据所有权 | Dream 只校验 Admin 凭据并调用数据接口 | Dream 更新当前目录合同、README 和架构，保留业务执行所有权 |

## 评审与验收要求

设计评审逐项核验：唯一认证中心、数据归属、完整数据库入口、原事务和权限、共享文件系统、Runtime/SSE/LKG 保留、无额外控制通道、文档/DTO/图一致。
测试前项目任务必须写流程影响表，包含成功与失败恢复路径。
技术验证必须返回 cwd、命令、退出码、关键输出与适用范围；隔离 fixture 不充当真实 Google 或真实模型验收。
最终关闭入口清单须同时具备代码复查和运行公开生产入口的无数据库访问证据。
只在下游实现、文档、必需验证全部完成后标记协调 goal complete。

首版规范契约位于 Admin worktree 的 `docs/architecture/admin-dream-auth-data-contract.md`，状态为设计，尚无发布 API capability。
协调评审要求补齐：长 Agent turn 的主体委托/续期、后台与工具范围、跨客户端 browser handle 绑定、设备/refresh 并发原子性、未知提交恢复、Gateway 主体签发归属，以及真实 schema/ACL 验证。
用户凭据不进入任务消息、版本库、公开日志或回执。

## 发布与回滚条件

执行顺序为 Admin expand/schema/API → Dream 兼容接口 → backfill/validate → contract。
本计划不授权修改正常本机数据库 schema，也不重启用户已有服务。
隔离 migration 必须先核验具名目标身份；应用回滚使用已审查制品，schema 问题新增前向 migration。
基线 Release 只记录源码，不证明新方案已实现或可在旧 schema 上运行。
