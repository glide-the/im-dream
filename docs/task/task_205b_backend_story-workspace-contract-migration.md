# task_205b_backend_story-workspace-contract-migration.md

> **Task ID**: `task_205b`
> **Task 类型**: shared（backend-led canonical contract migration）
> **Paperclip Issue**: [SUO-300](/SUO/issues/SUO-300)
> **来源业务 Issue**: `SUO-299-SH-001` — Story Workspace 合同 canonical 迁移与运行恢复
> **父 / 祖先 Issue**: [SUO-273](/SUO/issues/SUO-273) / [SUO-198](/SUO/issues/SUO-198)
> **上游裁决**: `DEC-026`（[SUO-299](/SUO/issues/SUO-299) 已完成）
> **生成日期**: 2026-08-01
> **生成 Agent**: `CEOOrchestrator`（direct-repair 代拟授权）
> **状态**: canonical Task 已定义；等待独立 Stage 规划与 execute readiness check

---

## 1. 任务标题

Story Workspace 前后端合同 canonical 迁移与 Python 启动恢复

## 2. 任务目标

以一次原子、可回滚的迁移完成以下闭环：

1. 删除会从 `backend/` 启动时遮蔽 Python 标准库 `types` 的顶层 `backend/types/` 业务包。
2. 将 Story Workspace 后端合同迁入唯一 canonical 文件 `backend/story_workspace/contracts.py`，并让现有 story-workspace 请求合同及其消费者直接引用 canonical 模块。
3. 将前端本域合同由 `frontend/src/hooks/story-workspace/types.ts` 迁至同目录 `contracts.ts`，同步更新全部直接 import 与 barrel export。
4. 保持 REST payload、字段名、枚举值、校验规则、状态机、数据库结构、数据表语义和 UI 行为不变。
5. 通过后端启动/import smoke、focused unittest、前端 build/scoped lint、禁止路径扫描和差异检查证明迁移闭合。

本 Task 是 `task_205` 的合同归属修复，不重开原共享类型设计，也不新增产品能力。

## 3. 上游输入与固定约束

### 3.1 权威输入

- `docs/design/story-workspace/story-workspace-prd.md` §3.5.4 / `DEC-026`
- `docs/design/story-workspace/story-workspace-layout-design.md` §10.5 / §11.7 / `DEC-026`
- `docs/issue/ISSUES_story-workspace.md` §3.4 `SUO-299-SH-001`、§6.4、§7.6、§8.2
- `docs/task/task_205_backend_story-workspace-shared-types.md`
- `docs/exec/exec_task_205_story-workspace-shared-types.md`
- `docs/task/TASK-REQUIREMENT-FORMAT.md`（execute 时强制使用，只读）

### 3.2 不可变业务合同

- REST 路径、HTTP 方法、请求字段、响应字段与 `{ data, pagination }` 形状不变。
- `pending / confirmed / rejected / archived` 等既有前端展示值不变；后端既有枚举值不变。
- `short / long / script / outline`、`draft / published / archived` 等枚举值不变。
- Pydantic 的 `extra`、默认值、字段 validator 和错误语义不变。
- SQLite 表、列、约束、DDL、migration 与 `backend/database.py` 不变。
- task_202c 的表格、Toolbar、页面、查询参数和 UI 交互不变；只允许合同 import 来源变化。

### 3.3 Canonical owner 规则

- 后端 Story Workspace 请求、响应、事件、投影、审阅值对象和 Agent 输入合同唯一归属 `backend/story_workspace/contracts.py`。
- 前端局部 REST 合同唯一归属 `frontend/src/hooks/story-workspace/contracts.ts`。
- 后端公开 Python 业务类型使用 `StoryWorkspace*` 前缀；合同版本常量使用 `STORY_WORKSPACE_*` 前缀。
- 不在旧路径或其他通用 `types` 路径保留 re-export、alias、shim、复制件或兼容包。
- `backend/story_workspace/__init__.py` 只作为最小包标记，不 re-export 业务合同；消费者直接 import `story_workspace.contracts`。

## 4. 当前基线与迁移差异

### 4.1 已确认基线

- 后端旧合同文件当前为：
  - `backend/types/__init__.py`
  - `backend/types/story_workspace/__init__.py`
  - `backend/types/story_workspace/naming-checklist.md`
