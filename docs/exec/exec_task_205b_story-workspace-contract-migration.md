# Exec Report: task_205b - Story Workspace 合同 canonical 迁移与 Python 启动恢复

## 1. 执行上下文

- Task ID: `task_205b`
- 执行 Issue: [SUO-308](/SUO/issues/SUO-308)
- 来源 Issue: [SUO-300](/SUO/issues/SUO-300) / `SUO-299-SH-001`
- Parent / Ancestor: [SUO-301](/SUO/issues/SUO-301) / [SUO-273](/SUO/issues/SUO-273) / [SUO-198](/SUO/issues/SUO-198)
- 关联设计稿:
  - `docs/design/story-workspace/product-scope-and-navigation.md` §3.5.4 / §7.5 / `DEC-026`
  - `docs/design/story-workspace/product-scope-and-navigation.md` §10.5 / §11.7 / `DEC-026`
- 关联任务: `docs/task/task_205b_backend_story-workspace-contract-migration.md`
- 关联 Stage: `docs/stage/stage_story-workspace.md` §13.2～§13.3（`SUO-301-direct-repair`）
- 执行 Agent: `ExecTaskAgent`
- 执行时间: 初始实现 `2026-08-01 20:33～20:44 CST (+0800)`；冻结复验 `2026-08-01 21:03～21:06 CST (+0800)`
- Paperclip runs: 初始实现 `f00a8af1-2deb-4a42-a052-c51f02cb6899`；最终复验 `45dfda50-dabb-466f-a5f3-8f64bc46a4f9`
- Checkout: 初始实现由 ExecTaskAgent checkout；最终复验由 heartbeat harness 为 ExecTaskAgent 预先 claim
- 最终执行状态: `completed`（[SUO-313](/SUO/issues/SUO-313) 建立只读冻结后，完整验证矩阵与数据库 hash Gate 均通过）

## 2. TASK-REQUIREMENT-FORMAT.md 填充摘要

- 模板路径: `docs/task/TASK-REQUIREMENT-FORMAT.md`（只读，未修改）
- 输入 Issue: [SUO-308](/SUO/issues/SUO-308)；高优先级、standard mode、无 blocker，最新 Gate 评论结论为九项 readiness check 全部 PASS
- 输入 Task: `task_205b`，唯一 Task 文档为 `docs/task/task_205b_backend_story-workspace-contract-migration.md`
- 输入 Stage: `SUO-301-direct-repair`，`task_205b` 为严格串行队首，执行期间独占 router / Agent integration / Claude consumer
- 填充后的执行目标: 原子迁移 Story Workspace 前后端合同 owner，删除遮蔽 stdlib 的顶层 `backend/types/`，保持 wire、Schema、数据库和 UI 行为不变
- 交付类型: shared / backend-led canonical contract migration
- 明确不负责: review workflow、浏览器/Network 补证、Schema/DDL、数据库、UI 页面/组件、依赖及 Story Workspace 之外业务域
- 关键约束:
  - 后端唯一 owner 为 `backend/story_workspace/contracts.py`
  - 前端唯一 owner 为 `frontend/src/hooks/story-workspace/contracts.ts`
  - 后端公开合同使用 `StoryWorkspace*` / `STORY_WORKSPACE_*`
  - 不保留旧路径 shim、alias、re-export、复制件或 `sys.path` workaround
  - `backend/database.py` 严格只读，前后内容 hash 必须一致
  - 仅写 Task §7.1 / Stage §13.3 / Issue Allowed 的同一闭集
- 验收条件: `AC-205B-01`～`AC-205B-08` 全量带入，无删减或放宽
- 测试要求: import smoke、三组 focused unittest、frontend build、六文件 scoped ESLint、两组禁止扫描、hash/path/diff 检查
- 回滚要求: canonical owner、旧 owner 删除及全部直接消费者 import 作为一个原子差异反向应用，不得形成双 owner
- 模板 Gate 结果: PASS；占位输入、Stage 准入、锁、边界、验收、测试和回滚信息齐全

