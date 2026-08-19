<!-- [Input] Workspace file router, edit session hooks, storage router, and sandbox configuration. -->
<!-- [Output] Current workspace-file, edit-sync, storage, and sandbox contract. -->
<!-- [Pos] Canonical workspace-storage module design. -->

# 工作区与存储

## 工作区文件

- `/api/workspace/files` 在认证用户的受控工作区内提供列表、读取/写入、重命名和删除。
- 下载入口支持单文件和所选目录/文件的 ZIP 输出；路径必须在 canonical 工作区根内解析。
- 写入、重命名和删除使用服务端规范化路径，拒绝越界、符号链接逃逸和未授权绝对路径。
- Agent 与编辑器共享文件事实；Agent 写回通过事件通知页面重新读取，不依赖固定等待时间。
- Workspace Mode 关闭时不创建隐式 Agent 文件访问；开启时使用服务端分配的 workspace descriptor。

## 对象存储

- `/api/storage` 返回当前存储能力，不暴露凭据。
- 上传支持服务端 multipart 或受控 Presigned URL；读取通过编码对象 Key 的代理入口完成。
- 存储驱动由服务端配置选择 S3/兼容 S3 或 Vercel Blob；浏览器不能选择任意 Endpoint。

## 沙箱边界

Claude Code 临时文件只允许位于规范化 `CLAUDE_CODE_TMPDIR`，工作区沙箱只放行同一真实根目录。
网络、命令和环境变量由服务端 allowlist/policy 决定，不能通过环境名称或用户设置降低权限。

## 代码所有权

- 前端文件面板：`frontend/src/components/dashboard/FileSidebar.tsx`
- 工作区 API：`backend/routers/workspace.py`
- 对象存储：`backend/routers/storage.py`、`backend/libs/file_storage/`
- 编辑同步：`frontend/src/hooks/useEditSessionEvents.ts`、`backend/routers/sessions.py`
- 沙箱：`backend/libs/claude_agent_kit/server/workspace.py`、`backend/libs/claude_agent_kit/server/sdk_env.py`、`backend/config.py`