- 从 `backend/` 启动 Python 时，顶层 `backend/types/` 会优先于标准库 `types` 被解析，既有 exec 报告已记录 `ModuleType` 等标准库符号缺失。
- 后端真实请求合同目前还分散在：
  - `backend/routers/story_workspace.py` 的 patch 请求模型
  - `backend/services/story_workspace/agent_integration.py` 的 Agent payload 模型
- 上述 Agent payload 的直接消费者还包括：
  - `backend/routers/story_workspace.py`
  - `backend/claude_agent/service.py`
  - `backend/tests/test_story_workspace_agent_integration.py`
- 前端旧合同 `frontend/src/hooks/story-workspace/types.ts` 的直接 import 仅存在于：
  - `frontend/src/hooks/story-workspace/index.ts`
  - `frontend/src/hooks/story-workspace/useStoryWorkspaceList.ts`
  - `frontend/src/hooks/story-workspace/useStories.ts`
  - `frontend/src/hooks/story-workspace/useCharacters.ts`
  - `frontend/src/hooks/story-workspace/useScenes.ts`
- 表格、Toolbar 与页面通过 `frontend/src/hooks/story-workspace/index.ts` 消费合同；迁移不要求改写这些间接消费者。

### 4.2 增量原则

- 只迁移合同归属、公共符号名称与 import；不得趁机重构路由、持久化、Hooks、表格或页面。
- 旧路径扫描已经为零的消费者不做“预防性”修改。
- 若 execute checkout 后出现新的旧路径直接消费者，只能先在执行 Issue 评论记录文件、owner 与冲突，再由 CEOOrchestrator 重新裁决边界；ExecTaskAgent 不自行扩大闭集。

## 5. 实现步骤

### Step 1：记录可审计基线

1. 记录 `git status --short --untracked-files=all`，区分既有工作树改动与本 Task 改动。
2. 记录第 7.1 节全部允许文件的存在状态与 blob hash；不存在的文件记为 `MISSING`。
3. 单独记录 `backend/database.py` 的 `git hash-object` 值，完成时必须一致。
4. 记录 `backend/types/`、前端 `types.ts` 和所有旧 import 的扫描结果，作为迁移前证据。

### Step 2：建立后端 canonical 包

1. 新建 `backend/story_workspace/__init__.py`，内容只保留最小包说明，不导出业务类型。
2. 新建 `backend/story_workspace/contracts.py`。
3. 将 `backend/types/story_workspace/__init__.py` 的有效合同迁入 `contracts.py`，保持字段、默认值、dataclass/Pydantic 校验、枚举值和序列化语义不变。
4. 将 `backend/routers/story_workspace.py` 的 patch 请求模型迁入 `contracts.py`；router 只保留路由和业务流程并直接 import canonical 名称。
5. 将 `backend/services/story_workspace/agent_integration.py` 的 Agent payload 模型迁入 `contracts.py`；service 只保留解析、持久化和错误处理并直接 import canonical 名称。
6. 更新 `backend/claude_agent/service.py` 的 story-workspace payload import 与类型注解；不得修改 Claude Agent 其他逻辑。
7. 更新定向测试对合同的 import 与名称；不得通过 service/router re-export 旧名称来让测试“继续通过”。

### Step 3：统一后端公共符号前缀

迁移后的公开符号按下表改名；只改 Python import 名称，不改变 wire contract：