## 3. 模型生成的执行任务

- 任务目标: 在不改变任何 wire / Schema / UI 语义的条件下完成两端 canonical owner 迁移，并恢复从 `backend/` 启动 Python 的 import 安全性
- 实现范围:
  1. 将原后端 dataclass/Enum 合同、router patch Pydantic 合同和 Agent payload Pydantic 合同集中到 canonical 模块
  2. 统一所有公开后端名称并让 router、service、Claude consumer 与定向测试直接 import canonical 名称
  3. 删除旧 `backend/types/` owner，不提供兼容层
  4. 将前端 `types.ts` 原样迁为 `contracts.ts`，只改五个直接消费者/barrel 的 import
  5. 新增 canonical/前缀/默认值/校验/stdlib/旧路径定向测试
  6. 执行 Task §9 与 Stage §13.3 的完整验证矩阵并回填证据
- 范围校验: PASS；生成任务仅命中 Allowed 闭集，没有申请或使用额外路径
- 既有改动处理: router、Agent integration/test 与 hooks 为前序 task 未跟踪产物，Claude service 为前序 task modified；本次仅做模型移动、import 和类型注解的最小增量，未 reset、checkout、stash、覆盖或格式化前序逻辑

## 4. 可审计基线与冲突处理

### 4.1 执行前关键状态 / hash

| 路径 | 执行前状态 | 执行前 hash |
|---|---|---|
| `backend/story_workspace/__init__.py` | MISSING | `MISSING` |
| `backend/story_workspace/contracts.py` | MISSING | `MISSING` |
| `backend/types/__init__.py` | tracked clean | `5d21401c7f7cad964db18eb87bef875f3ec35fa2` |
| `backend/types/story_workspace/__init__.py` | tracked clean | `5d0a03bd06373e72a9580f6845a7368eb02470c2` |
| `backend/types/story_workspace/naming-checklist.md` | tracked clean | `c971939f2c134cae4816e690264489edce0e8b7d` |
| `backend/routers/story_workspace.py` | untracked（前序 task） | `c6aad6a35e7f214745e288b86a448d111447b3a7` |
| `backend/services/story_workspace/agent_integration.py` | untracked（前序 task） | `e661d373540cf62990889ca531faf4325ae33841` |
| `backend/claude_agent/service.py` | modified（前序 task） | `2ec764d62c4614703687c05f90b8400945652020` |
| `backend/tests/test_story_workspace_agent_integration.py` | untracked（前序 task） | `4de9357500c99855ce8105f39e5edc41f2d7dd1b` |
| `backend/tests/test_story_workspace_contracts.py` | MISSING | `MISSING` |
| `frontend/src/hooks/story-workspace/contracts.ts` | MISSING | `MISSING` |
| `frontend/src/hooks/story-workspace/types.ts` | untracked（前序 task） | `0d47c3590c694d510b03d9bbfe1a2e27d3f4810d` |
| `frontend/src/hooks/story-workspace/index.ts` | untracked（前序 task） | `6b889a48533e372b00b875c27c3a1fae7a40626c` |
| `frontend/src/hooks/story-workspace/useStoryWorkspaceList.ts` | untracked（前序 task） | `ebb1be786ca24af95838c8be0bad5e2641b56191` |
| `frontend/src/hooks/story-workspace/useStories.ts` | untracked（前序 task） | `552af7f6b89a3fcc7ccc48e731679238384a1ba5` |
| `frontend/src/hooks/story-workspace/useCharacters.ts` | untracked（前序 task） | `f6618a18f3022821c137b053d975eb0671cca74d` |
| `frontend/src/hooks/story-workspace/useScenes.ts` | untracked（前序 task） | `b362974621794191c34e356f8256773b90aef573` |
| `docs/exec/exec_task_205b_story-workspace-contract-migration.md` | MISSING | `MISSING` |
| `backend/database.py` | modified（闭集外既有差异，只读） | `570d54e68c9a438754f711dc15ccdd1a285a4062` |

