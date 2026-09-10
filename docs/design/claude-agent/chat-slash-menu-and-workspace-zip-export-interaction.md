# Chat 斜杠快捷菜单与工作区 ZIP 导出交互设计稿（2026-09-11）

> [Pos] Claude Agent Chat 交互修复设计文档；承接 Codex 线程
> `01a0845d-6d1f-7313-bc03-14cd3f24c405` 两项问题的继承评审、修复与回归合同。
> 配套协议：`workspace-uri-preview-protocol.md`（workspace:// 预览与下载合同）。

## 一、背景与问题

### 问题一：Next.js 迁移后聊天输入 `/` 没有快捷菜单

斜杠菜单链路的实现文件（`AIInputDock.tsx`、`MarkdownInputEditor.tsx`、
`slashSkillCommands.ts`、后端 `GET /api/claude-agent/skill-commands`、Next
Route Handler 代理）全部存在，且组件本体自 Vite 时代迁移以来只有 import 路径
变化。继承评审定位到两个真实缺口：

1. **菜单触发的真因**：Tiptap Markdown 序列化器（`getMarkdown()`）为块级内容
   附加尾部换行，独立输入的 `/` 实际以 `"/\n\n"` 进入
   `filterInstalledSkillCommands`，被 `SLASH_DRAFT = /^\/[^\s]*$/` 拒绝，
   菜单在任何部署形态下都不会弹出（父任务的 SSR 诊断方向不成立：安装的
   @tiptap/react v3 已自动检测 Next 并延迟创建编辑器）。此前父任务的序列化
   断言因 Playwright `toHaveText` 的空白规整成为假阳性。
2. **验证缺口**：父任务提交的回归测试
   `MarkdownInputEditorSlashRegression.test.ts` 两个用例均失败——
   用例 1 的 harness 把编辑器元素作为 `props` 传给 `React.createElement('main', …)`，
   编辑器从未渲染（既有 `MarkdownInputEditor.test.ts` 基线通过，证明是 harness
   缺陷）；用例 2 断言 `immediatelyRender: false` 但该配置从未落入源码。
   `frontend/test-results/.last-run.json`（git 跟踪的 Playwright 产物）以
   `status: "failed"` 随提交入库，与"验证未提供通过回执"的用户观察一致。
   目录加载 → 菜单渲染 → 键盘选择链路此前没有任何测试覆盖。

### 问题二：Agent 因 shell `zip` 被拦截而拒绝提供真实 ZIP

`.dream` 运行面写保护（PreToolUse guard）拒绝 shell 压缩命令是**正确行为**，
不应放宽。父任务已建立"目录链接下载 = 后端即时打包真实二进制 ZIP"的方案：
Agent 把用户要求的文件放入 `files/` 独立目录后返回
`[Download ZIP](workspace://files/<目录>)`，聊天显式下载改走
`GET /api/workspace/files/download`。继承评审发现三个缺口：

1. **测试回归被破坏**：`WorkspaceUriPreview.test.ts` 的显式下载（`report.pdf`）
   仍只 mock 了 content 端点，父任务切换端点后该测试失败（下载事件不再触发），
   与 `.last-run.json: failed` 互相印证。
2. **下载端点防护弱于 content 端点**：`GET /api/workspace/files/download`
   此前只有 sessionId 格式校验 + `get_or_create_workspace`，缺少
   Thread 所有权校验、Workspace Mode 校验、严格公共路径校验和"不创建工作区"
   语义；聊天显式下载流量迁到该端点后，`.dream/`、`.claude/` 等非公共路径
   理论上可被下载，存在越权读取面。文件分支的常规文件读取也未拒绝符号链接。
3. **前端目录 ZIP 行为没有回归覆盖**：`workspaceFileAccess.ts` 的 download
   参数、`WorkspaceFileReference.tsx` 的 `.zip` 后缀逻辑均无测试。

## 二、目标与边界

### 目标