| 旧符号 | Canonical 符号 |
|---|---|
| `TYPE_CONTRACT_VERSION` | `STORY_WORKSPACE_CONTRACT_VERSION` |
| `ReviewStatus` | `StoryWorkspaceReviewStatus` |
| `ContentStatus` | `StoryWorkspaceContentStatus` |
| `StoryType` | `StoryWorkspaceStoryType` |
| `RoleType` | `StoryWorkspaceRoleType` |
| `BatchAction` | `StoryWorkspaceBatchAction` |
| `ResourceType` | `StoryWorkspaceResourceType` |
| `PaginationInfo` | `StoryWorkspacePaginationInfo` |
| `PaginatedResponse` | `StoryWorkspacePaginatedResponse` |
| `StoryFilter` | `StoryWorkspaceStoryFilter` |
| `CharacterFilter` | `StoryWorkspaceCharacterFilter` |
| `SceneFilter` | `StoryWorkspaceSceneFilter` |
| `ReviewActionRequest` | `StoryWorkspaceReviewActionRequest` |
| `BatchReviewRequest` | `StoryWorkspaceBatchReviewRequest` |
| `BatchReviewResponse` | `StoryWorkspaceBatchReviewResponse` |
| `WorkspaceStats` | `StoryWorkspaceStats` |
| `AgentCharacterOutput` | `StoryWorkspaceAgentCharacterOutput` |
| `AgentSceneOutput` | `StoryWorkspaceAgentSceneOutput` |
| `AgentStoryOutput` | `StoryWorkspaceAgentStoryOutput` |
| `AgentOutputRequest` | `StoryWorkspaceAgentOutputRequest` |
| `AgentCharacterPayload` | `StoryWorkspaceAgentCharacterPayload` |
| `AgentScenePayload` | `StoryWorkspaceAgentScenePayload` |
| `AgentStoryPayload` | `StoryWorkspaceAgentStoryPayload` |
| `WorkspacePatch` | `StoryWorkspaceWorkspacePatch` |
| `StoryPatch` | `StoryWorkspaceStoryPatch` |
| `CharacterPatch` | `StoryWorkspaceCharacterPatch` |
| `ScenePatch` | `StoryWorkspaceScenePatch` |

已符合 `StoryWorkspace*` 的实体名称保持不变。内部基类分别改为 `_StoryWorkspaceAgentPayload` 与 `_StoryWorkspaceControlledPatch`。`__all__` 只能暴露 `StoryWorkspace*` 或 `STORY_WORKSPACE_*` 名称；禁止暴露旧名。

### Step 4：删除后端旧 owner

1. 删除 `backend/types/story_workspace/__init__.py`。
2. 删除 `backend/types/story_workspace/naming-checklist.md`；命名规则已由设计文档与本 Task 固化，不在代码目录复制一份新 checklist。
3. 删除 `backend/types/__init__.py`，最终移除空目录 `backend/types/`。
4. 不创建 `backend/types.py`、`backend/types/` shim、`sys.path` workaround 或任何旧名 alias。

### Step 5：迁移前端本域合同

1. 将 `frontend/src/hooks/story-workspace/types.ts` 原子迁移为 `frontend/src/hooks/story-workspace/contracts.ts`。
2. 保持所有 type/interface 名称、字段、可选性、联合类型、默认语义和 REST payload 形状不变。
3. 把第 4.1 节列出的五个直接消费者从 `./types` 更新为 `./contracts`。
4. `frontend/src/hooks/story-workspace/index.ts` 继续作为本域稳定 barrel，但不得 re-export `./types`，不得创建兼容文件。
5. 表格、Toolbar、页面和路由只读；build 若暴露真实 import 缺口，先证明缺口是本迁移直接导致，再按 Issue 协议申请边界变更，不得顺手修改 UI。

### Step 6：完成验证与报告

1. 按第 9 节逐项执行命令，并把结果映射到第 8 节验收 ID。
2. 比较执行前后 `backend/database.py` hash，证明当前 Task 零写入；不能用相对 `HEAD` 的全局 diff 代替，因为工作树可能已有他人改动。
3. 生成 task-owned 文件清单，确认只命中第 7.1 节闭集。
4. ExecTaskAgent 在 `docs/exec/exec_task_205b_story-workspace-contract-migration.md` 回填执行报告、测试输出、未验证项和逐文件回滚建议。

## 6. 输入 / 输出说明

### 输入

- `task_205` 已落地的后端 dataclass/Enum 合同
- story-workspace router 的 patch Pydantic 请求合同
- Agent integration 的 payload Pydantic 合同及消费者
- task_202c 已落地的前端局部 REST 合同及 Hooks
- `DEC-026` canonical owner 与禁止兼容层裁决

### 输出

- `backend/story_workspace/contracts.py`：唯一后端业务合同 owner
- `backend/story_workspace/__init__.py`：无业务 re-export 的最小包标记
- 删除 `backend/types/**` 并更新全部受影响的后端直接消费者
- `frontend/src/hooks/story-workspace/contracts.ts`：唯一前端局部 REST 合同 owner
- 删除旧 `types.ts` 并更新五个直接消费者
- `backend/tests/test_story_workspace_contracts.py`：canonical 路径、前缀、默认值与禁止旧路径的定向回归
- 正式 execute 报告：`docs/exec/exec_task_205b_story-workspace-contract-migration.md`

