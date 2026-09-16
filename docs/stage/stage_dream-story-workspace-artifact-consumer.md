# Dream Story Workspace Artifact Admin 消费迁移

## Prompt Architect

Optimized Prompt:

在 `ink-dream-memory` 中使用 Admin Registry185–191 替换 Story Workspace 全部生产 PostgreSQL 访问。建立严格 Pydantic DTO 与统一 Admin client；浏览器路由使用当前 OAuth token，Agent turn 使用现有可续期的 exact Thread/Run persistence grant 和共享 unknown-write barrier。Dream 保留共享文件系统读取/写入、路径和符号链接防护、Episode registry、`.dream` 投影、Agent Runtime、EventBus、SSE、turn/resume/cancel、资源策略 LKG。Dream 只向 Admin 发送规范化 Artifact 业务投影，不发送用户 ID、SQL、表列、数据库或文件路径。完成后删除 Story Workspace SQL Repository、生命周期 SQL Service、re-entry SQL 和生产数据库启动依赖；Admin 不可用时 fail closed，不允许数据库回退。

验收必须覆盖 Dream files、Episode index/artifacts、Run re-entry、自动修复 scope、Episode authority 创建与重放、output-ready、Story Index inspect/materialize/reconcile、ETag 冲突、Admin 超时和未知写结果。代码清单与运行时配置共同证明 Dream 生产路径不再持有或打开 PostgreSQL。

Optional Enhancers:

- 对共享文件修改与 Admin index 提交之间注入失败，验证可由相同投影安全恢复。
- 使用真实本机服务执行一个保留记录的 Dream Run，并在日常 Admin 后台核对 Run、Thread、request 与 Story 索引。

## 背景与问题

Story Workspace 是 Dream 当前最后一组业务 SQL。直接调用集中在 `story_workflow_application.py`、`dream_artifact_turn_hook.py`、re-entry、Story Index Repository/reconcile 和旧 lifecycle service。

## 目标与边界

Admin 契约以 [Admin 现行设计](https://github.com/glide-the/dream-im-platform/blob/codex/admin-auth-data-provider/docs/stage/stage_admin-story-workspace-artifact-domain.md) 为唯一数据库契约。Dream 负责本地文件投影与产品响应，并通过 Registry185–191 获取数据库 authority 和提交持久化。

保持不变：Runner、ThreadFactory、service、EventBus、SSE、turn/resume/cancel、资源 admission/lease、`CLAUDE_CODE_TMPDIR`、thread workspace、`0700`、符号链接和 sandbox 精确放行。

## 概念与规则

- 公共 API 的读写使用当前用户 OAuth；turn hook 使用已有 server-persistence grant。
- Run authority 响应先与 turn ticket 的 frozen context 逐项匹配，再允许任何文件变更。
- Episode authority 由 Admin 建立后，Dream 才更新本地 Episode registry。
- Dream 计算 Project title、Episode count、manifest/script revision 与大小；Admin 派生 owner、Workspace、Thread 和 Story ID。
- reconcile 保留两次文件读取：第一次形成 inspect ETag，第二次形成 fresh projection；文件变化或 Admin ETag 变化均返回 revision conflict。
- 未知写结果进入统一 pending barrier并用 receipt 恢复；不同写操作不能越过未决结果。

## 验收与风险

先运行新的 DTO、客户端、turn persistence 和 Story Workspace 单元/合同测试，再运行类型/编译、生产 SQL import/call 清单和 provider-free E2E。最后在本机正常 Dream/Admin/Gateway/PostgreSQL 上走公开入口；真实 Google/模型条件不足时分别标记，不能用隔离测试冒充。

## 实现结果

- `backend/services/admin_data/story_workspace_artifact_data.py` 定义 Registry185–191 的 strict Pydantic DTO、HTTP client 与 provider；所有输入拒绝额外字段。
- `request_auth.py` 与 `turn_persistence.py` 注册 Story Workspace operation/capability；浏览器调用使用当前 OAuth，turn hook 复用 exact Thread/Run persistence grant。
- `dream_artifact_turn_hook.py` 在文件访问前校验 Admin 返回的 Run、Thread、Deck、Workspace 与 frozen ticket；`dream_reentry_service.py` 只投影 Admin authority。
- `story_workflow_application.py` 保留文件读取、路径防护、Episode registry 与 `.dream` 投影；数据库 authority、状态和 Story index 均来自 Admin。
- 已删除旧 Story Index Repository/service/reconcile、Dream lifecycle SQL 和独立 Workflow Run SQL service，Admin 失败时没有 PostgreSQL fallback。

确定性回归覆盖 Story Workspace DTO/client、route、re-entry、turn hook、Claude Agent service 与生产 SQL 边界。Dream backend 全量结果为 3523 passed、24 skipped、615 subtests passed，退出 0；Runtime 0.1.9 独立 resume 合同 4/4 通过；认证 BFF Node 合同 35/35、TypeScript、lint（0 error）和 Next.js 16.1.6 生产构建通过。Admin 全量为 2067 passed、36 skipped，生产构建通过。依赖锁/导出内容、AutoDL topology、生产数据库静态边界和 Markdown 引用均通过。

上述结果属于技术验证和本机 provider-free Runtime 合同。真实 Google 登录、指定账户的完整 Dream Run、真实模型调用及日常 Admin 后台可见性尚未在本阶段执行，不能据此宣称整体业务验收完成。完整命令与工作目录见 [Story Workspace Artifact 最终技术回执](../exec/admin-auth-data-verification/story-workspace-artifact-final-validation.md)。
