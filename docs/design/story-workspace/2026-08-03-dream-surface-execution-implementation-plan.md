# Dream Surface（.dream 协议目录 + 跳转链 + 独立执行页）Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 让声明了 dream surface 的 Deck 插件在会话工作区物化 `.dream/` 协议目录，前端经 launch manifest 感知后在 Dream 提案卡片上提供跳转按钮，并新增独立执行页 `/story-workspace/runs/:storyWorkspaceRunId/execution`。

**Architecture:** 分三层：① packer 层（backend/services/claude_plugin/）扩展 workspace-init profile 的 `surfaces[]` 校验与 `.dream/` 物化，launch-manifest/receipt/会话 API 透出；② story-workspace 后端合同层扩展 surface 业务语义与指导指令审计；③ 前端层新增卡片跳转按钮与执行页。

**Tech Stack:** Python 3.11+ / FastAPI / pytest（后端，按仓库既有栈）；React + TypeScript / vitest（前端，按仓库既有栈）。

**权威设计：** `files/design_004_story-workspace-dream-surface-execution-page.md`（下称 design_004）；上游 `files/drama-forge-workspace-init-design.md`（packer 扩展插槽、profile schema）、`files/design_003_story-workspace-episodes-metadata-review.md`（Gate、审计合同）。

> **执行环境注意：** 本计划编写时无法读取主仓库源码，文件路径按设计文档的合同归属推导。执行每个 Task 前先用 `grep`/`rg` 定位真实模块（关键词已给出），若路径与计划不符，以仓库实际结构为准并同步修订本计划。

## Global Constraints

- 全部新业务符号使用 `story-workspace` / `StoryWorkspace*` 前缀（DEC-004）。
- 后端业务合同只归 `backend/story_workspace/contracts.py`；前端局部 REST 合同只归 `frontend/src/hooks/story-workspace/contracts.ts`；禁止通用 `types` 路径承载（DEC-026）。
- `backend/database.py` 只读，不新增任何 Schema / DDL（DEC-026）。
- workspace-init profile 保持 `workspace-init/v1`，`surfaces[]` 为可选字段；无 profile / 无 surfaces 的行为必须与现状完全一致（DEC-027）。
- `.dream/` 全部静态物化、运行期不回写；`workspace.json` 不含 workflow_run_id、时间戳（DEC-029）。
- 前端不探测文件系统；旧会话 payload 无 `surfaces` 字段 = 无 surface，隐藏入口（DEC-028）。
- 执行页只承接 Gate 第四步之后；未 confirmed 的 run 访问执行页必须重定向审阅深链（design_004 §5.5）。
- 不提供视频预览/上传/播放器；不做复杂画布；仅桌面端（DEC-005/006）。
- 指导消息复用发起 run 的同一 Chat thread 作传输通道，但不渲染为 Chat 会话消息（DEC-032）。

---

### Task 1: packer — `surfaces[]` 校验与 `.dream/` 物化

**Files:**
- Modify: `backend/services/claude_plugin/workspace_init.py`（若不存在则按 drama-forge-workspace-init-design §6 创建；定位关键词 `load_init_profile`、`execute_init_profile`）
- Modify: packer 主模块（定位关键词 `pack_workspace_plugins`、`launch-manifest`）
- Test: `backend/tests/services/claude_plugin/test_workspace_init_surfaces.py`

**Interfaces:**
- Consumes: 既有 `load_init_profile(packed_dir: Path) -> InitProfile | None`、`execute_init_profile(workspace, packed_dir, profile) -> list[dict]`
- Produces:
  - `SurfaceSpec`（dataclass：`name: str`、`protocol_dir: str`、`entry_route: str`）
  - `validate_surfaces(raw: list[dict]) -> list[SurfaceSpec]` — 非法抛 `WorkspacePackError("CLAUDE_PLUGIN_INIT_PROFILE_INVALID")`
  - `materialize_dream_surface(workspace: Path, deck_id: str, plugins: list[dict], entry_route: str) -> dict` — 返回 init_step 审计条目
  - `DREAM_SURFACE_README: str` — 静态模板常量
  - pack 产物：`.dream/README.md`、`.dream/workspace.json`；manifest/receipt 含 `surfaces: list[dict]`

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

- [ ] **Step 4: 写失败测试 — 物化与幂等**

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

- [ ] **Step 5: 运行确认失败 → 实现物化 → 运行确认通过**

```python
import json
from pathlib import Path

DREAM_SURFACE_README = """# .dream/ — Dream Surface 协议目录（只读）

本目录由 packer 在会话创建时物化，标识本工作区由 Dream 驱动插件加载。

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
    dream_dir = workspace / ".dream"
    dream_dir.mkdir(exist_ok=True)
    payload = {
        "schema_version": "dream-surface/v1",
        "deck_id": deck_id,
        "plugins": plugins,
        "entry_route": entry_route,
    }
    ws_file = dream_dir / "workspace.json"
    if not ws_file.exists():
        ws_file.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n")
    readme_file = dream_dir / "README.md"
    if not readme_file.exists():
        readme_file.write_text(DREAM_SURFACE_README)
    return {"step": "materialize-surface", "surface": "dream", "path": ".dream/"}
```

