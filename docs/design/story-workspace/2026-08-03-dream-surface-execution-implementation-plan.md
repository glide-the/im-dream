# Dream Surface（.dream 协议目录 + 跳转链 + 独立执行页）Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 让声明了 dream surface 的 Deck 插件在会话工作区物理映射 `.dream/` 协议目录，前端经 `plugin-load-receipt` 端点（整文件透传 launch manifest）感知后在 Dream 审阅面板侧提供跳转按钮，并新增独立执行页 `/story-workspace/runs/:storyWorkspaceRunId/execution`。

**Architecture:** 分三层：① packer 层（backend/services/claude_plugin/）扩展 workspace-init profile 的 `surfaces[]` 校验与 `.dream/` 物理映射，launch-manifest/receipt 写入后经既有 `plugin-load-receipt` 端点透出；② story-workspace 后端合同层扩展 surface 业务语义与指导指令（`chat_message.metadata` 承载，无 DDL）；③ 前端层新增审阅面板侧跳转按钮与执行页。

**Tech Stack:** Python 3.11+ / FastAPI / pytest（后端，按仓库既有栈）；React + TypeScript / vitest（前端，按仓库既有栈）。

**权威设计：** `files/design_004_story-workspace-dream-surface-execution-page.md`（下称 design_004）；上游 `files/drama-forge-workspace-init-design.md`（packer 扩展插槽、profile schema）、`files/design_003_story-workspace-episodes-metadata-review.md`（Gate、审计合同）。

> **执行环境注意：** 本计划编写时无法读取主仓库源码，文件路径按设计文档的合同归属推导。执行每个 Task 前先用 `grep`/`rg` 定位真实模块（关键词已给出），若路径与计划不符，以仓库实际结构为准并同步修订本计划。
>
> **2026-08 术语对齐更新：** 各 Task「定位关键词」处已补充经代码核实的真实文件路径（见下方术语对照表及各 Task）；路径与计划原写不符处以真实路径为准并保留了原定位关键词。
>
> **2026-08-03 兼容性修订（任务二）：** 见审计报告 `2026-08-03-dream-surface-audit-report.md`（A1–E15）。本计划修订点：术语对照表（会话透出载体、提案可见形态）、Global Constraints（DEC-032 承载）、Task 1（A4 原子物理映射、E14 前置）、Task 2（B7：删除虚构的 `build_session_payload`，改挂既有 `plugin-load-receipt` 端点）、Task 3（D11/D12/D13：guidance 的 `chat_message.metadata` 承载与幂等）、Task 4（C9：按钮改挂审阅面板侧）、Task 5（C10：state router 参数化与 query 解析前置）、Task 6（E14 既有库 digest 迁移）。

## 术语对照表（业务术语 → 技术命名）

> 术语表已收编至唯一权威来源 **`docs/architecture/术语表.md`**（按模块分类，含实现状态与 commit 追溯）。本计划用到的 packer/`load_init_profile`/launch-manifest/pack-receipt/插件制品/会话 API 与 surfaces 透出载体/run/Gate/story-workspace 后端/Dream 页/Dream 提案可见形态/Deck 插件/ReviewEvent/guidance/`surfaces[]`/`.dream/` 等术语，见该文件 §1–§5。两条关键修订记录（保留于此以便执行者注意）：surfaces 透出载体 = 既有端点 `GET /api/claude-agent/threads/{thread_id}/plugin-load-receipt`（审计 B7）；pack 发生在会话首个 agent turn，非 thread 创建（审计 B6）。

## Global Constraints

- 全部新业务符号使用 `story-workspace` / `StoryWorkspace*` 前缀（DEC-004）。
- 后端业务合同只归 `backend/story_workspace/contracts.py`；前端局部 REST 合同只归 `frontend/src/hooks/story-workspace/contracts.ts`（文件已核实存在）；禁止通用 `types` 路径承载（DEC-026）。
- `backend/database.py` 只读，不新增任何 Schema / DDL（DEC-026）。
- workspace-init profile 保持 `workspace-init/v1`，`surfaces[]` 为可选字段；无 profile / 无 surfaces 的行为必须与现状完全一致（DEC-027）。
- `.dream/` 全部静态物理映射、运行期不回写；`workspace.json` 不含 workflow_run_id、时间戳（DEC-029）。
- 前端不探测文件系统；旧会话（及首个 agent turn pack 完成前）无 `surfaces` = 无 surface，隐藏入口；透出载体为既有 `plugin-load-receipt` 端点（DEC-028，2026-08-03 修订）。
- 执行页只承接 Gate 第四步之后；未 confirmed 的 run 访问执行页必须重定向审阅深链（design_004 §5.5）。
- 不提供视频预览/上传/播放器；不做复杂画布；仅桌面端（DEC-005/006）。
- 指导消息复用发起 run 的同一 Chat thread 作传输通道，但不渲染为 Chat 会话消息：以 `metadata.kind="story-workspace-guidance"` 标记落 `chat_message`（无 DDL），Chat 视图按 kind 过滤，幂等键作 `chat_message.id` + 服务层先查比对（DEC-032，2026-08-03 修订；审计报告 D11/D12/D13）。`awaiting-guidance` 为投影态，非 `RunStatus` 新枚举。