## 7. 写入边界

### 7.1 允许修改范围（闭集）

| 路径 | 动作 | 允许的最小变更 |
|---|---|---|
| `backend/story_workspace/__init__.py` | 新建 | 最小包说明；不得 re-export 合同 |
| `backend/story_workspace/contracts.py` | 新建 | 承载本 Task 点名的 Story Workspace 合同；无业务逻辑 |
| `backend/types/__init__.py` | 删除 | 删除旧顶层 `types` 包入口 |
| `backend/types/story_workspace/__init__.py` | 删除 | 内容迁入 canonical 后删除 |
| `backend/types/story_workspace/naming-checklist.md` | 删除 | 删除代码目录中的重复命名 owner |
| `backend/routers/story_workspace.py` | 修改 | 移出 patch 模型，改为 canonical import 与新名称；路由逻辑不变 |
| `backend/services/story_workspace/agent_integration.py` | 修改 | 移出 payload 模型，改为 canonical import 与新名称；解析/持久化逻辑不变 |
| `backend/claude_agent/service.py` | 修改 | 仅更新 Story Workspace payload import 与类型注解 |
| `backend/tests/test_story_workspace_agent_integration.py` | 修改 | 仅更新 canonical import、类型名及迁移直接相关断言 |
| `backend/tests/test_story_workspace_contracts.py` | 新建 | 覆盖 canonical import、公开名称、值/默认值、旧路径消失与 stdlib import safety |
| `frontend/src/hooks/story-workspace/contracts.ts` | 新建 | 从旧 `types.ts` 迁入，合同语义不变 |
| `frontend/src/hooks/story-workspace/types.ts` | 删除 | 删除旧 owner，不保留 shim |
| `frontend/src/hooks/story-workspace/index.ts` | 修改 | `./types` 改为 `./contracts` |
| `frontend/src/hooks/story-workspace/useStoryWorkspaceList.ts` | 修改 | `./types` 改为 `./contracts` |
| `frontend/src/hooks/story-workspace/useStories.ts` | 修改 | `./types` 改为 `./contracts` |
| `frontend/src/hooks/story-workspace/useCharacters.ts` | 修改 | `./types` 改为 `./contracts` |
| `frontend/src/hooks/story-workspace/useScenes.ts` | 修改 | `./types` 改为 `./contracts` |
| `docs/exec/exec_task_205b_story-workspace-contract-migration.md` | 新建 / 更新 | 仅由 ExecTaskAgent 写正式执行报告 |

除上述路径外，所有仓库路径默认禁止修改。目录名不构成扩大父目录写权限的授权。

### 7.2 禁止修改范围

- `backend/database.py`：严格只读；执行前后 blob hash 必须一致。
- 所有 Schema、DDL、migration、SQL 文件和数据库结构。
- `backend/server.py`、依赖、环境配置、Docker、部署文件与生成物。
- 除 `backend/claude_agent/service.py` 点名 import/注解外的 Claude Agent 逻辑。
- Story Workspace 之外的其他业务域与通用类型整理。
- `frontend/src/components/**`、`frontend/src/pages/**`、`frontend/src/router/**`、`frontend/src/App.tsx`。
- `frontend/package.json`、任何 lockfile、构建配置、lint 配置、测试 runner 与仓库内 mock。
- `docs/design/**`、`docs/issue/**`、`docs/stage/**`、其他 `docs/task/**`、既有 `docs/exec/**`。
- `docs/task/TASK-REQUIREMENT-FORMAT.md`：execute 时只读，禁止预填或改写模板源文件。
- REST payload、字段名、状态机、数据库语义、表格/Toolbar/页面行为、产品范围。

### 7.3 冲突处理

- 若允许文件在 execute checkout 时已有无法归属或无法安全合并的并发改动，停止受影响写入并在执行 Issue 评论记录文件、现有 diff owner、冲突点和解锁动作。
- 禁止覆盖、reset、checkout、stash 或格式化他人改动。
- 对已存在但与本 Task 无关的工作树差异只做基线记录，不纳入本 Task 变更摘要。

## 8. 验收条件