### 4.2 冲突结论

- 允许范围内既有差异均能通过小范围 import/注解 patch 安全增量合并；没有不明 owner 或重叠逻辑冲突。
- `backend/database.py`、`backend/server.py`、设计/Issue/Task/Stage、UI 页面和组件的既有差异只记录，不回退、不暂存、不纳入本 Task。
- 本次所有实现写入均通过文件级 patch 完成；旧目录中的缓存文件仅做精确清理，没有删除其他任务产物。

## 5. 实现变更记录

| 文件 | 操作 | 最小变更说明 | 完成后 hash / 状态 |
|---|---|---|---|
| `backend/story_workspace/__init__.py` | create | 最小领域包标记，不 re-export 业务合同 | `d12cd82c2952bac6e37c32cc013d1485f6a25d78` |
| `backend/story_workspace/contracts.py` | create | 唯一后端合同 owner；承载原 dataclass/Enum、Agent payload 与 controlled patch 模型；公开名称统一前缀 | `b2ec3d73dc2c306667ee9b8eb28cf0c02bfea5c1` |
| `backend/types/__init__.py` | delete | 删除遮蔽 stdlib `types` 的顶层包入口 | MISSING |
| `backend/types/story_workspace/__init__.py` | delete | 合同迁入 canonical 后删除旧 owner | MISSING |
| `backend/types/story_workspace/naming-checklist.md` | delete | 删除代码目录中的重复命名 owner | MISSING |
| `backend/routers/story_workspace.py` | update | 移除四个 patch 模型，直接 import canonical patch / Agent payload 新名称；路由逻辑不变 | `9b8f0a36484d2a6bf188bcadfb5daa8073d40470` |
| `backend/services/story_workspace/agent_integration.py` | update | 移除三个 Agent payload 模型，直接 import canonical payload；解析/持久化逻辑不变 | `7ab5408ddb281dfeaa738663a69ab2da25d19e4b` |
| `backend/claude_agent/service.py` | update | 仅将 Story Workspace payload 类型来源和注解改为 canonical 名称；保留前序 task_204 全部逻辑 | `1d716073d7f714c3b4d6db02106c91a56763d3a3` |
| `backend/tests/test_story_workspace_agent_integration.py` | update | 仅切换 canonical payload import/名称；既有测试语义不变 | `b9819def995b94e69e42bc3c10304e94382b91b7` |
| `backend/tests/test_story_workspace_contracts.py` | create | 覆盖 canonical owner、`__all__` 前缀、枚举/默认值、Pydantic 校验、stdlib import 与旧目录消失；最终移除不必要的 `sys.path` 注入 | `045faec5f4d4d0c2f3f555b8446b08633c2555d5` |
| `frontend/src/hooks/story-workspace/contracts.ts` | create | 原 `types.ts` 内容原样迁入；字段、可选性、联合类型和 REST 形状不变 | `0d47c3590c694d510b03d9bbfe1a2e27d3f4810d` |
| `frontend/src/hooks/story-workspace/types.ts` | delete | 删除旧 owner，不保留 shim | MISSING |
| `frontend/src/hooks/story-workspace/index.ts` | update | barrel 从 `./types` 指向 `./contracts` | `2bc8afb3240f8e3c9396727c314e161ca8414edb` |
| `frontend/src/hooks/story-workspace/useStoryWorkspaceList.ts` | update | type import 从 `./types` 指向 `./contracts` | `83dab41a453319bf4bcb85a919fd8272d1be97a4` |
| `frontend/src/hooks/story-workspace/useStories.ts` | update | type import 从 `./types` 指向 `./contracts` | `1aa12b61dc98f11927d3ac155f136c8f70a94ce3` |
| `frontend/src/hooks/story-workspace/useCharacters.ts` | update | type import 从 `./types` 指向 `./contracts` | `318a258376e195968f1017da3c6beb8a08777877` |
| `frontend/src/hooks/story-workspace/useScenes.ts` | update | type import 从 `./types` 指向 `./contracts` | `8c351cce7da34a1051727f4d0ab0e151adfedf2a` |
| `docs/exec/exec_task_205b_story-workspace-contract-migration.md` | create | 唯一正式执行报告 | 本文件 |