Run: `pytest backend/tests/services/claude_plugin/test_workspace_init_surfaces.py -v`
Expected: PASS（全部）

- [ ] **Step 6: packer 集成 + manifest/receipt 透出**

在 `pack_workspace_plugins` 的「复制制品之后、写 manifest 之前」插槽（drama-forge-workspace-init-design §6 伪码位置）加入：

```python
# 冻结工作区分支：仅校验，不重建
if frozen_workspace and merged_surfaces:
    expected = {s["protocol_dir"] for s in merged_surfaces}
    missing = [d for d in expected
               if not (workspace / d / "workspace.json").exists()]
    if missing:
        raise WorkspacePackError("CLAUDE_PLUGIN_INIT_PROFILE_INVALID")

# 非冻结分支：物化 + 收集 init_steps
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

### Task 2: 会话 API 透出 `surfaces`

**Files:**
- Modify: 会话 payload 组装模块（定位关键词 `workspace_context`、`launch-manifest.json` 读取处、`plugin-pack-receipt`）
- Test: `backend/tests/.../test_session_surfaces_payload.py`（路径随既有会话测试）

**Interfaces:**
- Consumes: Task 1 写入的 `.ink/launch-manifest.json`（含 `surfaces`）、`.ink/plugin-pack-receipt.json`（兜底）
- Produces: 会话 API payload 新增 `surfaces: list[{name, protocol_dir, entry_route}]`；无 surface 时字段缺省（不是空数组——与旧会话不可区分，前端统一按「无 surface」处理）

- [ ] **Step 1: 写失败测试**

```python
def test_session_payload_includes_surfaces_when_manifest_has_them(session_factory):
    session = session_factory(manifest_surfaces=[{
        "name": "dream", "protocol_dir": ".dream",
        "entry_route": "/story-workspace/dream",
    }])
    payload = build_session_payload(session)
    assert payload["surfaces"][0]["name"] == "dream"
    assert payload["surfaces"][0]["entry_route"] == "/story-workspace/dream"

def test_session_payload_omits_surfaces_for_legacy_sessions(session_factory):
    session = session_factory(manifest_surfaces=None)  # 旧会话：manifest 无该键
    payload = build_session_payload(session)
    assert "surfaces" not in payload

def test_session_payload_falls_back_to_receipt(session_factory):
    session = session_factory(manifest_surfaces=None,
                              receipt_surfaces=[{"name": "dream", ...}])
    payload = build_session_payload(session)
    assert payload["surfaces"][0]["name"] == "dream"
```

- [ ] **Step 2: 运行确认失败 → Step 3: 实现读取（manifest → receipt 兜底，纯 JSON 读取，无任何文件系统探测暴露给前端）→ Step 4: 运行确认通过**

```python
def load_workspace_surfaces(workspace: Path) -> list[dict] | None:
    for name in (".ink/launch-manifest.json", ".ink/plugin-pack-receipt.json"):
        f = workspace / name
        if f.exists():
            surfaces = json.loads(f.read_text()).get("surfaces")
            if surfaces:
                return surfaces
    return None
# build_session_payload 中：surfaces = load_workspace_surfaces(...)；为 None 则不写入 payload
```

- [ ] **Step 5: Commit**

```bash
git add backend/ && git commit -m "feat(sessions): expose workspace surfaces in session payload"
```

---

### Task 3: story-workspace 后端合同 — surface 业务语义 + 指导指令

**Files:**
- Modify: `backend/story_workspace/contracts.py`
- Modify: story-workspace 路由/服务模块（定位关键词 `story-workspace`、`StoryWorkspaceReviewEvent`）
- Test: `backend/tests/story_workspace/test_guidance.py`

**Interfaces:**
- Consumes: design_003 的 `StoryWorkspaceReviewEvent`、`StoryWorkspaceExecutionGateRecord` 信封
- Produces:
  - `StoryWorkspaceSurface`（值对象：name/protocol_dir/entry_route）
  - `StoryWorkspaceGuidanceCommand`（run_id、kind: `retry-step|free-text`、text、idempotency_key、actor）
  - `StoryWorkspaceExecutionProjection`（run_id、phase、steps[]、assets_ref、events[]）
  - `ReviewAction` 枚举新增 `guide`（合同层扩展，不动 DDL）
  - `POST /api/story-workspace/runs/{run_id}/guidance` — 幂等；run 非可指导状态返回 409

- [ ] **Step 1: 写失败测试**

```python
def test_guidance_accepted_when_run_continuing(client, run_factory):
    run = run_factory(status="continuing")
    resp = client.post(f"/api/story-workspace/runs/{run.id}/guidance", json={
        "kind": "free-text", "text": "第二集节奏放慢",
        "idempotency_key": "k-1", "actor": "user-1",
    })
    assert resp.status_code == 202
    events = review_events_for(run.id)
    assert events[-1].action == "guide"
    assert events[-1].actor == "user-1" and events[-1].request_id