---

### Task 1: packer — `surfaces[]` 校验与 `.dream/` 物理映射

**Files:**
- Modify: `backend/services/claude_plugin/workspace_init.py`（已核实存在：`load_init_profile()` 位于 :87；保留定位关键词 `load_init_profile`、`execute_init_profile`）
- Modify: `backend/services/claude_plugin/workspace_packer.py`（已核实：`pack_workspace_plugins()` 位于 :100；保留定位关键词 `pack_workspace_plugins`、`launch-manifest`）
- Test: `backend/tests/services/claude_plugin/test_workspace_init_surfaces.py`

**Interfaces:**
- Consumes: 既有 `load_init_profile(packed_dir: Path) -> InitProfile | None`、`execute_init_profile(workspace, packed_dir, profile) -> list[dict]`
- Produces:
  - `SurfaceSpec`（dataclass：`name: str`、`protocol_dir: str`、`entry_route: str`）
  - `validate_surfaces(raw: list[dict]) -> list[SurfaceSpec]` — 非法抛 `WorkspacePackError("CLAUDE_PLUGIN_INIT_PROFILE_INVALID")`
  - `materialize_dream_surface(workspace: Path, deck_id: str, plugins: list[dict], entry_route: str) -> dict` — 返回 init_step 审计条目
  - `DREAM_SURFACE_README: str` — 静态模板常量
  - pack 产物：`.dream/README.md`、`.dream/workspace.json`；manifest/receipt 含 `surfaces: list[dict]`

- [ ] **Step 0（前置，E14）：内置插件 profile 与既有库 digest 迁移**

代码前置（本步先于 Step 1 排期，审计报告 §4.2 / E14）：

1. 新增 `plugins/ink-dream-story/.ink/workspace-init.json`：`schema_version: "workspace-init/v1"` + `surfaces: [{name: "dream", protocol_dir: ".dream", entry_route: "/story-workspace/dream"}]`（可选 `runtime_dirs`/`workspace_files`）。现状该目录无 `.ink/`，`load_init_profile` 返回 None、走「无 profile → 跳过」路径，**Dream surface 全链路对内置插件当前是关闭的**。
2. **digest 级联与既有库迁移（必须显式处理，防止 e2e 假阳性）**：`plugin_artifact_digest()` 对制品目录全部文件哈希（`backend/services/deck/builtin_plugin.py:28-43`），新增 profile 文件 → digest 变化 → 既有 DB 中 `deck_runtime_plugin_locks.lock_json` 的 `artifact_digest` 与 `claude_plugin_installations`/`deck_claude_plugin_refs` 已存 digest 全部过期；而 `seed_builtin_deck_plugin` 是「每库一次」INSERT（:52-62），**既有数据库不会自动重 seed**。必须二选一并写进实施记录：①提供重 seed / digest 迁移脚本（刷新 installation、ref 与 lock 的 digest）；②显式声明「仅新装库获得 surfaces，旧库接受无 surface 降级」。若不做①，Task 6 的 e2e 在旧库上会静默走无 surface 路径，属验收假阳性，必须在 e2e 前置检查中排除。**（2026-08-03 复核批注 R1：推荐选①迁移脚本——选②会让存量开发库长期无 surface，演示/回归路径分叉。）**

- [ ] **Step 1: 写失败测试 — surfaces 校验**

