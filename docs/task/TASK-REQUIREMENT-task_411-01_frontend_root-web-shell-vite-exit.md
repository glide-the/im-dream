<!-- [输入] task_411-01、DEC-005 和现有 frontend 行为。 -->
<!-- [输出] N1-01—N1-05/N1-RB 的直接实施和验证要求。 -->
<!-- [定位] 根 Web Shell requirement；包含技术依赖、范围、验收和回滚。 -->
<!-- [同步] 2026-09-06：改用技术边界、当前工作树和可观察证据。 -->

# TASK-REQUIREMENT：根 Web Shell 与 Vite 退出

1. 记录当前工作树，保护用户和并发任务的现有改动。
2. 将 `frontend/` 建为唯一 workspace/Web/Next root，`frontend/app/**` 建为唯一 App Router。
3. 以 client-only compatibility shell 复用现有 SPA，避免 SSR 访问浏览器对象。
4. 迁移 route-level view 时先复用现有模块，不复制 router、状态或 transport。
5. 保持 auth、OAuth、Python API、Agent SSE、cancel/resume、voice、runtime config、动态资源和普通 Chat 行为。
6. 退出 Vite 默认生产入口和嵌套 Next；不创建 Runtime package 或修改最终 pnpm lock。
7. 运行 N1-01—N1-05/N1-RB 的 root 命令、focused tests 和本机 Chrome journey。
8. 同步直接受影响的文件头、`.folder.md`、Docker/启动说明和双语 README。
9. 记录命令、退出码、关键输出、未运行原因、image digest、差异和清理。
10. 回滚只使用已验证 Vite image，不恢复嵌套 Next 或 legacy Runtime。
