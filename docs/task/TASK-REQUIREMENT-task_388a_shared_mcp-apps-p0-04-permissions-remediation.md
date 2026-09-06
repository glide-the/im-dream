<!-- [输入] task_388a、DEC-002 和当前 task_411-03。 -->
<!-- [输出] P0-04 当前候选的权限与隔离验收摘要。 -->
<!-- [定位] 历史 requirement；当前实施以 task_411-03 为准。 -->
<!-- [同步] 2026-09-06：按真实 Browser 安全证据重建要求。 -->

# TASK-REQUIREMENT：P0-04 当前候选

在当前 pnpm lock 和本机兼容 Chrome 上验证：

1. requested/desired/effective/revision 与 server-owned policy snapshot 一致；
2. outer/inner iframe sandbox/allow 与 proxy CSP/`Permissions-Policy` 一致；
3. 允许的权限正向成功，未允许权限、非法来源和非法 message schema 被拒绝；
4. adapter→bridge→transport→iframe teardown 顺序可观察；
5. refresh/reconnect/close 不重放首次工具调用；
6. trace 不含 HTML 正文、credential、headers、env 或用户内容；
7. Browser/runner 无法启动时记录运行前置缺失，不判断页面/API 失败；
8. 所有结果保持 `production_apps_effective=false`。

详细路径、命令和 P0-08 汇总见 [task_411-03](./task_411-03_shared_pnpm-standalone-phase0-gate.md)。