```python
# backend/tests/services/claude_plugin/test_workspace_init_surfaces.py
import pytest
from backend.services.claude_plugin.workspace_init import (
    validate_surfaces, WorkspacePackError,
)

def test_validate_surfaces_accepts_dream():
    specs = validate_surfaces([{
        "name": "dream",
        "protocol_dir": ".dream",
        "entry_route": "/story-workspace/dream",
    }])
    assert len(specs) == 1
    assert specs[0].name == "dream"
    assert specs[0].protocol_dir == ".dream"

@pytest.mark.parametrize("bad", [
    {"name": "evil", "protocol_dir": ".evil", "entry_route": "/story-workspace/x"},   # 未知 name
    {"name": "dream", "protocol_dir": ".ink", "entry_route": "/story-workspace/dream"},  # 保留目录
    {"name": "dream", "protocol_dir": ".editor", "entry_route": "/story-workspace/dream"},
    {"name": "dream", "protocol_dir": "dream", "entry_route": "/story-workspace/dream"},  # 无点前缀
    {"name": "dream", "protocol_dir": ".dream", "entry_route": "/other/route"},       # 越界路由
    {"name": "dream", "protocol_dir": ".a/b", "entry_route": "/story-workspace/dream"},  # 多层路径
])
def test_validate_surfaces_rejects_invalid(bad):
    with pytest.raises(WorkspacePackError, match="CLAUDE_PLUGIN_INIT_PROFILE_INVALID"):
        validate_surfaces([bad])
```

- [ ] **Step 2: 运行测试确认失败**

Run: `pytest backend/tests/services/claude_plugin/test_workspace_init_surfaces.py -v`
Expected: FAIL（`ImportError` / `validate_surfaces` 未定义）

- [ ] **Step 3: 实现校验**

```python
# backend/services/claude_plugin/workspace_init.py（追加）
import re
from dataclasses import dataclass

ALLOWED_SURFACE_NAMES = frozenset({"dream"})
RESERVED_PROTOCOL_DIRS = frozenset({".ink", ".editor", ".notion"})
PROTOCOL_DIR_RE = re.compile(r"^\.[a-z][a-z0-9-]*$")
ENTRY_ROUTE_PREFIX = "/story-workspace/"

@dataclass(frozen=True)
class SurfaceSpec:
    name: str
    protocol_dir: str
    entry_route: str

def validate_surfaces(raw: list[dict]) -> list[SurfaceSpec]:
    specs: list[SurfaceSpec] = []
    seen: set[tuple[str, str]] = set()
    for item in raw:
        name = item.get("name", "")
        pdir = item.get("protocol_dir", "")
        route = item.get("entry_route", "")
        ok = (
            name in ALLOWED_SURFACE_NAMES
            and PROTOCOL_DIR_RE.match(pdir)
            and pdir not in RESERVED_PROTOCOL_DIRS
            and route.startswith(ENTRY_ROUTE_PREFIX)
            and (name, pdir) not in seen
        )
        if not ok:
            raise WorkspacePackError("CLAUDE_PLUGIN_INIT_PROFILE_INVALID")
        seen.add((name, pdir))
        specs.append(SurfaceSpec(name=name, protocol_dir=pdir, entry_route=route))
    return specs
```

在 `load_init_profile` 的解析流程中接入：`profile.surfaces = validate_surfaces(raw.get("surfaces", []))`；`raw` 无 `surfaces` 键时得到空列表，不改变任何既有行为。

- [ ] **Step 4: 写失败测试 — 物理映射与幂等**

```python
import json
from backend.services.claude_plugin.workspace_init import materialize_dream_surface

PLUGINS = [{"package_spec": "drama-forge@drama-studio",
            "artifact_digest": "sha256:ee54", "resolved_version": "1.0.1"}]

def test_materialize_dream_surface_writes_static_files(tmp_path):
    step = materialize_dream_surface(tmp_path, "deck-1", PLUGINS, "/story-workspace/dream")
    ws = json.loads((tmp_path / ".dream" / "workspace.json").read_text())
    assert ws == {
        "schema_version": "dream-surface/v1",
        "deck_id": "deck-1",
        "plugins": PLUGINS,
        "entry_route": "/story-workspace/dream",
    }
    readme = (tmp_path / ".dream" / "README.md").read_text()
    assert "只读" in readme and "workflow_run_id" in readme  # 边界声明
    assert step["step"] == "materialize-surface" and step["surface"] == "dream"

def test_materialize_is_byte_identical_on_repack(tmp_path):
    materialize_dream_surface(tmp_path, "deck-1", PLUGINS, "/story-workspace/dream")
    first = (tmp_path / ".dream" / "workspace.json").read_bytes()
    materialize_dream_surface(tmp_path, "deck-1", PLUGINS, "/story-workspace/dream")
    assert (tmp_path / ".dream" / "workspace.json").read_bytes() == first
    assert "workflow_run_id" not in json.loads(first)  # 无 run 级事实
```

- [ ] **Step 5: 运行确认失败 → 实现物理映射 → 运行确认通过**