def test_guidance_idempotent_replay(client, run_factory):
    run = run_factory(status="continuing")
    body = {"kind": "retry-step", "step_id": "s3",
            "idempotency_key": "k-2", "actor": "user-1"}
    r1 = client.post(f"/api/story-workspace/runs/{run.id}/guidance", json=body)
    r2 = client.post(f"/api/story-workspace/runs/{run.id}/guidance", json=body)
    assert r1.status_code == r2.status_code == 202
    assert len([e for e in review_events_for(run.id) if e.action == "guide"]) == 1

def test_guidance_rejected_when_not_confirmed(client, run_factory):
    run = run_factory(status="pending_review")
    resp = client.post(f"/api/story-workspace/runs/{run.id}/guidance", json={
        "kind": "free-text", "text": "x", "idempotency_key": "k-3", "actor": "user-1"})
    assert resp.status_code == 409
```

- [ ] **Step 2: 运行确认失败 → Step 3: 实现合同与端点（指导入队给执行 Agent 走既有 thread 传输通道，不写 Chat 消息表；审计写 ReviewEvent action=guide）→ Step 4: 运行确认通过**

- [ ] **Step 5: Commit**

```bash
git add backend/story_workspace/ backend/tests/story_workspace/
git commit -m "feat(story-workspace): guidance command contract and idempotent endpoint"
```

---

### Task 4: 前端 — `StoryWorkspaceSurfaceLinkButton` 与深链 run 定位

**Files:**
- Modify: `frontend/src/hooks/story-workspace/contracts.ts`（加 `StoryWorkspaceSurface`、按钮状态聚合类型）
- Modify: Dream 提案卡片组件（定位关键词 `pending proposal`、Dream JSON 合同渲染处）
- Modify: Dream 页（`?run=` 定位逻辑）
- Test: `frontend/src/components/story-workspace/__tests__/StoryWorkspaceSurfaceLinkButton.test.tsx`

**Interfaces:**
- Consumes: Task 2 的 payload `surfaces`；Task 3/既有 run 状态聚合接口
- Produces: `StoryWorkspaceSurfaceLinkButton(props: {proposalId, runId, episodeId?})`；阶段文案映射表 `SURFACE_LINK_LABELS`

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
  render(<StoryWorkspaceSurfaceLinkButton proposal={proposal({stage})} />);
  expect(screen.getByRole("link", {name: label})).toHaveAttribute("href", href);
});

it("hidden when session has no dream surface", () => {
  render(<StoryWorkspaceSurfaceLinkButton proposal={proposal({stage: "confirmed"})}
                                         surfaces={undefined} />);
  expect(screen.queryByRole("link")).toBeNull();
});

it("superseded proposal degrades to 查看最新版本", () => {
  render(<StoryWorkspaceSurfaceLinkButton proposal={proposal({superseded: true})} />);
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

- [ ] **Step 6: Commit**

```bash
git add frontend/src/ && git commit -m "feat(story-workspace): surface link button and run deep-link"
```

---

### Task 5: 前端 — 独立执行页

**Files:**
- Modify: `frontend/src/router/story-workspace.tsx`（新增路由）
- Create: `frontend/src/pages/story-workspace/StoryWorkspaceExecutionPage.tsx`
- Create: `frontend/src/components/story-workspace/StoryWorkspaceExecutionProgressTable.tsx`、`StoryWorkspaceExecutionAssetPanel.tsx`、`StoryWorkspaceGuidanceSidebar.tsx`
- Test: `frontend/src/pages/story-workspace/__tests__/StoryWorkspaceExecutionPage.test.tsx`

**Interfaces:**
- Consumes: Task 3 的 `StoryWorkspaceExecutionProjection` 与 guidance 端点；design_003 的 run/Gate 状态
- Produces: 路由 `/story-workspace/runs/:storyWorkspaceRunId/execution`；五态 UI（continuing / awaiting-guidance / completed / failed / not-confirmed）

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

- [ ] **Step 1:** 真实链路验证：Deck 绑定含 dream surface 的制品 → 发起 Chat → 工作区出现 `.dream/` 两文件、manifest/receipt/payload 三处 surfaces 一致
- [ ] **Step 2:** Agent 输出 Dream 提案 JSON → 卡片按钮六态走查（含 supersede 降级）
- [ ] **Step 3:** confirmed → 执行页 → 提交指导 → 审计事件可见且 Chat 消息流无指导消息
- [ ] **Step 4:** 旧会话（无 surfaces）回归：无按钮、无报错、payload 无该字段
- [ ] **Step 5:** 全量测试套件 + `claude plugin validate`（若制品有变更）

```bash
git add -A && git commit -m "test: dream surface end-to-end regression"
```