前端 rename 的关键证据：旧 `types.ts` 执行前 hash 与新 `contracts.ts` 执行后 hash 都是 `0d47c3590c694d510b03d9bbfe1a2e27d3f4810d`，证明合同正文未发生变化。

## 6. 测试与验证

### 6.1 后端 import smoke

最终命令从 `backend/` 执行，并把项目虚拟环境置于 `PATH` 首位：

```text
PATH="$PWD/.venv/bin:$PATH" \
PYTHONPYCACHEPREFIX="$PAPERCLIP_RUN_SCRATCH_DIR/pycache-smoke-venv" \
python3 -c "import types; ...; from story_workspace.contracts import StoryWorkspaceStory, StoryWorkspaceAgentStoryPayload; import server"
```

结果: PASS（exit 0）。

- stdlib 路径: `/Users/dmeck/.local/share/uv/python/cpython-3.12.9-macos-aarch64-none/lib/python3.12/types.py`
- `types.ModuleType`: 存在
- canonical contracts import: PASS
- `server` import: PASS
- 无 `ModuleType` / `MappingProxyType` shadowing 错误

首次按 shell 默认 `python3` 执行时使用了 Homebrew Python 3.14，该解释器没有仓库依赖，因 `pydantic` / `fastapi` 缺失在 collection 前失败。未修改依赖；切换到仓库已有 `backend/.venv` 后同一验证完整通过。该环境失败不计为产品测试 PASS，已保留原因与恢复动作。

### 6.2 Focused unittest

```text
PATH="$PWD/.venv/bin:$PATH" \
PYTHONPYCACHEPREFIX="$PAPERCLIP_RUN_SCRATCH_DIR/pycache-tests-venv" \
python3 -m unittest \
  tests.test_story_workspace_contracts \
  tests.test_story_workspace_api \
  tests.test_story_workspace_agent_integration \
  -v
```

最终复验结果: PASS（exit 0），`Ran 23 tests in 0.186s`，`OK`。

- canonical 合同测试: 5 PASS
- Story Workspace API 测试: 12 PASS
- Agent integration / endpoint / Chat isolation 测试: 6 PASS

### 6.3 前端 build

```text
cd frontend && npm run build
```

结果: PASS（exit 0）。TypeScript build 与 Vite bundle 完成，`2633 modules transformed`。Vite 报告既有 dynamic-import 与 chunk-size warning，但没有 build error，也没有要求或触发配置/依赖修改。

### 6.4 前端 scoped ESLint

```text
cd frontend && npx eslint \
  src/hooks/story-workspace/contracts.ts \
  src/hooks/story-workspace/index.ts \
  src/hooks/story-workspace/useStoryWorkspaceList.ts \
  src/hooks/story-workspace/useStories.ts \
  src/hooks/story-workspace/useCharacters.ts \
  src/hooks/story-workspace/useScenes.ts
```

结果: PASS（exit 0），零 ESLint error。

### 6.5 禁止扫描

结果全部 PASS：

- `test ! -e backend/types`: PASS
- `test ! -e frontend/src/hooks/story-workspace/types.ts`: PASS
- 旧路径/import 扫描: 0 matches
- `AgentStoryPayload|AgentCharacterPayload|AgentScenePayload|WorkspacePatch|StoryPatch|CharacterPatch|ScenePatch` 旧公共符号扫描: 0 matches
- router、Agent service、Claude consumer 与两个定向测试均直接 import `story_workspace.contracts`
- 前端五个直接消费者/barrel 均直接 import/re-export `./contracts`