1. 斜杠快捷菜单：修复触发真因——在 slash 匹配前剥离 Markdown 序列化器的尾部
   换行伪影（保留选择后 `/cmd ` 的有意尾空格语义）；显式声明
   `immediatelyRender: false`；修复父任务 harness 缺陷，并以真实浏览器测试证明
   "目录加载 → 聚焦 → 输入 `/` → 菜单渲染 → 键盘选择/发送 → Escape 收起 →
   目录失败静默降级"全链路可用。
2. ZIP 导出：聊天显式下载继续走 download 端点（目录 → 后端即时打包真实
   ZIP；普通文件 → attachment 下载），图片预览保持 content 端点；补齐
   前端端点分流与文件名回归。
3. 权限与路径保护：把 download 端点防护对齐 content 端点合同（所有权、
   Workspace Mode、公共路径、不创建、符号链接拒绝），`.dream` shell 写保护
   保持不变。
4. 清理父任务遗留：恢复被误提交的 `.last-run.json`；不留本轮测试产物脏状态。

### 边界（明确不做）

1. 不新增第二套斜杠菜单实现、不引入新端点、新状态机、新配置项或环境开关。
2. 不放宽 `.dream` PreToolUse 写保护，不新增任何 shell 控制通道。
3. 不在本轮重构 workspace 路由 list/upload/delete/mkdir 等其他端点的所有权
   校验（系统性加固另行立项，见"剩余限制"）。
4. 不把 ZIP 链接表述为磁盘上已生成的 ZIP，不用拼接 Markdown 冒充多文件；
   Agent 引导文案维持父任务口径。
5. 不执行真实模型/真实业务验收；本轮全部验证为 provider-free 技术合同测试。

## 三、概念与规则

### 概念

| 概念 | 定义 |
|------|------|
| 斜杠草稿 | 匹配 `/^\//[^\s]*$/` 的输入框 Markdown 值，是快捷菜单的唯一触发态 |
| Skill 目录 | 后端 `GET /api/claude-agent/skill-commands` 返回的 common Skill 目录（`/{name}`），经 Next Route Handler 同源代理 |
| 显式下载 | 用户点击 `workspace://files/...` 链接（`WorkspaceFileLink`）触发的下载动作 |
| 图片预览 | `workspace://files/*.png|jpg|webp` 的缩略图/大图渲染（`WorkspaceImage`） |
| 目录 ZIP 导出 | download 端点对已存在目录即时打包的二进制 ZIP，顶层条目保留所选目录名 |
| 公共路径 | 以 `files/`、`logs/`、`skills/`（`WORKSPACE_SUBDIRS`）为首段的工作区相对路径 |

### 规则

1. **端点分流**：图片预览（含缩略图、大图、长图导出）只走
   `GET /api/workspace/files/content`；显式下载（普通文件与目录）只走
   `GET /api/workspace/files/download`。
2. **下载端点防护链**（与 content 端点同序）：
   认证 → sessionId 格式校验 → Thread 所有权（`_require_owned_workspace_thread`，
   非本人 Thread 一律 404）→ Workspace Mode（关闭时 409 `WORKSPACE_DISABLED`）
   → 严格公共路径校验（拒绝 `%` 转义、控制字符、反斜杠、`?`/`#`、`..`、
   绝对路径，首段必须属于 `WORKSPACE_SUBDIRS`）→ 不创建工作区
   （`get_existing_workspace`，缺失即 404 `WORKSPACE_NOT_FOUND`）→
   常规文件分支拒绝符号链接；目录分支不跟随目录符号链接且逐条目
   resolve 校验不逃逸工作区根。
3. **Tiptap SSR 与序列化**：`MarkdownInputEditor` 显式声明 `immediatelyRender: false`，
   使编辑器只在客户端挂载后创建，与 Tiptap v3 的 Next 自动默认一致，
   不依赖 `window.next` 探测的未来行为。斜杠匹配只剥离 `getMarkdown()` 的
   尾部换行伪影（`/\n+$`），不改动编辑器 onChange 载荷——避免 value 回写触发
   `setContent` 重写文档导致光标跳动；选择命令后的尾空格保持关菜单语义。