| 验收 ID | 验收条件 | 必须证据 |
|---|---|---|
| `AC-205B-01` | 后端业务合同唯一位于 `backend/story_workspace/contracts.py`；公开业务类均为 `StoryWorkspace*`，版本常量为 `STORY_WORKSPACE_*` | canonical import + `__all__` 定向 unittest + 符号扫描 |
| `AC-205B-02` | `backend/types/` 已删除；不存在旧路径 import、re-export、alias、shim 或同名复制件 | 文件存在性检查 + `rg` 禁止路径扫描 |
| `AC-205B-03` | 从 `backend/` 启动 Python 可加载标准库 `types`、canonical contracts 与 `server`，不再发生遮蔽 | 启动/import smoke 完整输出 |
| `AC-205B-04` | router、Agent integration、Claude consumer 与定向测试直接引用 canonical 名称，行为和校验规则不变 | focused unittest + direct-import scan |
| `AC-205B-05` | 前端唯一合同文件为 `contracts.ts`；旧 `types.ts` 消失，五个直接消费者全部更新且无兼容层 | 文件扫描 + scoped lint + build |
| `AC-205B-06` | REST payload、字段、枚举值、状态机、现有数据表语义与 task_202c UI 行为不变 | 合同测试 + API/Agent focused unittest + build；无 UI 文件 diff |
| `AC-205B-07` | `backend/database.py`、Schema / DDL / migration、依赖与其他业务域对本 Task 零写入 | 前后 hash 比对 + task-owned path 清单 |
| `AC-205B-08` | 实际变更仅命中允许闭集，格式检查通过，报告包含未验证项与回滚建议 | `git diff --check` + 变更清单 + exec report |

任一验收项缺少证据时，不得宣称 execute 完成。

## 9. 测试与验证策略

所有命令从仓库根目录开始；Python 缓存写入 `PAPERCLIP_RUN_SCRATCH_DIR`，不得在仓库生成 `__pycache__`。

### 9.1 后端启动 / import smoke

```bash
cd backend && \
PYTHONPYCACHEPREFIX="$PAPERCLIP_RUN_SCRATCH_DIR/pycache" \
python3 -c "import types; assert hasattr(types, 'ModuleType'); from story_workspace.contracts import StoryWorkspaceStory, StoryWorkspaceAgentStoryPayload; import server"
```

通过标准：命令 exit 0；`types` 来自 Python 标准库；canonical 类型与 `server` 可导入；无 `types.ModuleType` / `MappingProxyType` 遮蔽错误。

### 9.2 Focused unittest

```bash
cd backend && \
PYTHONPYCACHEPREFIX="$PAPERCLIP_RUN_SCRATCH_DIR/pycache" \
python3 -m unittest \
  tests.test_story_workspace_contracts \
  tests.test_story_workspace_api \
  tests.test_story_workspace_agent_integration \
  -v
```

通过标准：全部测试通过；覆盖 canonical import、公共符号、字段/默认值、payload 校验、API 列表/详情/patch、Agent 解析与持久化，不以旧名 re-export 通过。

### 9.3 前端 build

```bash
cd frontend && npm run build
```

通过标准：TypeScript build 与 Vite bundle 均成功；所有间接消费者通过 stable barrel 解析到 `contracts.ts`。

### 9.4 前端 scoped lint

```bash
cd frontend && npx eslint \
  src/hooks/story-workspace/contracts.ts \
  src/hooks/story-workspace/index.ts \
  src/hooks/story-workspace/useStoryWorkspaceList.ts \
  src/hooks/story-workspace/useStories.ts \
  src/hooks/story-workspace/useCharacters.ts \
  src/hooks/story-workspace/useScenes.ts
```

通过标准：零 ESLint error；不得以修改 lint 配置或依赖来绕过。

### 9.5 禁止路径与兼容层扫描

```bash
test ! -e backend/types
test ! -e frontend/src/hooks/story-workspace/types.ts
! rg -n "backend\.types\.story_workspace|types\.story_workspace|hooks/story-workspace/types|from ['\"]\./types['\"]" \
  backend frontend/src --glob '*.py' --glob '*.ts' --glob '*.tsx'
! rg -n "\\b(AgentStoryPayload|AgentCharacterPayload|AgentScenePayload|WorkspacePatch|StoryPatch|CharacterPatch|ScenePatch)\\b" \
  backend --glob '*.py'
```