### 6.6 数据库、范围与格式检查

- `backend/database.py` 初始实现窗口基线 hash: `570d54e68c9a438754f711dc15ccdd1a285a4062`
- `backend/database.py` 初始实现与测试完成后首次复核 hash: `570d54e68c9a438754f711dc15ccdd1a285a4062`
- 初始收口阻塞证据: 文件在 `2026-08-01 20:43:19 CST` 被其他任务并发写入，hash 变为 `d71289c6c98cf91ebb6b36d9987991ead5663f9a`；本 Task 当时正确保持 blocked，没有把该写入归入本 Task
- 解锁证据: [SUO-313](/SUO/issues/SUO-313) 复核并冻结 `backend/database.py`，权威 Git blob 为 `d71289c6c98cf91ebb6b36d9987991ead5663f9a`，mtime `1785588199`，size `148781`
- 最终复验窗口进入 hash: `d71289c6c98cf91ebb6b36d9987991ead5663f9a`
- 最终复验窗口退出 hash: `d71289c6c98cf91ebb6b36d9987991ead5663f9a`
- 最终 hash Gate: PASS；复验前后 hash、mtime 与 size 均一致，`lsof backend/database.py` 无持有者，本 Task 在冻结窗口内对数据库与 Schema 零写入
- task-owned `git status`: 仅命中 Task §7.1 的创建/删除/最小修改路径及本报告
- scoped tracked `git diff --check`: PASS
- 对 task-owned 未跟踪文件逐文件执行 `git diff --no-index --check`: PASS
- 仓库级 tracked `git diff --check`: PASS
- 最终未保留本 Task 产生的仓库内 `__pycache__`

### 6.7 未执行项与替代证据

- 未执行浏览器/Network 验证：Stage 明确由后序 `task_202c_verify` evidence-only Issue 负责，本 Task 禁止提前执行或修改 UI。
- 未执行全仓后端测试：Task/Stage 指定的三组 focused unittest 已完整通过；扩大到全仓不属于最小充分验证。
- 未修改或重跑数据库 Schema/DDL migration：严格禁止；使用 `backend/database.py` 前后 hash 与 API/Agent focused tests 作为当前迁移的数据库零写入和行为保持证据。

### 6.8 复验中的失败项与恢复证据

- 额外禁止 workaround 扫描首次发现 `backend/tests/test_story_workspace_contracts.py` 含不必要的 `sys.path.insert(...)`。该注入不是旧 owner shim，但违反本 Task 的显式禁止规则，因此在允许闭集内移除。
- 移除时第一次重跑 focused unittest 出现 `1 ERROR / 22 PASS`：`test_stdlib_types_and_old_owner_path` 因同时误删仍被断言使用的 `Path/ROOT` 辅助常量而报 `NameError`。
- 恢复动作仅重新加入 `pathlib.Path` 与只读 `ROOT` 常量，没有恢复 `sys.path` 注入；随后完整 23 项 focused unittest 全部通过，workaround 扫描为零。
- 上述失败未被静默跳过，也没有通过旧路径、兼容层、依赖或闭集外写入规避。

## 7. 验收条件逐项结果

