<!-- [输入] task_411-03、411-01/02 当前候选和 Phase 0 harness。 -->
<!-- [输出] R3-lock—R3-production-off 的直接实施与验证要求。 -->
<!-- [定位] pnpm/standalone/P0 requirement；只包含技术依赖、范围、验收和回滚。 -->
<!-- [同步] 2026-09-06：改用唯一 lock、同一候选证据和精确回滚。 -->

# TASK-REQUIREMENT：pnpm、standalone 与 P0 重验

1. 核对 411-01/02 的 canonical tree、Runtime/Route graph、Host、result identity 和官方 artifact。
2. 创建或更新唯一 `frontend/pnpm-lock.yaml`，以 frozen install 证明依赖闭包；退役旧 npm lock。
3. 从 `frontend/` 无位置参数运行 dev/build/start，并验证 root standalone trace 收入 Runtime production dependencies。
4. 在同一源码、lock、Chrome、Browser 入口和官方制品上执行 P0-01、P0-04，并核对 P0-02/P0-03/P0-05/P0-06/P0-07。
5. 只原位更新唯一 P0-08 Go/No-Go；缺少当前证据时写 No-Go，不拼接历史证据。
6. 运行 auth/OAuth/SSE/cancel/resume/voice/runtime config/普通 Chat 回归。
7. 演练当前 Next image 与 Vite image 回滚，记录 digest、命令、smoke 和清理。
8. 记录 R3-lock—R3-production-off 每项命令、退出码、关键输出、指纹、未运行项和证据位置。
9. 不实施 Phase 2/3，不修改数据库 schema/Gateway/外部 Server 配置，不启用 production Apps。