```python
import json, os, shutil
from pathlib import Path

DREAM_SURFACE_README = """# .dream/ — Dream Surface 协议目录（只读）

本目录由 packer 在会话首个 agent turn 的 pack 时物理映射到会话工作区，标识本工作区由 Dream 驱动插件加载。

- workspace.json：静态 launch 事实（deck_id、插件制品清单、入口路由）。
  它在 pack 后不再变化，不含 workflow_run_id 等 run 级事实。
- 运行期事实（run 状态、Gate 阶段、快照锁）一律以会话 / story-workspace
  REST API 为准，不要以本目录文件判断。
- 本目录对 Agent 只读：不要写入、修改或删除其中任何文件。
- Dream 提案输出仍走 Chat JSON 合同，不经本目录落盘。

入口路由：/story-workspace/dream
"""

def materialize_dream_surface(workspace: Path, deck_id: str,
                              plugins: list[dict], entry_route: str) -> dict:
    # 原子物理映射（2026-08-03 修订，审计报告 A4）：临时目录写全两文件 →
    # os.rename 原子就位；任一写失败 → 整个 pack 失败且不留半截 .dream/。
    # 已存在完整 .dream/ 时跳过（create-if-missing），重 pack 字节一致。
    dream_dir = workspace / ".dream"
    if (dream_dir / "workspace.json").is_file() and (dream_dir / "README.md").is_file():
        return {"step": "materialize-surface", "surface": "dream", "path": ".dream/"}
    payload = {
        "schema_version": "dream-surface/v1",
        "deck_id": deck_id,
        "plugins": plugins,
        "entry_route": entry_route,
    }
    tmp_dir = workspace / f".dream.tmp-{os.getpid()}"
    if tmp_dir.exists():
        shutil.rmtree(tmp_dir)
    tmp_dir.mkdir()
    try:
        (tmp_dir / "workspace.json").write_text(
            json.dumps(payload, ensure_ascii=False, indent=2) + "\n")
        (tmp_dir / "README.md").write_text(DREAM_SURFACE_README)
        if dream_dir.exists():
            shutil.rmtree(dream_dir)  # 清除半截目录后重建
        os.rename(tmp_dir, dream_dir)
    except Exception:
        shutil.rmtree(tmp_dir, ignore_errors=True)
        raise
    return {"step": "materialize-surface", "surface": "dream", "path": ".dream/"}
```

Run: `pytest backend/tests/services/claude_plugin/test_workspace_init_surfaces.py -v`
Expected: PASS（全部）

- [ ] **Step 6: packer 集成 + manifest/receipt 透出**

在 `pack_workspace_plugins` 的「复制制品之后、写 manifest 之前」插槽（drama-forge-workspace-init-design §6 伪码位置）加入（2026-08-03 注，审计报告 A1：**以下物理映射逻辑在逐 ref 循环结束后执行一次**——`manifest_plugins` 需全量清单，循环内物理映射会导致多插件 Deck 拿到不完整 plugins[]）：

```python
# 冻结工作区分支：仅校验，不重建
if frozen_workspace and merged_surfaces:
    expected = {s["protocol_dir"] for s in merged_surfaces}
    missing = [d for d in expected
               if not (workspace / d / "workspace.json").exists()]
    if missing:
        raise WorkspacePackError("CLAUDE_PLUGIN_INIT_PROFILE_INVALID")

# 非冻结分支：物理映射 + 收集 init_steps
for spec in merged_surfaces:           # 多插件同名 surface：pack 顺序前者胜出，
    if spec.name == "dream":           # 冲突写 receipt["warnings"]
        init_steps.append(materialize_dream_surface(
            workspace, deck_id, manifest_plugins, spec.entry_route))

manifest["surfaces"] = [asdict(s) for s in merged_surfaces]   # 空列表则不写该键
receipt["surfaces"] = manifest.get("surfaces", [])
receipt["init_steps"] = init_steps
```

集成测试（真实 CLI 链路已有设施则复用）：profile 含 surfaces 的制品 pack 后断言 ①`.dream/` 两文件存在 ②manifest/receipt 含 surfaces ③无 surfaces 的制品 pack 产物与现状 diff 为空。

- [ ] **Step 7: Commit**

```bash
git add backend/services/claude_plugin/ backend/tests/services/claude_plugin/
git commit -m "feat(claude-plugin): workspace-init surfaces[] validation and .dream materialization"
```

---

### Task 2: 前端消费 `plugin-load-receipt` 透出 `surfaces`