通过标准：旧路径、旧直接 import、旧公开符号、兼容层均为零；单词边界不得把 canonical `StoryWorkspaceAgentStoryPayload` 等新名称误判为旧名。

### 9.6 数据库与范围检查

```bash
git hash-object backend/database.py
git status --short --untracked-files=all
git diff --name-only --diff-filter=ACDMRTUXB -- \
  backend/story_workspace \
  backend/types \
  backend/routers/story_workspace.py \
  backend/services/story_workspace/agent_integration.py \
  backend/claude_agent/service.py \
  backend/tests/test_story_workspace_agent_integration.py \
  backend/tests/test_story_workspace_contracts.py \
  frontend/src/hooks/story-workspace
```

通过标准：`backend/database.py` 前后 hash 完全一致；task-owned 变更逐项落在第 7.1 节，未出现 UI、Schema、依赖或其他业务域写入。共享工作树已有差异必须与执行前基线对照，不能误记为本 Task 产物。

### 9.7 差异格式检查

```bash
git diff --check -- \
  backend/story_workspace \
  backend/types \
  backend/routers/story_workspace.py \
  backend/services/story_workspace/agent_integration.py \
  backend/claude_agent/service.py \
  backend/tests/test_story_workspace_agent_integration.py \
  backend/tests/test_story_workspace_contracts.py \
  frontend/src/hooks/story-workspace
```

通过标准：exit 0。另执行一次仓库级 `git diff --check`；若它命中执行前已经存在的越界差异，报告必须给出执行前后相同的证据，且本 Task scoped 检查仍须通过。

### 9.8 测试失败规则

- 任一命令失败时保留命令、exit code、首个可行动错误与影响范围。
- 不得恢复旧 `types` shim 来规避 Python 启动失败。
- 不得修改数据库、依赖、构建配置或 UI 来规避测试失败。
- 若失败来自闭集外既有问题，记录 owner/action 并按 Issue 协议阻塞；不得把“未运行”写成 PASS。

## 10. 完成标志

- [ ] `backend/story_workspace/contracts.py` 成为唯一后端 canonical owner。
- [ ] `backend/story_workspace/__init__.py` 不含业务 re-export。
- [ ] `backend/types/` 完全删除且旧路径/旧公开名扫描为零。
- [ ] 后端请求合同迁出 router/service，全部直接消费者引用 canonical 名称。
- [ ] 从 `backend/` 启动 Python、导入标准库 `types`、canonical contracts 与 `server` 均成功。
- [ ] 三组 focused unittest 全部通过。
- [ ] 前端 `contracts.ts` 已建立，旧 `types.ts` 删除，五个直接消费者更新。
- [ ] 前端 build 与 scoped lint 通过。
- [ ] REST、枚举、校验、状态机、数据库和 task_202c UI 语义不变。
- [ ] `backend/database.py` 前后 hash 一致，无 Schema / DDL / migration / 依赖变更。
- [ ] task-owned 路径闭集检查与 `git diff --check` 通过。
- [ ] Exec report 已记录变更、测试、未验证项、风险和逐文件回滚建议。

## 11. 风险与缓解

| 风险 | 影响 | 缓解 |
|---|---|---|
| 顶层 `backend/types/` 遮蔽标准库 | Python 从 `backend/` 无法启动 | 必须物理删除旧包，并从 `backend/` 执行 smoke |
| 为兼容旧 import 保留 alias/shim | 形成双 owner，问题复发 | 禁止兼容层；更新所有直接消费者并扫描为零 |
| 移动 Pydantic 模型时改变校验 | 请求行为或错误语义漂移 | 原样保留字段、默认值、`extra` 与 validator；focused unittest 回归 |
| 公共 Python 名称前缀迁移漏改 | 运行时 import 失败 | 明确映射表、直接消费者扫描与 `__all__` 测试 |
| 前端 rename 漏掉 import | build 失败 | 五个直接消费者闭集 + build + scoped lint |
| 共享工作树污染范围判断 | 误回滚他人改动 | 前置 status/hash 基线、task-owned 路径清单、逐文件反向 patch |
| 借迁移修改数据库或 UI | 越权且难以审计 | `backend/database.py` hash gate、闭集、禁止路径扫描 |

## 12. 回滚策略

