<!-- [Input] Immutable Admin Registry103 commit plus root and Admin task command receipts. -->
<!-- [Output] Picture-history DTO/Service/typed Repository hashes and restricted-role technical validation evidence. -->
<!-- [Pos] Admin provider receipt; Dream route consumer and normal-account picture acceptance remain separate. -->
<!-- [Sync] 2026-09-15: freeze exact Registry103 Git and read-contract identities. -->

# Registry103 当前用户图片历史 Admin 验证

## Git 与契约

- commit: `547e89896776627b43ecaab0a5ac848891f21a94`
- tree: `1eec30f84691d53a1cf35e04a4ccaf98c93c04f2`
- parent Registry101: `c051a58e9193b0f39f2b211ac9ff5182fea87d73`
- subject: `feat: add current-user picture history reads`
- operations: 103；`picture-history.list` hash `d03993f15860caadba56b6788a4c1b1d0fa086e949f1831b6e805a2eabee028d`；`picture-history.full` hash `e35e76d3425641660da361f2671f0004042a3600b2f3d4072386233c0d90efa3`
- requirements: `identity.better-auth.v1` v1 / `1dc05e229d3f4147923fcdfe117c4c4930a43bf9f31439d7b4bc83d2a0d04cd3`；`dream.schema.unified.v1` v1 / `8b71cf5687f61dee884c3e6f2fb109c7a951b0789066a0f13583a7b67757fa71`
- Registry101 prefix canonical SHA: `8964d7dea090d83bf2795b1b0e1c1fc23da293b80182428c7bec7ebc9ded8147`
- raw Registry103 artifact SHA: `adc1b16b705e8905a1447bf33dc3e2c62feab8f049ee032c7159f96bdd88965e`
- raw implementation map SHA: `aec6ba4a0692df7a63e9d9a948cf3ff1ffef71a6a40c76e30ef562aa234a8663`
- `git diff-tree ... | rg ^drizzle/`: no output；本阶段没有 schema/migration 变化。

Root 直接从 commit object 读取 DTO、registry 和生成 JSON，并用 `shasum -a 256` 重新计算 raw SHA；Admin worktree 提交后为 clean。实现是 strict Zod DTO → OAuth Service → typed Drizzle Repository → shared read UOW，wire 只接受日期范围、limit 或单一日期，不接受 actor/friend/SQL/表列选择器。

## Root 独立验证

所有命令 cwd 均为 `/Users/dmeck/.codex/worktrees/729f/ink-admin-memory`。

```text
pnpm exec vitest run app/lib/dream/pictureHistory.test.ts app/lib/dream/pictureHistoryHandler.test.ts app/lib/dream/pictureHistoryRegistration.test.ts app/lib/dream/pictureHistorySource.test.ts
```

exit0：4 files / 33 tests。覆盖真实日期、非负安全 limit、closed selector、OAuth scope/entity delegation、nullable prompt/time、损坏投影、只读无 receipt、Registry103 路由和实际 Dream source oracle。

```text
pnpm exec tsx tests/integration/adminPictureHistory.contract.mts
```

最终 exit0。runner-owned 随机 loopback PostgreSQL 使用只有 Picture/capability SELECT 的受限 DATA role；owner/other 隔离、无范围/start/end/both、limit0、thumbnail fallback、重复日期、full newest、nullable prompt/time、输入先于数据库拒绝、capability/scope/entity fail closed 与 owned cluster cleanup 全通过。初次沙箱 loopback EPERM 与第一次 `+08:00` fixture 表示断言失败均保留在 Admin verification log；修正测试表示后生产代码未放宽。

Admin 任务另报告 cache-free TypeScript、full ESLint、默认单元 `1762 passed / 34 skipped`、JSON/Markdown/link/diff gates exit0；Root 没有重复执行同一全量命令。

## 范围限制

这是 provider-free 与自有隔离 PostgreSQL 技术验证。没有连接正常业务数据库，没有真实 Google、指定账户、浏览器或模型调用。Dream 的三个公开图片入口必须绑定上述 exact hashes 并完成运行时 legacy helper fence 后，才能声明该入口关闭。