> 2026-08-03 兼容性修订（审计报告 B7）：原 Task 2 假设的「会话 payload 组装模块」与 `build_session_payload(session)` 接口**在代码中不存在**。既有端点 `GET /api/claude-agent/threads/{thread_id}/plugin-load-receipt`（`backend/routers/claude_agent.py:471-523`）把 `.ink/launch-manifest.json` 与 `.ink/plugin-pack-receipt.json` **整文件透传**，Task 1 一旦写入 `surfaces`，该端点**零后端改动**自动透出。本 Task 因此改为纯前端消费任务。

**Files:**
- Modify: `frontend/src/hooks/story-workspace/contracts.ts`（已核实存在；新增 `StoryWorkspaceSurface` 类型）
- Modify: 会话/thread 数据加载处（Dream 页或 ChatView 的 thread 上下文；加载 `GET /api/claude-agent/threads/{thread_id}/plugin-load-receipt` 并解析 `launch_manifest.surfaces`，兜底 `receipt.surfaces`）
- Test: `frontend/src/.../__tests__/useWorkspaceSurfaces.test.ts`（路径随既有前端 hooks 测试）

**Interfaces:**
- Consumes: 既有端点 `GET …/plugin-load-receipt` 响应 `{workspace_found, receipt, launch_manifest}`（后端零改动）
- Produces: `useWorkspaceSurfaces(threadId) -> StoryWorkspaceSurface[] | undefined`；manifest 与 receipt 均无 `surfaces` 键、或 `workspace_found: false`（thread 创建后、首个 agent turn pack 完成前，审计报告 B6）→ 返回 `undefined`（缺省 = 无 surface，不是空数组——与「有 surface 但为空」不可区分，前端统一按无 surface 隐藏入口）

- [ ] **Step 1: 写失败测试**

```tsx
it("returns surfaces from launch_manifest when present", async () => {
  mockReceiptEndpoint({workspace_found: true, launch_manifest: {
    surfaces: [{name: "dream", protocol_dir: ".dream",
                entry_route: "/story-workspace/dream"}]}});
  const {result} = renderHook(() => useWorkspaceSurfaces("t1"));
  await waitFor(() => expect(result.current?.[0].name).toBe("dream"));
});

it("falls back to receipt.surfaces", async () => { /* manifest 无键、receipt 有 → 透出 */ });

it("returns undefined for legacy sessions and pre-pack threads", async () => {
  // manifest/receipt 均无 surfaces 键 → undefined；workspace_found:false → undefined
});
```

- [ ] **Step 2: 运行确认失败 → Step 3: 实现 hook（纯 REST 消费 + manifest → receipt 兜底，无任何文件系统探测）→ Step 4: 运行确认通过**

- [ ] **Step 5: Commit**

```bash
git add frontend/src/ && git commit -m "feat(story-workspace): consume workspace surfaces via plugin-load-receipt"
```

---

### Task 3: story-workspace 后端合同 — surface 业务语义 + 指导指令

**Files:**
- Modify: `backend/story_workspace/contracts.py`（已核实存在）
- Modify: story-workspace 路由/服务模块（已核实：`backend/routers/story_workspace.py`（`story_workspace_router`，前缀 `/api/story-workspace`，注册于 `backend/server.py:1011`）、`backend/services/story_workspace/`、`backend/services/deck/story_workflow_gateway.py`（`StoryWorkflowApplicationGateway`）；保留定位关键词 `story-workspace`、`StoryWorkspaceReviewEvent`）
- Test: `backend/tests/story_workspace/test_guidance.py`

**Interfaces:**
- Consumes: design_003 的 `StoryWorkspaceReviewEvent`、`StoryWorkspaceExecutionGateRecord` 信封；`chat_message` 表（`metadata TEXT` 列与 `save_chat_message(..., metadata=...)` 均已存在，`backend/database.py:603-611`、:4249-4296）
- Produces:
  - `StoryWorkspaceSurface`（值对象：name/protocol_dir/entry_route）
  - `StoryWorkspaceGuidanceCommand`（run_id、kind: `retry-step|free-text`、text、idempotency_key、actor）
  - `StoryWorkspaceExecutionProjection`（run_id、phase、steps[]、assets_ref、events[]）
  - `ReviewAction` 枚举新增 `guide`（合同层扩展，不动 DDL）
  - `POST /api/story-workspace/runs/{run_id}/guidance` — 幂等；run 非可指导状态返回 409

