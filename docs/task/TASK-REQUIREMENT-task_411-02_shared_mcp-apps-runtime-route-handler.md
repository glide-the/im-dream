<!-- [输入] task_411-02、411-01 current root、DEC-002/004/005 和官方离线 artifact。 -->
<!-- [输出] R2-graph—R2-gate 的直接实施、验证和回滚要求。 -->
<!-- [定位] Phase 1 Runtime/Host requirement；只包含技术依赖、范围、验收和回滚。 -->
<!-- [同步] 2026-09-06：按源码闭集、技术依赖、当前证据和 run-owned 资源重建。 -->

# TASK-REQUIREMENT：Runtime、Route Handler 与只读 Host

1. 记录工作树并协调目标文件；保留现有生成物和并发改动。
2. 只在 `frontend/packages/mcp-apps-runtime/**` 建立 Node Runtime；公开入口显式 server-only，composition root 持有进程级 manager。
3. 根 `frontend/app/api/mcp-apps/**` 只解析同源请求和身份上下文，再薄委派 Runtime。
4. Python 在解密前校验服务身份、actor、workspace、Server、revision、expiry 和 enabled，只返回单 Server 短时最小配置。
5. result identity 必须由受管 Server 注册信息产生，贯穿 live SSE、persisted part、Public DTO 和 refresh；不从 tool name、URI 或上游 result 猜测。
6. Browser 只连接 IM endpoint；Host adapter 持有 resource metadata、policy snapshot、双 iframe、sandbox/CSP 和 teardown。
7. 只使用未修改的官方 `server-basic-vanillajs@1.7.5` 离线 artifact。
8. Phase 1 不声明页面工具调用能力，Host/Node 对 `tools/call` 全拒绝且不上游。
9. 运行 R2-graph—R2-gate 的 focused Backend/Node/Browser/Next integration checks，记录命令、退出码、指纹和脱敏证据。
10. 不修改最终 pnpm lock、legacy Runtime、Phase 2/3、数据库 schema、Gateway 或普通 Agent/Chat 语义。
11. 只清理本轮具名 scratch/PID/port；production Apps 保持关闭。
