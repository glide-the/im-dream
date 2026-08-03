# Dream Surface Task 1 实施记录（packer surfaces[] 校验 + .dream 物化 + manifest/receipt 透出）

> 依据：`2026-08-03-dream-surface-execution-implementation-plan.md` Task 1（Step 0–Step 7）
> 日期：2026-08-04

## Step 0 决策记录（E14）

- **决策：选① 迁移脚本**（按复核批注 R1 推荐）。选②「旧库无 surface 降级」会让存量开发库长期无 surface、演示/回归路径分叉，且 Task 6 e2e 在旧库上会静默走无 surface 路径（验收假阳性），否决。
- 新增内置插件 profile：`plugins/ink-dream-story/.ink/workspace-init.json`（`workspace-init/v1` + `surfaces: [{name: dream, protocol_dir: .dream, entry_route: /story-workspace/dream}]`，不含 runtime_dirs/workspace_files/python）。
- 迁移脚本：`scripts/migrate_ink_dream_story_digest.py`（UPDATE-only，无 DDL，幂等）：
  1. `import_tree` 把插件源码重新导入 content-addressed artifact store（注册新 digest 的制品目录）；
  2. `claude_plugin_installations`：刷新内置包行的 `artifact_digest` 与 `artifact_path`；
  3. `deck_claude_plugin_refs`：刷新内置 spec 行的 `artifact_digest`；
  4. `deck_runtime_plugin_locks.lock_json`：重写 JSON 内 `claude_code_plugins[].artifact_digest`（按 `source_ref == builtin://ink-dream-story` 匹配）。
- 执行证据：`python scripts/migrate_ink_dream_story_digest.py` → `installations=1 refs=0 locks=1`（本开发库无内置 spec 的 refs 行，refs=0 属实）；副本验证后二次运行 `0/0/0`（幂等）。新 digest：`sha256:77d77a10…92b3ed`。
- 冻结工作区不迁移：既有 launch-manifest 钉住旧 digest，属冻结合同，非缺陷。

## 与 PLAN 的偏差（均按代码现实调整，语义不变）

1. **错误类型**：PLAN 示例在 `workspace_init.py` 中抛 `WorkspacePackError`。代码现实：`WorkspacePackError` 定义于 `workspace_packer.py`，反向 import 会成循环依赖；模块内惯例是 `WorkspaceInitError(code, message)`，packer 经 `_as_pack_error` 在 pack 边界转为 `WorkspacePackError` 且**保留同一 code**。故 `validate_surfaces` 抛 `WorkspaceInitError("CLAUDE_PLUGIN_INIT_PROFILE_INVALID", …)`；pack 期可观测行为与 PLAN 完全一致（错误码 `CLAUDE_PLUGIN_INIT_PROFILE_INVALID`，fail-closed）。
2. **测试文件路径**：PLAN 写 `backend/tests/services/claude_plugin/test_workspace_init_surfaces.py`；代码现实：后端测试扁平存放于 `backend/tests/`（无 `tests/services/` 目录）。实际落在 `backend/tests/test_workspace_init_surfaces.py`，与既有 `test_workspace_init.py` 同级，沿用 unittest 风格。
3. **唯一性规则**：design_004 §3.1 要求 profile 内 `name` 与 `protocol_dir` 各自不得重复；PLAN 示例的 `(name, protocol_dir)` 元组去重更宽松。实现采用 design 的更严规则（fail-closed 方向；当前白名单仅 `dream`，两条 dream 声明必然重复）。
4. **receipt.surfaces 空值**：PLAN 伪码 `receipt["surfaces"] = manifest.get("surfaces", [])` 恒写该键；但 PLAN Step 6 集成测试③要求「无 surfaces 的制品 pack 产物与现状 diff 为空」。实现改为仅非空时写 `surfaces` 键（manifest/receipt 一致），满足 diff-empty 验收。
5. **迁移脚本附加动作**：仅更新 DB digest 而不注册新 digest 制品，pack 时会因 store 缺新 digest 目录失败；故脚本同时 `import_tree` 注册制品并刷新 `artifact_path`。仍只 UPDATE 既有行，无 DDL。

## TDD 过程摘要（Red → Green）

| 步骤 | 测试（`backend/tests/test_workspace_init_surfaces.py`） | Red | Green |
|------|------|-----|-------|
| Step 1/2 校验 | `ValidateSurfacesTests`（合法 dream 1 例；非法 6 组 subTest；非 dict 条目；重复声明；空列表；`load_init_profile` 解析/无 surfaces 不变/非法 fail-closed/非 list fail-closed） | ImportError（collection error） | ✅ |
| Step 4/5 物化 | `MaterializeDreamSurfaceTests`（静态文件内容与 audit step；重 pack 字节一致；README/workspace.json 均无时间戳） | ImportError | ✅ |
| Step 6 集成 | `PackerSurfacesIntegrationTests`（物化 + manifest/receipt/init_steps 透出；无 surfaces diff-empty；冻结重 pack 字节一致且透出；冻结缺 `.dream/workspace.json` fail-closed；多插件同名 surface 前者胜出 + receipt warnings + workspace.json 全量插件清单） | 4 failed | ✅ |

## 测试运行输出关键行

```
tests/test_workspace_init_surfaces.py: 17 passed, 6 subtests passed
相关既有套件（test_workspace_init / test_claude_plugin_pipeline / test_deck_chat_context /
  test_deck_plugin_admin_integration / test_deck_plugin_lock）: 71 passed, 23 subtests passed
后端全量（排除需真实 CLI/服务器的 3 个文件）: 718 passed, 1 skipped, 262 subtests passed
```

## 变更文件清单

- `plugins/ink-dream-story/.ink/workspace-init.json`（新增）
- `scripts/migrate_ink_dream_story_digest.py`（新增）
- `backend/services/claude_plugin/workspace_init.py`（SurfaceSpec/validate_surfaces/materialize_dream_surface/InitProfile.surfaces/load_init_profile 接线）
- `backend/services/claude_plugin/workspace_packer.py`（surfaces 合并与冲突警告、非冻结物化、冻结校验、manifest/receipt 透出）
- `backend/tests/test_workspace_init_surfaces.py`（新增）
- `docs/design/story-workspace/2026-08-04-dream-surface-task1-implementation-record.md`（本文件）
