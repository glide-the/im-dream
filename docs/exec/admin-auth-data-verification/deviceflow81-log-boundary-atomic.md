<!-- [Input] Better Auth 1.7.4 source, Admin auth error boundary and primary-owned DeviceFlow81 isolated PostgreSQL harness. -->
<!-- [Output] Sanitized deterministic and atomic rollback/unknown-commit validation receipt. -->
<!-- [Pos] Technical evidence for the Device Flow log-disclosure remediation; excludes normal business acceptance. -->
<!-- [Sync] 2026-09-15: record zero-log 503 rollback and actual final-COMMIT recovery evidence. -->

# Device Flow81 日志边界与原子恢复回执

## 发现与修复

首次 `identity."deviceCode"` 写入故障触发 Better Call 的默认 `console.error`，Drizzle 异常对象包含 SQL 参数以及动态 `device_code`、`user_code`。执行器立即停止其余故障步骤，原始输出仅按 `0600` 私有证据保留；公开回执不包含动态值。

已安装 Better Auth 1.7.4 的 `onAPIError.throw` 会在默认 logger 处理前重抛未知插件/ORM异常，Better Call 随后跳过其 `console.error`。Admin `createAdminAuth` 已开启该配置；外层 `handleAuthRequest` 保持事务回滚，并返回 `Cache-Control: no-store` 的 `503 {"error":"temporarily_unavailable"}`。

## 确定性验证

工作目录均为 `/Users/dmeck/.codex/worktrees/729f/ink-admin-memory`。

| 命令 | 退出码 | 结果 |
| --- | ---: | --- |
| `node /Users/dmeck/.cache/node/corepack/v1/pnpm/9.15.0/bin/pnpm.cjs exec vitest run app/lib/auth/server.test.ts --configLoader runner --cache false` | 0 | 1 file，2/2；覆盖配置重抛、rollback、零 `console.error`、通用 503 body 与 no-store。 |
| `node /Users/dmeck/.cache/node/corepack/v1/pnpm/9.15.0/bin/pnpm.cjs exec tsc --noEmit --incremental false` | 0 | 无类型错误。 |
| `node /Users/dmeck/.cache/node/corepack/v1/pnpm/9.15.0/bin/pnpm.cjs exec eslint app/lib/auth/server.ts app/lib/auth/server.test.ts` | 0 | 无 lint 错误。 |
| `git diff --check` | 0 | 无 whitespace error。 |

主任务对隔离故障脚本先尝试 `esbuild` syntax-only；当前依赖未安装 `esbuild`，该 harness 检查退出 1，未执行脚本、未访问数据库。随后使用已安装 TypeScript 的 `transpileModule` 做 syntax-only 转换，退出 0，输出 `TypeScript syntax transform PASS`。

## 具名隔离 PostgreSQL 验证

```text
cwd: /Users/dmeck/.codex/worktrees/729f/ink-admin-memory
command: python3 /private/tmp/ink-auth-migration-validation/run-deviceflow81-atomic-recovery-after-log-boundary.py
exit: 0
target: ink_auth_data_codex_test_792494523a17_deviceflow81, port 51534
```

实际结果为 1,429 项断言通过：

- `deviceCode` INSERT、approve UPDATE、refresh-token INSERT 三个选择性故障均返回 no-store 503 `temporarily_unavailable`，125 个关系逐字节回滚；每个自有 trigger/function 均已清理。
- 产品处理期间 `console.error` 调用数为 0；child stdout/stderr 不进入公开回执，动态 code、token、Session、密码、DSN 与私钥均未导出。
- refresh-token INSERT 故障后的原 device code 可安全重试，重试返回 200 且只产生一组 token。
- 实际最终 `COMMIT` 完成后注入响应丢失：首次结果为 503，数据库保留一次消费和一个 refresh grant；原 device code 重试返回 400 `invalid_grant`，没有第二次持久化。客户端恢复规则为重新启动 Device Flow，因为 token endpoint 不保存原响应回执。
- 正常 5433 数据库、Google、真实用户、模型、Dream Runtime 和共享文件系统均未执行。本回执是隔离技术验证，不能代替真实业务验收。

原始安全 proof 和命令回执保留在 `/private/tmp/ink-auth-migration-validation/deviceflow81-atomic-recovery-after-log-boundary-*.json`；其导出结构只含汇总字段。首次泄露回执不归档、不发布。
