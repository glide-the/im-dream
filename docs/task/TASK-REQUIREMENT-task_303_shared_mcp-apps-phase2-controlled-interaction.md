<!-- [输入] task_303、Phase 1 当前证据与服务端低风险 allowlist。 -->
<!-- [输出] I2-01—I2-07 的直接执行要求。 -->
<!-- [定位] Phase 2 requirement；只包含技术依赖、范围、验收和回滚。 -->
<!-- [同步] 2026-09-06：以技术依赖、写入范围和 Browser/Node 证据重建。 -->

# TASK-REQUIREMENT：Phase 2 受控交互

1. 先核对 Phase 1 当前候选的同源 endpoint、Node 权限、Host sandbox、fallback 和 no-replay 证据。
2. 实现 I2-01—I2-07，不改变首次工具调用、Agent turn、Thread、SSE 或数据库语义。
3. 页面工具请求必须经 Host 和 Node 双重校验；未允许请求上游计数为零。
4. `ui/message` 只进入当前 Thread 的现有 Chat ingress。
5. `window.im` 只暴露真实实现的能力，不发明私有 transport。
6. 高风险写工具在服务端可验证、不可重放的独立授权合同存在前始终拒绝。
7. 运行 focused unit/integration/Chrome E2E，记录命令、退出码、当前源码/lock/Browser 指纹和脱敏 trace。
8. 回滚按 capability 独立关闭，保留 Phase 1 只读 App、ordinary fallback 和 `production_apps_effective=false`。
