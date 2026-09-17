<!-- [Input] Immutable Admin Registry101 commit plus task and root command receipts. -->
<!-- [Output] Local-data DTO/Service/typed Repository/UOW contract hashes and technical validation evidence. -->
<!-- [Pos] Admin provider technical receipt; Dream consumer and normal-account acceptance remain separate. -->
<!-- [Sync] 2026-09-15: freeze exact Registry101 Git and contract identities after restricted-role validation. -->

# Registry101 本地数据导入 Admin 验证

## Git 与契约

- commit: `c051a58e9193b0f39f2b211ac9ff5182fea87d73`
- tree: `49cd33a9cdf0f73c1faebecc01baccfca0af7a5b`
- parent Registry99: `16a3d9b2796254fa525a966ca851de96d4373445`
- subject: `feat: add atomic local data import operations`
- operations: 101；`local-data.import` hash `f2f13ac392be415b42bb9532d42e20bf04fef2400551cd2f528991f4f6de271d`；`first-login.complete` hash `f06bbfd87fd905139b40df61eccdda6726678adda304dcd141a0bf52cf874cb0`
- requirements: `identity.better-auth.v1` v1 / `1dc05e229d3f4147923fcdfe117c4c4930a43bf9f31439d7b4bc83d2a0d04cd3`；`dream.schema.unified.v1` v1 / `8b71cf5687f61dee884c3e6f2fb109c7a951b0789066a0f13583a7b67757fa71`
- Registry canonical SHA: `8964d7dea090d83bf2795b1b0e1c1fc23da293b80182428c7bec7ebc9ded8147`
- raw operation artifact SHA: `0f78063e2204ea835b16015bf50a45a40adfc5289520a6c548e1c63c28d652e6`
- raw implementation map SHA: `0bda942de0ad3d806d76c7890c9768cfdaa536371c8904b1bc2e1bd74b772260`
- `git diff-tree ... | rg ^drizzle/`: no output；本阶段没有 schema/migration 变化。

上述值由 Root 直接读取 Git commit object 后重新计算，与 Admin 任务回传一致。实现是 strict Zod DTO → Service → typed Drizzle Repository → shared Receipt/Audit UOW；wire 不接受主体或物理数据库选择器。

## Root 独立验证

所有命令 cwd 均为 `/Users/dmeck/.codex/worktrees/729f/ink-admin-memory`。

```text
pnpm exec vitest run app/lib/dream/localDataImport.test.ts app/lib/dream/localDataImportHandler.test.ts app/lib/dream/localDataImportReceipt.test.ts app/lib/dream/localDataImportRegistration.test.ts
```

exit0：4 files / 42 tests。覆盖 strict fields、actor/scope、四类别、0..4 preference count、foreign owner、receipt replay/concurrency/conflict、注册与 original receipt。

```text
INK_DREAM_SOURCE=/Users/dmeck/project/ink-dream-memory INK_DREAM_ORACLE_PYTHON=/Users/dmeck/project/ink-dream-memory/.venv/bin/python pnpm exec vitest run app/lib/dream/localDataImportSource.test.ts
```

exit0：1/1。实际 Dream 源 oracle 捕获旧聚合与 first-login SQL/commit/close；冻结经评审差异：禁止 owner 转移，规范化并保存报告时间。

```text
pnpm exec tsx tests/integration/adminLocalDataImport.contract.mts
```

exit0。runner-owned 随机 loopback PostgreSQL 使用受限 DATA role；same-owner upsert、foreign-owner 和注入故障全回滚、raw JSON/报告时间、重复/并发单效果、changed-input conflict、unknown commit 只读原 receipt、first-login receipt/audit insert/update/repeat 全通过；owned cluster removed。

```text
pnpm exec tsc --noEmit --incremental false
pnpm lint
```

两项 exit0。

Admin 任务另报告 full unit `1730 passed / 32 skipped`、88 focused、Markdown/JSON/diff gates exit0；该回执来自任务，Root 没有重复执行同一全量命令。

## 范围限制

以上为 provider-free 与自有隔离 PostgreSQL 技术验证。没有连接正常业务数据库，没有真实 Google/现有账户/浏览器/模型调用，也不证明 Dream 三个公开入口已经迁移；Dream 必须绑定上述 exact hashes 后另行验证。