> 2026-08-03 兼容性修订（审计报告 D11/D12/D13）：guidance 的无 DDL 承载 = `chat_message`：①指导以 `metadata={kind:"story-workspace-guidance", story_workspace_run_id, actor, request_id, idempotency_key, command_kind, text_summary}` 的 user 消息落库（审计字段齐全，指导历史按 `thread_id`+kind 反查）；②幂等键派生 `guide_<idempotency_key>` 作 `chat_message.id`，`INSERT OR REPLACE` 去重，**服务层先 SELECT 比对：同键同内容 → 202；同键不同内容 → 409**（纯应用层，弥补静默覆盖弱点）；③「不渲染为 Chat 消息」= Chat 视图消息消费层按 `metadata.kind` 过滤（前端改动，落点 `ChatView.tsx` 消息加载 :346 与 ChatPanel 渲染，见 Task 4 前置）；④`awaiting-guidance` 为投影态（`continuing` + 执行投影推断），非 `RunStatus` 新枚举。

- [ ] **Step 1: 写失败测试**

```python
def test_guidance_accepted_when_run_continuing(client, run_factory):
    run = run_factory(status="continuing")
    resp = client.post(f"/api/story-workspace/runs/{run.id}/guidance", json={
        "kind": "free-text", "text": "第二集节奏放慢",
        "idempotency_key": "k-1", "actor": "user-1",
    })
    assert resp.status_code == 202
    msg = guidance_messages_for(run.id)[-1]      # chat_message 按 metadata.kind 反查
    assert msg.metadata["kind"] == "story-workspace-guidance"
    assert msg.metadata["actor"] == "user-1" and msg.metadata["request_id"]

def test_guidance_idempotent_replay(client, run_factory):
    run = run_factory(status="continuing")
    body = {"kind": "retry-step", "step_id": "s3",
            "idempotency_key": "k-2", "actor": "user-1"}
    r1 = client.post(f"/api/story-workspace/runs/{run.id}/guidance", json=body)
    r2 = client.post(f"/api/story-workspace/runs/{run.id}/guidance", json=body)
    assert r1.status_code == r2.status_code == 202
    assert len(guidance_messages_for(run.id)) == 1   # 同键同内容 → 单条记录

def test_guidance_conflicting_replay_returns_409(client, run_factory):
    run = run_factory(status="continuing")
    client.post(f"/api/story-workspace/runs/{run.id}/guidance", json={
        "kind": "free-text", "text": "A", "idempotency_key": "k-3", "actor": "user-1"})
    resp = client.post(f"/api/story-workspace/runs/{run.id}/guidance", json={
        "kind": "free-text", "text": "B", "idempotency_key": "k-3", "actor": "user-1"})
    assert resp.status_code == 409                  # 同键不同内容 → 冲突可观测

def test_guidance_rejected_when_not_confirmed(client, run_factory):
    run = run_factory(status="pending_review")
    resp = client.post(f"/api/story-workspace/runs/{run.id}/guidance", json={
        "kind": "free-text", "text": "x", "idempotency_key": "k-4", "actor": "user-1"})
    assert resp.status_code == 409
```

- [ ] **Step 2: 运行确认失败 → Step 3: 实现合同与端点（指导以 `metadata.kind="story-workspace-guidance"` 标记的 user 消息落 `chat_message` 并注入同一 thread 的执行 Agent；幂等键作 message id + 服务层先查比对；审计字段承载于同一 metadata，对应 ReviewEvent action=guide 语义）→ Step 4: 运行确认通过**

（2026-08-03 复核批注 R5：注入机制为「同 thread 新 turn」——代码现状无 mid-turn 注入通道，Step 3 实现时先落实「指导消息作为新 user turn 交给同一 thread 的 runner」这条路径，再写端点其余部分。）

- [ ] **Step 5: Commit**

```bash
git add backend/story_workspace/ backend/tests/story_workspace/
git commit -m "feat(story-workspace): guidance command contract and idempotent endpoint"
```

---

### Task 4: 前端 — `StoryWorkspaceSurfaceLinkButton`（审阅面板侧）与深链 run 定位

> 2026-08-03 兼容性修订（审计报告 C9）：代码中**不存在** Chat 消息流内的「Dream 提案卡片」挂靠点（`story-workspace-output` 帧不进消息气泡，`ChatPanel.tsx:421-424`）。按钮改挂**既有审阅面板侧**（`StoryWorkspaceReviewDetail` 提案详情区 + 故事列表行操作列），不新建 Chat 卡片、不新增 Chat 域消息合同。