4. **失败语义**：Skill 目录加载失败静默降级为空菜单（不阻塞输入）；下载
   失败展示既有 `chat.workspaceFile.*` 失败态；均不新增错误路径。
5. **ZIP 命名**：后端以 `<目录名>.zip` 返回 Content-Disposition 与
   `application/zip`；前端在 blob 类型为 `application/zip` 且链接名缺
   `.zip` 后缀时补 `.zip`，其余沿用链接名。
6. **测试卫生**：`frontend/test-results/.last-run.json` 属于运行产物，本轮
   只恢复父任务改动，不新增跟踪策略变更；测试断言的真实 ZIP 字节在
   backend 层用 `zipfile` 解析验证。

## 四、方案与回归合同

### 变更清单

| 文件 | 变更 |
|------|------|
| `frontend/.../chat/slashSkillCommands.ts` | `filterInstalledSkillCommands` 匹配前剥离尾部换行伪影（真因修复） |
| `frontend/.../chat/MarkdownInputEditor.tsx` | `useEditor` 增加 `immediatelyRender: false` |
| `frontend/.../chat/__tests__/MarkdownInputEditorSlashRegression.test.ts` | 修复 harness `createElement` 缺陷，保留序列化 + SSR 配置断言 |
| `frontend/.../chat/__tests__/SlashSkillCommands.test.ts` | 新增序列化伪影草稿匹配用例 |
| `frontend/.../chat/__tests__/AIInputDockSlashMenuRegression.test.ts` | 新增：mock Skill 目录/system-config，真实键盘输入 `/` → listbox 渲染、Enter 选择、Escape 收起 |
| `frontend/.../chat/__tests__/WorkspaceUriPreview.test.ts` | 增加 download 端点路由 mock 与目录 ZIP 下载用例；断言图片走 content、显式下载走 download、文件名 `.zip` |
| `backend/routers/workspace.py` | download 端点补齐防护链与不创建语义；文件分支 `reject_symlinks=True` |
| `backend/libs/claude_agent_kit/server/workspace.py` | `read_workspace_download_content` 文件分支按合同拒绝符号链接 |
| `backend/tests/test_workspace_router.py` | 新增：他人 Thread 404、Mode 关闭 409、`.dream`/`.claude`/遍历路径 400、缺失工作区不创建 |
| `frontend/test-results/.last-run.json` | 恢复父任务误改的 `failed` 状态 |
| 受影响 `.folder.md` / 协议文档 | 同步本轮合同 |

### 验收命令

- `cd backend && python3 -m unittest tests.test_workspace_router -v`
- `cd frontend && pnpm exec playwright test app/_dream/components/chat/__tests__/MarkdownInputEditorSlashRegression.test.ts app/_dream/components/chat/__tests__/AIInputDockSlashMenuRegression.test.ts app/_dream/components/chat/__tests__/WorkspaceUriPreview.test.ts app/_dream/components/chat/__tests__/MarkdownInputEditor.test.ts --reporter=line --workers=1`

## 五、评审结论（防过度设计自审）

1. 两问题均为"修复既有实现 + 补齐验证"，无新增业务端点、组件、状态机、
   配置面或环境分支；斜杠菜单代码零逻辑改动（仅一行 Tiptap 配置）。
2. 下载端点防护复用 content 端点既有 helper（所有权/Mode 校验、路径校验
   泛化为 `WORKSPACE_SUBDIRS` 参数），不复制第二套校验逻辑。
3. 明确把"workspace 路由其余端点的所有权加固"排除在本轮外，避免范围蔓延。
4. 测试新增集中于用户点名的验收面（真实 ZIP 字节/目录内容、文件名、
   预览不回归、权限与路径保护、菜单链路），未增加与验收无关的
   浏览器 revision、远程环境或部署状态检查。