回滚必须把本 Task 的迁移视为一个原子变更，但按迁移清单逐文件审查和反向 patch。禁止 `git reset`、`git checkout --`、目录覆盖、整目录复制、stash 清理或回退包含他人改动的提交。

### 12.1 回滚前置

1. 使用执行报告记录的 task-owned diff 生成反向 patch，并先执行逐文件 `--check`。
2. 对照执行前 blob hash，确认允许文件没有被后续工作再次修改；若已变化，停止并拆分人工可审查的三方 patch。
3. 回滚必须一次覆盖全部消费者和 owner 文件，不允许留下双 owner 或悬空 import。

### 12.2 逐文件反向顺序

1. 后端消费者：反向 patch `backend/claude_agent/service.py`、`backend/routers/story_workspace.py`、`backend/services/story_workspace/agent_integration.py`、`backend/tests/test_story_workspace_agent_integration.py`，恢复旧名称和旧 import 关系。
2. 后端测试：反向移除 `backend/tests/test_story_workspace_contracts.py`。
3. 后端 owner：逐文件恢复 `backend/types/__init__.py`、`backend/types/story_workspace/__init__.py`、`backend/types/story_workspace/naming-checklist.md`，再反向移除 `backend/story_workspace/contracts.py` 与最小 `backend/story_workspace/__init__.py`。
4. 前端消费者：反向 patch五个直接 import 文件，由 `./contracts` 恢复为 `./types`。
5. 前端 owner：按文件级 rename 的反向 patch 恢复 `types.ts`，移除 `contracts.ts`；不得同时保留两者。
6. 重新执行旧路径存在性、后端 focused unittest、前端 build/scoped lint 和 `git diff --check`，记录回滚后的可运行状态。

`backend/database.py`、Schema / DDL、依赖、UI 与其他业务域不属于回滚清单，任何回滚 patch 命中这些路径都必须拒绝。

## 13. Stage 与 Execute Handoff

### 13.1 StagePlanner 必须固化的准入

- 为 `SUO-299` 增量建立独立 Stage，不能复用旧 `stage_story-workspace.md` 直接准入。
- 将 `task_205b` 放入“合同 canonical 迁移与运行恢复”wave；该 wave 必须先于 task_202c 浏览器/Network evidence-only 验证。
- Stage 完成信号至少包含：旧路径为零、`backend/` Python 启动恢复、focused unittest 通过、前端 build/scoped lint 通过、`backend/database.py` hash 不变、闭集与 diff check 通过。
- Stage 不得把浏览器/Network 补证合并进本 Task；后续验证 Task 只能在本迁移完成后进入 execute。

### 13.2 当前 execute readiness

| 检查项 | 当前状态 |
|---|---|
| task 任务内容 | ✅ 本文档已定义 |
| 关联 Issue | ✅ `SUO-299-SH-001` / [SUO-300](/SUO/issues/SUO-300) |
| 关联 Stage 允许 execute | ❌ 尚未由 StagePlanner 形成独立增量 Stage |
| `TASK-REQUIREMENT-FORMAT.md` | ✅ 存在；execute 时只读使用 |
| 允许修改范围 | ✅ 第 7.1 节闭集 |
| 禁止修改范围 | ✅ 第 7.2 节 |
| 验收条件 | ✅ 第 8 节 |
| 测试 / 验证 | ✅ 第 9 节 |
| execute Issue checkout / assignee | ❌ 尚未创建或切换到 ExecTaskAgent |
| 结论 | **NOT READY — 当前只允许进入 Stage 规划，不得指派 execute** |

### 13.3 正式 execute 约束

Stage 准入通过后，CEOOrchestrator 仍须重新执行九项 execute readiness check。正式执行必须由 ExecTaskAgent：

1. 先 checkout 唯一 execute Issue；
2. 读取 `agents/exec-task-agent/AGENTS.md`；
3. 读取并以当前 Issue + 本 Task + 最新 Stage 完整填充 `docs/task/TASK-REQUIREMENT-FORMAT.md`；
4. 基于格式化后的单 Task prompt 执行，不得绕过模板；
5. 仅写第 7.1 节实现闭集及正式报告 `docs/exec/exec_task_205b_story-workspace-contract-migration.md`。

本 Task 文档的完成不等于 execute 准入，也不授权 CEOOrchestrator 直接实现迁移。