**Files:**
- Modify: `frontend/src/hooks/story-workspace/contracts.ts`（加 `StoryWorkspaceSurface`、按钮状态聚合类型）
- Modify: `frontend/src/components/story-workspace/layout/StoryWorkspaceReviewDetail.tsx`（已核实存在；提案详情区挂载 `StoryWorkspaceSurfaceLinkButton`）与故事列表行操作列（同一组件复用）
- Modify: Dream 页 `frontend/src/pages/story-workspace/StoryWorkspaceDreamPage.tsx`（已核实存在；路由 `/story-workspace/dream`（`STORY_WORKSPACE_PATHS.dream`）；`?run=` 定位逻辑）
- Test: `frontend/src/components/story-workspace/__tests__/StoryWorkspaceSurfaceLinkButton.test.tsx`

**Interfaces:**
- Consumes: Task 2 的 `useWorkspaceSurfaces`（`plugin-load-receipt` 透出）；Task 3/既有 run 状态聚合接口
- Produces: `StoryWorkspaceSurfaceLinkButton(props: {resourceType, resourceId, runId, episodeId?})`；阶段文案映射表 `SURFACE_LINK_LABELS`

- [ ] **Step 0（前置，审计报告 §4.2「Chat 消息过滤位」）：Chat 视图按 `metadata.kind` 过滤 guidance**

`GET /threads/{id}/messages` 全量返回消息的现状不变；在消息消费/渲染层过滤 `metadata.kind === "story-workspace-guidance"` 的消息（落点 `ChatView.tsx` 消息加载 :346 附近与 ChatPanel 渲染），保证 Task 3 落库的指导消息不出现在 Chat 气泡中。本步随 Task 4 排期，Task 6 e2e Step 3 验收。

- [ ] **Step 1: 写失败测试（可见条件 + 六态文案 + 目标路由）**

```tsx
const CASES = [
  ["pending_review", "前往 Dream 审阅", "/story-workspace/episodes/ep1/review?run=r1"],
  ["confirmed",      "进入后续执行",   "/story-workspace/runs/r1/execution"],
  ["continuing",     "查看执行进度",   "/story-workspace/runs/r1/execution"],
  ["completed",      "查看执行结果",   "/story-workspace/runs/r1/execution"],
  ["failed",         "查看失败详情",   "/story-workspace/runs/r1/execution"],
  ["rejected",       "查看审阅记录",   "/story-workspace/episodes/ep1/review?run=r1"],
] as const;

test.each(CASES)("stage %s renders %s → %s", (stage, label, href) => {
  renderReviewDetail({selection: selection({stage}), surfaces: [dreamSurface]});
  expect(screen.getByRole("link", {name: label})).toHaveAttribute("href", href);
});

it("hidden when session has no dream surface", () => {
  renderReviewDetail({selection: selection({stage: "confirmed"}),
                      surfaces: undefined});
  expect(screen.queryByRole("link")).toBeNull();
});

it("superseded proposal degrades to 查看最新版本", () => {
  renderReviewDetail({selection: selection({superseded: true}),
                      surfaces: [dreamSurface]});
  expect(screen.getByRole("link", {name: "查看最新版本"}));
});
```

- [ ] **Step 2: 运行确认失败 → Step 3: 实现组件（状态全部来自服务端聚合 props，前端不推断）→ Step 4: 运行确认通过**

- [ ] **Step 5: Dream 页 `?run=` 定位**

```ts
// Dream 页加载：const runParam = searchParams.get("run");
// runParam 存在且属于当前用户 → 设为选中 run（替代默认最新 run）；
// 不存在/无权 → toast 提示并回退默认。深链只做初始定位，不冻结选中（stale-review 沿用 design_003）。
```

（2026-08-03 复核批注 R2：本步的 query 解析先由 Dream 页局部 `URLSearchParams` 实现，Task 5 Step 0 统一收编至 router 参数化/query 解析——消除 Task 4→Task 5 的隐式跨 Task 依赖。）

- [ ] **Step 6: Commit**

```bash
git add frontend/src/ && git commit -m "feat(story-workspace): surface link button and run deep-link"
```

---

### Task 5: 前端 — 独立执行页

**Files:**
- Modify: `frontend/src/router/story-workspace.tsx`（新增路由；文件与路由常量 `STORY_WORKSPACE_PATHS.dream`（`/story-workspace/dream`）均已核实存在）
- Create: `frontend/src/pages/story-workspace/StoryWorkspaceExecutionPage.tsx`（已核实页面目录 `frontend/src/pages/story-workspace/` 存在，含 `StoryWorkspaceDreamPage.tsx` 等）
- Create: `frontend/src/components/story-workspace/StoryWorkspaceExecutionProgressTable.tsx`、`StoryWorkspaceExecutionAssetPanel.tsx`、`StoryWorkspaceGuidanceSidebar.tsx`
- Test: `frontend/src/pages/story-workspace/__tests__/StoryWorkspaceExecutionPage.test.tsx`