| 验收 ID | 结果 | 证据 |
|---|---|---|
| `AC-205B-01` | PASS | `backend/story_workspace/contracts.py` 为唯一后端 owner；`__all__` 定向测试证明全部公开名称为 `StoryWorkspace*` / `STORY_WORKSPACE_*`；旧公共符号扫描为零 |
| `AC-205B-02` | PASS | `backend/types/` 物理不存在；旧路径/import、shim/alias/re-export 扫描为零 |
| `AC-205B-03` | PASS | 从 `backend/` 使用项目虚拟环境执行 stdlib `types` + canonical contracts + `server` smoke exit 0，stdlib 来源路径明确 |
| `AC-205B-04` | PASS | router、Agent integration、Claude consumer 与定向测试直接 import canonical；23 项 focused unittest 全部通过 |
| `AC-205B-05` | PASS | `contracts.ts` 为单 owner，旧 `types.ts` 消失；五个直接消费者已更新；build 与 scoped lint 通过 |
| `AC-205B-06` | PASS | 前端 owner 文件 rename 前后 hash 相同；合同/patch/Agent/API focused tests 通过；未写 UI、Schema 或数据库逻辑 |
| `AC-205B-07` | PASS | 初始并发漂移保留为历史阻塞证据；[SUO-313](/SUO/issues/SUO-313) 建立权威冻结后，最终复验窗口前后 Git blob 均为 `d71289c6c98cf91ebb6b36d9987991ead5663f9a`，mtime/size 未漂移且无文件持有者；本 Task 零数据库/Schema 写入 |
| `AC-205B-08` | PASS | 实际 task-owned 写入仅命中允许闭集；scoped tracked、逐个 untracked whitespace 与仓库级 tracked diff check 均通过；本报告记录全部失败、未验证项与原子回滚建议 |

## 8. 风险与阻塞

- 阻塞: 无。初始 `backend/database.py` 并发写入 blocker 已由 [SUO-313](/SUO/issues/SUO-313) 的只读冻结与稳定快照解除，并完成全量复验。
- 已处理风险: allowed 文件与前序 task 产物重叠；通过执行前逐文件 hash、最小 patch 与执行后 hash 留证，保留前序逻辑。
- 环境风险: 默认 Homebrew `python3` 未安装后端依赖；正式验证已明确使用仓库 `backend/.venv`。这不是代码或依赖 blocker。
- 非阻塞 warning: 前端 build 输出既有 dynamic import / chunk-size warning；本 Task 禁止且不需要修改构建配置。
- 剩余风险: 共享工作树仍承载其他任务的大量未提交差异；后续任务必须消费当前 canonical owner，不得 reset、覆盖或恢复旧路径。
- 需要上游澄清的问题: 无。

## 9. 完成状态

- [x] 已完成实现
- [x] 已完成模板填充和模型任务范围校验
- [x] 已完成 Task / Stage 要求的全部五组最终验证
- [x] 已记录基线、文件变更、测试、未执行项与风险
- [x] 已逐项满足 `AC-205B-01`～`AC-205B-08`
- [x] 可进入 review / audit

结论：实现、测试、冻结复验与报告均已闭合；[SUO-308](/SUO/issues/SUO-308) 可标记为 `done` 并释放后序 [SUO-309](/SUO/issues/SUO-309)。

## 10. 回滚建议

回滚必须作为一个原子合同迁移反向 patch，禁止部分恢复形成双 owner：

1. 先对当前文件 hash 与本报告执行后 hash 做一致性检查，防止覆盖后序改动。
2. 反向恢复后端消费者的旧 import/注解：Claude service、router、Agent integration、Agent integration test。
3. 移除 `backend/tests/test_story_workspace_contracts.py`。
4. 同时恢复三个 `backend/types/**` 旧 owner 文件，并移除 `backend/story_workspace/contracts.py` 与最小包标记。
5. 将前端五个消费者/barrel 由 `./contracts` 恢复为 `./types`，再原子恢复 `types.ts`、移除 `contracts.ts`；两者不得并存。
6. 重新执行旧路径检查、后端 import smoke、focused unittest、前端 build/scoped lint 和 diff check。

注意事项：禁止使用 `git reset --hard`、`git checkout --`、stash 或整目录覆盖；回滚不得触碰 `backend/database.py`、Schema/DDL、依赖、UI 或其他业务域。若任一执行后 hash 已变化，停止自动回滚并生成逐文件三方反向 patch。