**Interfaces:**
- Consumes: Task 3 的 `StoryWorkspaceExecutionProjection` 与 guidance 端点；design_003 的 run/Gate 状态
- Produces: 路由 `/story-workspace/runs/:storyWorkspaceRunId/execution`；五态 UI（continuing / awaiting-guidance / completed / failed / not-confirmed；`awaiting-guidance` 为投影态，由 `continuing` + 执行投影推断，非 `RunStatus` 枚举——2026-08-03 注，审计报告 D13）

- [ ] **Step 0（前置，C10）：state router 扩展参数化匹配与 query 解析**

story-workspace 前端是自研 state router 而非 react-router（`frontend/src/router/story-workspace.tsx`）：路由 union 为封闭 `'dream' | 'stories' | 'characters' | 'scenes'`（:23），`resolveStoryWorkspacePath` 仅精确路径等值匹配（:52-67），query 完全不解析。本 Task 需要：①扩展 union 与 `STORY_WORKSPACE_PATHS`（runs execution、episodes review）；②`resolveStoryWorkspacePath` 加参数化匹配（前缀分段比较，支持 `:param` 段）；③新增 query 解析（`URLSearchParams`）以承载 `?run=`；④`replaceWithCanonicalPath`（:78-82）目前会丢弃 query，深链实现时**必须保留 `?run=`**；⑤手写 pushState/replaceState（:159-167）同步携带 query。改造集中在 `resolveStoryWorkspacePath` 单一 choke point。

- [ ] **Step 1: 写失败测试（Gate 重定向 + 五态渲染）**

```tsx
it("redirects to review deep-link when run not confirmed", () => {
  renderExecutionPage({run: {status: "pending_review", episodeId: "ep1"}});
  expect(mockNavigate).toHaveBeenCalledWith(
    "/story-workspace/episodes/ep1/review?run=r1");
});

it.each([
  ["continuing", "任务进度"],
  ["awaiting-guidance", "等待你的指导"],
  ["completed", "执行完成"],
  ["failed", "重试失败步骤"],
])("renders %s state", (status, text) => {
  renderExecutionPage({run: {status}});
  expect(screen.getByText(text)).toBeInTheDocument();
});

it("guidance submit posts idempotent command", async () => {
  renderExecutionPage({run: {status: "continuing"}});
  await user.type(screen.getByRole("textbox"), "放慢节奏");
  await user.click(screen.getByRole("button", {name: "发送指导"}));
  expect(postGuidance).toHaveBeenCalledWith("r1",
    expect.objectContaining({kind: "free-text", idempotency_key: expect.any(String)}));
});
```

- [ ] **Step 2: 运行确认失败 → Step 3: 实现页面与组件（布局：AppHeader Dream 选中 + breadcrumb + 左数据层 Tab[任务进度/资产/运行记录] + 右 360px 指导侧边栏；视觉 token 沿用 UI Design v2，无视频控件）→ Step 4: 运行确认通过**

- [ ] **Step 5: Commit**

```bash
git add frontend/src/ && git commit -m "feat(story-workspace): standalone execution page with guidance sidebar"
```

---

### Task 6: 端到端回归

- [ ] **Step 0（前置检查，E14）：** 确认 Task 1 Step 0 的 digest 迁移策略已执行：既有 DB 的 `claude_plugin_installations` / `deck_claude_plugin_refs` / `deck_runtime_plugin_locks.lock_json` 中内置插件 digest 已刷新（重 seed / 迁移脚本），或显式声明旧库无 surface 降级并在 e2e 环境使用新装库——防止旧库静默走无 surface 路径造成验收假阳性
- [ ] **Step 1:** 真实链路验证：Deck 绑定含 dream surface 的制品 → 发起 Chat（首个 agent turn 触发 pack）→ 工作区出现 `.dream/` 两文件、manifest/receipt/`plugin-load-receipt` 端点三处 surfaces 一致
- [ ] **Step 2:** Agent 输出故事产出 → 审阅面板打开 → 面板侧按钮六态走查（含 supersede 降级）
- [ ] **Step 3:** confirmed → 执行页 → 提交指导 → 审计字段（`chat_message.metadata`）可见且 Chat 消息流无指导消息气泡
- [ ] **Step 4:** 旧会话（无 surfaces）回归：无按钮、无报错、`plugin-load-receipt` 响应无该字段
- [ ] **Step 5:** 全量测试套件 + `claude plugin validate`（若制品有变更）

```bash
git add -A && git commit -m "test: dream surface end-to-end regression"
```
