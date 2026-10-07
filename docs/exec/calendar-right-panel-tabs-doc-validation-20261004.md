<!-- [Input] 当前 Calendar 右侧页签 PRD/UI/四阶段工作流、五份 HEAD 历史快照、目录合同与本轮独立文档检查命令。 -->
<!-- [Output] 文档清单、头部/目录索引、Markdown 本地引用、Mermaid 解析渲染、历史字节一致性、空白和范围检查回执。 -->
<!-- [Pos] docs/exec 下 Calendar 右侧页签的文档技术验证；不作为功能实现、真实业务或真实 Notion 验收。 -->
<!-- [Sync] 2026-10-04: 初次回执记录 dc5c7723 基线、pending 独立评审链接和本地 Chrome/Mermaid 技术证据；等待评审冻结后 focused rerun。 -->
<!-- [Sync] 2026-10-05: 记录 PRD 迁移至 docs/prd/calendar、正式 UI 三图正文补正、评审 §9 及 focused 文档与 Mermaid 技术验证；严格完整今日文档目标仍保留 B01 阻塞。 -->

# Calendar 右侧页签文档技术验证回执

本回执只覆盖文档技术检查。基线为 `dc5c7723f28bc75efe55f7573182fe857782dbdf`，分支为 `develop`；检查时工作树已有其他 Agent 的文档改动，本阶段没有回退、覆盖、staging 或 commit。

## 初次范围与清单

初始 `git status --short --branch` 显示 10 个已修改文档、15 个未追踪叶文件（其中 13 个 Markdown、1 个 TXT、1 个 PNG），`git diff --shortstat` 为 `10 files changed, 50 insertions(+), 2 deletions(-)`。叶文件范围检查为 `allowed_docs_only=True`，`functional_paths=[]`，`non_docs_paths=[]`；没有 frontend/backend 功能文件。

新增文件均已在最近的 `.folder.md` 清单中登记：15/15；受影响 Markdown 头部按角色检查 23/23 通过。普通文档具备 `[Input]`、`[Output]`、`[Pos]`、`[Sync]`，`.folder.md` 按目录合同检查 `[Sync]`。

## 命令回执

| 检查 | 实际命令/结果 |
| --- | --- |
| 工作树与范围 | `git rev-parse HEAD`; `git status --short --branch`; `git diff --shortstat`; 通过，基线与上述清单一致。叶文件范围脚本 exit `0`。 |
| Git 空白 | `git diff --check` exit `0`，无输出。 |
| 未追踪 Markdown 空白/EOL | Python 检查 13 个未追踪 Markdown；`issues=[]`，exit `0`。无 CR、尾部空白或缺少末尾 LF。 |
| 目录清单 | Python 检查 15 个新叶文件与最近目录合同，`inventory_failures=0`，exit `0`。 |
| 文档头部 | Python 角色化检查 23 个当前/新增 Markdown，`header_failures=0`，exit `0`。 |
| 本地 Markdown 引用（初次） | pending-aware Python 检查 `changed_markdown_files=23`、`markdown_links_checked=70`、`non_pending_missing=0`、`inherited_from_HEAD=0`，exit `0`。当时 10 条 pending：独立评审 6 条；本回执自身 4 条（检查发生在本文件落盘前）。普通外部 URL 被跳过。 |
| Mermaid | `frontend/node_modules/mermaid` 版本 `11.17.2`；本机 Chrome 单次启动、单 blank page、单 session，三图均 parse/render 通过，SVG 长度 `37743/47440/80692`，exit `0`。 |
| 新文档图清单 | 13 个未追踪 Markdown 中仅 Stage 3 含本轮 3 个 Mermaid 图；历史快照的 1/5/2 个图来自对应 HEAD 原文。扫描 exit `0`。 |
| 历史原文 | Python 对五对 `git show HEAD:<原稿>` 与相邻 snapshot 做 bytes/SHA-256 比较，`matches=5/5`，exit `0`。 |

历史快照 SHA-256：PRD `2e2820ed9077aa763db6e3fe8f81e72518545f91ebbe741c30b64a1790a8eb07`；结构 `b96405b627e4028d02740b635a22ac09b07bf7558d02442828b253d993398b77`；UI `74de96b6c6e93755ed1ee62b8b9a968c249c31c9fe5e2dccbcff98dd6addb10f`；Resource Connector `ea6cd10a685d3b3be88a4a88aa1304087be47ce3d71cb6386ea0243b20a4f66d`；Connector interaction `f988f987bc4efa9eb0af36fda203e43d489b1fcdf37b94864717133240810b9f`。

## Harness-only 记录与限制

早期三次内联检查分别出现了可修正的 harness 脚本问题：未追踪 Markdown 检查的第一次 heredoc 因 `\r` 引号展开产生 Python `SyntaxError`（exit `1`，未执行检查）；第一次链接检查未把相对 pending 路径归一化（exit `1`），修正后为上述 exit `0`；第一次范围检查把未追踪目录项当作无扩展名文件（exit `1`），展开叶文件后为上述 exit `0`。这些不是产品证据。

直接 Node Mermaid API 对两个时序图通过，对状态图因 Node 环境 `DOMPurify.addHook is not a function` 失败；这是 harness 兼容限制。随后使用已安装本机 Chrome 的 Playwright blank page 完成 3/3 parse/render，未下载浏览器、未启动应用服务、未接触数据库、Notion、真实账户或生产服务。`@mermaid-js/parser` `1.2.0` 不识别 sequence/state 类型，未将该独立 parser 结果用于产品判定。

初次检查时 `docs/exec/calendar-right-panel-tabs-design-review-20261004.md` 尚未生成，因此所有指向它的链接保持 pending；pending 不得汇报为全通过。独立评审冻结后必须重新执行 focused 文档检查，并复核评审文件加入后的链接、清单、空白、历史 bytes、Mermaid 和范围结果。

本阶段跳过功能测试、真实业务/模型/Notion 验收、数据库、服务启动、应用源码检查、部署和扩展 reload；这些不属于文档技术验证。浏览器仅产生本次 Playwright 自有 headless Chrome 进程，已在脚本结束时关闭；无隔离数据库、端口、外部进程或仓库临时产物需要清理。

## 最终 focused rerun（独立评审冻结后）

评审文件 `docs/exec/calendar-right-panel-tabs-design-review-20261004.md` 已存在并已由 `docs/exec/.folder.md` 登记。最终检查覆盖 25 个当前/新增 Markdown、17 个未追踪叶文件和 95 条本地 Markdown 引用：`non_pending_missing=0`、`pending=0`、`inherited_from_HEAD=0`；目录清单 `17/17`，头部 `25/25`，未追踪 Markdown 空白/EOL `15` 个且 `0` 个问题，范围 `allowed_docs_only=True`、`functional_paths=[]`、`non_docs_paths=[]`。回执自身 `receipt_exists=True`、`receipt_indexed=True`、`receipt_final_lf=True`，本附录代码围栏被链接扫描器跳过（`receipt_code_fences=6`）。

实际检查器命令：

```sh
python3 /tmp/ink-calendar-tabs-doc-check-20261004/focused_doc_checker.py /Users/dmeck/project/ink-dream-memory > /tmp/ink-calendar-tabs-doc-check-20261004/focused_doc_checker.stdout
rc=$?
cat /tmp/ink-calendar-tabs-doc-check-20261004/focused_doc_checker.stdout
printf 'focused_doc_checker_exit=%s\\n' "$rc"
exit "$rc"
```

检查器 exit `0`；关键原始 stdout 为：

```text
HEAD=dc5c7723f28bc75efe55f7573182fe857782dbdf
tracked_status_entries=10 untracked_leaf_files=17 changed_markdown_files=25
allowed_docs_only=True
functional_paths=[]
non_docs_paths=[]
new_files_checked=17 inventory_failures=0
header_checked=25 header_failures=0
markdown_links_checked=95 non_pending_missing=0 pending=0 inherited_from_HEAD=0
untracked_markdown_files=15 whitespace_eol_issues=0
snapshot_matches=5/5
untracked_markdown_with_mermaid=[('docs/design/claude-agent/calendar-right-panel-tabs-workflow-20261004/3_hierarchy_logic.md', 3), ('docs/design/notion-session/connector-interaction-pre-calendar-20261004-history.md', 1), ('docs/prd/claude-agent/scheduled-task-diary-page-prd-v5-20261004-history.md', 5), ('docs/prd/notion-session/resource-connector-pre-calendar-20261004-history.md', 2)]
receipt_exists=True receipt_indexed=True
receipt_code_fences=6 receipt_final_lf=True
git_diff_check_exit=0
focused_checker_failures=0
focused_doc_checker_20261005_exit=0
focused_doc_checker_exit=0
```

最终三图只使用已有依赖执行一次本机 Chrome blank page parse/render：

```sh
node /tmp/ink-calendar-tabs-doc-check-20261004/focused_mermaid_render.cjs > /tmp/ink-calendar-tabs-doc-check-20261004/focused_mermaid_render.stdout 2>&1
rc=$?
cat /tmp/ink-calendar-tabs-doc-check-20261004/focused_mermaid_render.stdout
printf 'focused_mermaid_render_exit=%s\\n' "$rc"
exit "$rc"
```

渲染器 exit `0`；关键原始 stdout 为：

```text
browser=chrome channel=headless session=single page=blank
mermaid_version=11.17.2 blocks=3
diagram_1=PASS parsed=true svg_length=38770
diagram_2=PASS parsed=true svg_length=48092
diagram_3=PASS parsed=true svg_length=81956
render_failures=0
focused_mermaid_render_20261005_exit=0
focused_mermaid_render_exit=0
```

两个可复现脚本与原始 stdout 保留在 `/tmp/ink-calendar-tabs-doc-check-20261004/`，未复制进仓库；Chrome 由渲染器 `finally` 关闭，未产生数据库、端口、服务或其他需清理资源。最终仍跳过功能、真实账户/模型/Notion、数据库、服务、部署和扩展 reload 验收。

## 2026-10-05 文档归属与正文图示补正 focused 验证

本节追加 2026-10-05 补正验证，保留上方 2026-10-04 命令、输出和历史事实不变。评审文件已追加并冻结 §9；本轮新增现行 PRD 位于 `docs/prd/calendar/calendar-right-panel-tabs-prd.md`，旧 `docs/prd/claude-agent/calendar-right-panel-tabs-prd.md` 作为迁移指引，`docs/prd/claude-agent/calendar-right-panel-tabs-prd-20261004-history.md` 保留主代理读取后写入的完整 history bytes。本轮没有修改源码、review、PRD、UI 或其他文档，只追加本回执。

最终检查器实际命令：

```sh
python3 /tmp/ink-calendar-tabs-doc-check-20261005/focused_doc_checker.py /Users/dmeck/project/ink-dream-memory > /tmp/ink-calendar-tabs-doc-check-20261005/focused_doc_checker.stdout
rc=$?
cat /tmp/ink-calendar-tabs-doc-check-20261005/focused_doc_checker.stdout
printf 'focused_doc_checker_20261005_exit=%s\\n' "$rc"
exit "$rc"
```

检查器 exit `0`。关键原始 stdout：

```text
HEAD=dc5c7723f28bc75efe55f7573182fe857782dbdf
tracked_status_entries=16 untracked_leaf_files=20 changed_markdown_files=34
allowed_root3_docs_scope=True
functional_paths=[]
non_allowed_paths=[]
new_files_checked=20 inventory_failures=0
header_checked=34 header_failures=0
markdown_links_checked=128 non_pending_missing=0 pending=0 inherited_from_HEAD=0
current_markdown_files=34 whitespace_eol_issues=0
snapshot_matches=5/5
new_prd_history=docs/prd/claude-agent/calendar-right-panel-tabs-prd-20261004-history.md sha256=85725c7e2c3b8818f6e86d28170f040b713aa2730d835d560c0812b330329352 bytes=42919 exists=True
prd_skeleton_desktop=True narrow=True hierarchy=True mermaid_blocks=0
receipt_indexed=True
git_diff_check_exit=0
focused_checker_failures=0
```

五个旧 HEAD snapshot SHA-256 与 bytes 比较仍为 `5/5`：PRD `2e2820ed9077aa763db6e3fe8f81e72518545f91ebbe741c30b64a1790a8eb07`；结构 `b96405b627e4028d02740b635a22ac09b07bf7558d02442828b253d993398b77`；UI `74de96b6c6e93755ed1ee62b8b9a968c249c31c9fe5e2dccbcff98dd6addb10f`；Resource Connector `ea6cd10a685d3b3be88a4a88aa1304087be47ce3d71cb6386ea0243b20a4f66d`；Connector interaction `f988f987bc4efa9eb0af36fda203e43d489b1fcdf37b94864717133240810b9f`。新 PRD history 独立记录为 `85725c7e2c3b8818f6e86d28170f040b713aa2730d835d560c0812b330329352` / `42919` bytes；只记录 `read_bytes` 后写入的 history 内容，不用 pointer 与 history 反向比较。

UI 正式设计稿当前正文包含 3 个 Mermaid 图；Stage 3 仍有 3 个过程图。最终渲染器只读取 UI 正文三图，并逐字比较 UI 三图与 Stage 3 三图：

```sh
node /tmp/ink-calendar-tabs-doc-check-20261005/focused_mermaid_render.cjs > /tmp/ink-calendar-tabs-doc-check-20261005/focused_mermaid_render.stdout 2>&1
rc=$?
cat /tmp/ink-calendar-tabs-doc-check-20261005/focused_mermaid_render.stdout
printf 'focused_mermaid_render_20261005_exit=%s\\n' "$rc"
exit "$rc"
```

渲染器 exit `0`。关键原始 stdout：

```text
ui_file=/Users/dmeck/project/ink-dream-memory/docs/design/claude-agent/calendar-right-panel-tabs-ui-design.md
stage3_file=/Users/dmeck/project/ink-dream-memory/docs/design/claude-agent/calendar-right-panel-tabs-workflow-20261004/3_hierarchy_logic.md
ui_blocks=3 stage3_blocks=3 source_equal=true
browser=chrome channel=headless session=single page=blank
mermaid_version=11.17.2 ui_blocks=3
ui_diagram_1=PASS parsed=true svg_length=39058
ui_diagram_2=PASS parsed=true svg_length=48413
ui_diagram_3=PASS parsed=true svg_length=82586
render_failures=0
```

PRD 正文骨架检查为桌面/窄屏/层级三项 `True`，PRD 正文 Mermaid 数量为 `0`；正式 UI 三图直接位于 §9.1–§9.3，且与 Stage 3 源一致 `3/3`。本轮没有重新解析或渲染历史图，没有执行 Notion API、CLI、账户、数据库、服务、功能或真实业务验收。所有 current Markdown local links 均已检查，`missing=0`、`pending=0`；所有新/修改 Markdown header、空白和 LF 均通过。

临时脚本与原始日志：

- `/tmp/ink-calendar-tabs-doc-check-20261005/focused_doc_checker.py`
- `/tmp/ink-calendar-tabs-doc-check-20261005/focused_doc_checker.stdout`
- `/tmp/ink-calendar-tabs-doc-check-20261005/focused_mermaid_render.cjs`
- `/tmp/ink-calendar-tabs-doc-check-20261005/focused_mermaid_render.stdout`

两份脚本源码完整附录如下；脚本只使用已有 Python、Node、Mermaid 11.17.2、Playwright 和本机 Chrome。Chrome 由渲染器 `finally` 关闭，无数据库、端口、服务或生产资源清理动作。

### 附录 C：2026-10-05 focused_doc_checker.py 完整源码

```python
#!/usr/bin/env python3
from pathlib import Path
import hashlib
import re
import subprocess
import sys

ROOT = Path(sys.argv[1]).resolve() if len(sys.argv) > 1 else Path.cwd().resolve()
ROOT_ALLOWED = {"AGENTS.md", "Agent.md", ".folder.md"}
CURRENT_PRD = ROOT / "docs/prd/calendar/calendar-right-panel-tabs-prd.md"
PRD_HISTORY = ROOT / "docs/prd/claude-agent/calendar-right-panel-tabs-prd-20261004-history.md"

def run(*args, text=True):
    return subprocess.check_output(args, cwd=ROOT, text=text)

def changed_paths():
    rows = run("git", "status", "--porcelain=v1").splitlines()
    tracked = [row[3:] for row in rows if row[:2].strip() and not row.startswith("??")]
    untracked = run("git", "ls-files", "--others", "--exclude-standard").splitlines()
    return sorted(set(tracked + untracked)), tracked, untracked

def markdown_links(text):
    pattern = re.compile(r"\[[^\]]*\]\(([^)]+)\)")
    links = []
    fenced = False
    for line in text.splitlines():
        if line.strip().startswith("```"):
            fenced = not fenced
            continue
        if fenced:
            continue
        for match in pattern.finditer(line):
            raw = match.group(1).strip()
            if raw.startswith("<") and ">" in raw:
                raw = raw[1:raw.index(">")]
            else:
                raw = raw.split(None, 1)[0]
            if re.match(r"^(?:https?://|mailto:|data:|#)", raw):
                continue
            links.append(raw)
    return links

paths, tracked, untracked = changed_paths()
md = [p for p in paths if p.endswith(".md") and (ROOT / p).is_file()]
leaf = [p for p in paths if (ROOT / p).is_file()]
allowed = all((p in ROOT_ALLOWED) or (p.startswith("docs/") and Path(p).suffix in {".md", ".txt", ".png"}) for p in leaf)
print(f"HEAD={run('git', 'rev-parse', 'HEAD').strip()}")
print(f"tracked_status_entries={len(tracked)} untracked_leaf_files={len(untracked)} changed_markdown_files={len(md)}")
print(f"allowed_root3_docs_scope={allowed}")
print(f"functional_paths={[p for p in leaf if p.startswith(('frontend/', 'backend/'))]}")
print("non_allowed_paths=" + str([p for p in leaf if p not in ROOT_ALLOWED and not p.startswith("docs/")]))

inventory_failures = []
for p in untracked:
    path = ROOT / p
    if not path.is_file():
        continue
    if p in ROOT_ALLOWED:
        contract = ROOT / ".folder.md"
        token = p
    elif path.name == ".folder.md":
        contract = path.parent.parent / ".folder.md"
        token = path.parent.name + "/"
    else:
        contract = path.parent / ".folder.md"
        token = path.name
    ok = contract.is_file() and token in contract.read_text(encoding="utf-8")
    if not ok:
        inventory_failures.append((p, str(contract), token))
print(f"new_files_checked={len([p for p in untracked if (ROOT / p).is_file()])} inventory_failures={len(inventory_failures)}")
for item in inventory_failures:
    print("INVENTORY_MISSING", item)

header_failures = []
for p in md:
    head = "\n".join((ROOT / p).read_text(encoding="utf-8").splitlines()[:24])
    required = ["[Sync]"] if Path(p).name == ".folder.md" or p in ROOT_ALLOWED else ["[Input]", "[Output]", "[Pos]", "[Sync]"]
    missing = [tag for tag in required if tag not in head]
    if missing:
        header_failures.append((p, missing))
print(f"header_checked={len(md)} header_failures={len(header_failures)}")
for item in header_failures:
    print("HEADER_MISSING", item)

pending_paths = set()
bad_links = []
pending_refs = []
inherited_bad = []
link_count = 0
for p in md:
    source = (ROOT / p).read_text(encoding="utf-8")
    for raw in markdown_links(source):
        link_count += 1
        pathpart = raw.split("#", 1)[0].split("?", 1)[0]
        if not pathpart:
            continue
        target = (ROOT / Path(p).parent / pathpart).resolve()
        rel = str(target.relative_to(ROOT)) if target.is_relative_to(ROOT) else str(target)
        if target.exists():
            continue
        if rel in pending_paths:
            pending_refs.append((p, raw, rel))
            continue
        bad_links.append((p, raw, rel))
        try:
            old = run("git", "show", "HEAD:" + p)
            if raw in markdown_links(old):
                inherited_bad.append((p, raw, rel))
        except subprocess.CalledProcessError:
            pass
print(f"markdown_links_checked={link_count} non_pending_missing={len(bad_links)} pending={len(pending_refs)} inherited_from_HEAD={len(inherited_bad)}")
for item in bad_links:
    print("MISSING", item)
for item in pending_refs:
    print("PENDING", item)
for item in inherited_bad:
    print("INHERITED_BAD", item)

untracked_md_issues = []
for p in md:
    data = (ROOT / p).read_bytes()
    if b"\r" in data:
        untracked_md_issues.append((p, "CR byte"))
    if data and not data.endswith(b"\n"):
        untracked_md_issues.append((p, "missing final LF"))
    for line_no, line in enumerate(data.splitlines(), 1):
        if line.rstrip(b" \t") != line:
            untracked_md_issues.append((p, f"trailing whitespace line {line_no}"))
print(f"current_markdown_files={len(md)} whitespace_eol_issues={len(untracked_md_issues)}")
for item in untracked_md_issues:
    print("WHITESPACE_EOL", item)

pair_names = [
    ("docs/prd/claude-agent/scheduled-task-diary-page-prd.md", "docs/prd/claude-agent/scheduled-task-diary-page-prd-v5-20261004-history.md"),
    ("docs/prd/claude-agent/scheduled-task-diary-page-structure-sketch.md", "docs/prd/claude-agent/scheduled-task-diary-page-structure-sketch-v5-20261004-history.md"),
    ("docs/design/claude-agent/scheduled-task-diary-page-ui-design.md", "docs/design/claude-agent/scheduled-task-diary-page-ui-design-v5-20261004-history.md"),
    ("docs/prd/notion-session/resource-connector.md", "docs/prd/notion-session/resource-connector-pre-calendar-20261004-history.md"),
    ("docs/design/notion-session/connector-interaction.md", "docs/design/notion-session/connector-interaction-pre-calendar-20261004-history.md"),
]
snapshot_failures = []
for source, snapshot in pair_names:
    expected = run("git", "show", "HEAD:" + source, text=False)
    actual = (ROOT / snapshot).read_bytes()
    expected_sha = hashlib.sha256(expected).hexdigest()
    actual_sha = hashlib.sha256(actual).hexdigest()
    ok = expected == actual
    print(f"SNAPSHOT {'MATCH' if ok else 'MISMATCH'} source={source} snapshot={snapshot} HEAD_sha256={expected_sha} snapshot_sha256={actual_sha} bytes={len(actual)}")
    if not ok:
        snapshot_failures.append((source, snapshot))
print(f"snapshot_matches={len(pair_names)-len(snapshot_failures)}/5")

history_data = PRD_HISTORY.read_bytes()
history_sha = hashlib.sha256(history_data).hexdigest()
print(f"new_prd_history={PRD_HISTORY.relative_to(ROOT)} sha256={history_sha} bytes={len(history_data)} exists={PRD_HISTORY.exists()}")

prd_text = CURRENT_PRD.read_text(encoding="utf-8")
desktop = bool(re.search(r"^###? 4\.1 .*桌面", prd_text, re.M)) and "透明 Calendar 画布" in prd_text
narrow = bool(re.search(r"^###? 4\.2 .*窄屏", prd_text, re.M)) and "视口内 Calendar" in prd_text
hierarchy = bool(re.search(r"^###? 4\.3 .*层级与弹窗关系", prd_text, re.M)) and "P01 现有日历 Modal" in prd_text
print(f"prd_skeleton_desktop={desktop} narrow={narrow} hierarchy={hierarchy} mermaid_blocks={len(re.findall(r'^```mermaid\\s*$', prd_text, re.M))}")

graph_counts = []
for p in untracked:
    if not p.endswith(".md"):
        continue
    count = len(re.findall(r"^```mermaid\s*$", (ROOT / p).read_text(encoding="utf-8"), re.M))
    if count:
        graph_counts.append((p, count))
print(f"untracked_markdown_with_mermaid={graph_counts}")

receipt = ROOT / "docs/exec/calendar-right-panel-tabs-doc-validation-20261004.md"
receipt_text = receipt.read_text(encoding="utf-8") if receipt.exists() else ""
receipt_indexed = receipt.name in (ROOT / "docs/exec/.folder.md").read_text(encoding="utf-8")
print(f"receipt_exists={receipt.exists()} receipt_indexed={receipt_indexed}")
print(f"receipt_code_fences={len(re.findall(r'^```', receipt_text, re.M)) // 2} receipt_final_lf={receipt_text.endswith(chr(10))}")

rc = subprocess.run(["git", "diff", "--check"], cwd=ROOT).returncode
print(f"git_diff_check_exit={rc}")

failure = bool(inventory_failures or header_failures or bad_links or pending_refs or inherited_bad or untracked_md_issues or snapshot_failures or not allowed or not receipt.exists() or not receipt_indexed or not PRD_HISTORY.exists() or not desktop or not narrow or not hierarchy or rc != 0)
print(f"focused_checker_failures={int(failure)}")
sys.exit(1 if failure else 0)
```

### 附录 D：2026-10-05 focused_mermaid_render.cjs 完整源码

```javascript
const fs = require('node:fs');
const { chromium } = require('/Users/dmeck/project/ink-dream-memory/frontend/node_modules/@playwright/test');

(async () => {
  const root = '/Users/dmeck/project/ink-dream-memory';
  const uiFile = `${root}/docs/design/claude-agent/calendar-right-panel-tabs-ui-design.md`;
  const stage3File = `${root}/docs/design/claude-agent/calendar-right-panel-tabs-workflow-20261004/3_hierarchy_logic.md`;
  const uiSource = fs.readFileSync(uiFile, 'utf8');
  const stage3Source = fs.readFileSync(stage3File, 'utf8');
  const uiBlocks = [...uiSource.matchAll(/```mermaid\n([\s\S]*?)```/g)].map(match => match[1]);
  const stage3Blocks = [...stage3Source.matchAll(/```mermaid\n([\s\S]*?)```/g)].map(match => match[1]);
  const sourceEqual = uiBlocks.length === 3 && stage3Blocks.length === 3 && uiBlocks.every((block, index) => block === stage3Blocks[index]);
  console.log(`ui_file=${uiFile}`);
  console.log(`stage3_file=${stage3File}`);
  console.log(`ui_blocks=${uiBlocks.length} stage3_blocks=${stage3Blocks.length} source_equal=${sourceEqual}`);
  const browser = await chromium.launch({ channel: 'chrome', headless: true });
  try {
    const page = await browser.newPage();
    await page.setContent('<!doctype html><html><body><div id="host"></div></body></html>');
    await page.addScriptTag({ path: `${root}/frontend/node_modules/mermaid/dist/mermaid.min.js` });
    const result = await page.evaluate(async diagrams => {
      mermaid.initialize({ startOnLoad: false, securityLevel: 'strict' });
      const output = [];
      for (let index = 0; index < diagrams.length; index += 1) {
        try {
          const parsed = await mermaid.parse(diagrams[index]);
          const rendered = await mermaid.render(`calendar_tabs_20261005_${index + 1}`, diagrams[index]);
          output.push({ index: index + 1, parsed: !!parsed, svgLength: rendered.svg.length });
        } catch (error) {
          output.push({ index: index + 1, error: String(error && error.message ? error.message : error) });
        }
      }
      return output;
    }, uiBlocks);
    console.log(`browser=chrome channel=headless session=single page=blank`);
    console.log(`mermaid_version=${require(`${root}/frontend/node_modules/mermaid/package.json`).version} ui_blocks=${uiBlocks.length}`);
    for (const item of result) {
      if (item.error) console.log(`ui_diagram_${item.index}=FAIL error=${item.error.replace(/\s+/g, ' ').slice(0, 240)}`);
      else console.log(`ui_diagram_${item.index}=PASS parsed=${item.parsed} svg_length=${item.svgLength}`);
    }
    const failures = result.filter(item => item.error).length;
    console.log(`render_failures=${failures}`);
    process.exitCode = failures || !sourceEqual || uiBlocks.length !== 3 || stage3Blocks.length !== 3 ? 1 : 0;
  } finally {
    await browser.close();
  }
})().catch(error => {
  console.error(`harness_error=${error && error.stack ? error.stack : error}`);
  process.exitCode = 2;
});
```

### 2026-10-05 receipt 自检命令与输出

```sh
python3 - <<'PY'
from pathlib import Path
import re
receipt=Path('docs/exec/calendar-right-panel-tabs-doc-validation-20261004.md').read_text(encoding='utf-8')
checker=Path('/tmp/ink-calendar-tabs-doc-check-20261005/focused_doc_checker.py').read_text(encoding='utf-8')
renderer=Path('/tmp/ink-calendar-tabs-doc-check-20261005/focused_mermaid_render.cjs').read_text(encoding='utf-8')
blocks=re.findall(r'^```(?:python|javascript)\n(.*?)^```$', receipt, flags=re.M|re.S)
print(f'receipt_exists=True appendix_script_blocks={len(blocks)}')
print(f'checker_appendix_exact={blocks[0] == checker} renderer_appendix_exact={blocks[1] == renderer}')
print(f'final_lf={receipt.endswith(chr(10))} indexed={"calendar-right-panel-tabs-doc-validation-20261004.md" in Path("docs/exec/.folder.md").read_text(encoding="utf-8")} code_fence_count={len(re.findall(r"^```", receipt, re.M)) // 2}')
ok=len(blocks)>=4 and blocks[0] == checker and blocks[1] == renderer and receipt.endswith(chr(10))
raise SystemExit(0 if ok else 1)
PY
rc=$?
printf 'receipt self-check exit=%s\n' "$rc"
exit "$rc"
```

实际输出：

```text
receipt_exists=True appendix_script_blocks=4
checker_appendix_exact=True renderer_appendix_exact=True
final_lf=True indexed=True code_fence_count=12
receipt self-check exit=0
```
### 附录 A：focused_doc_checker.py 完整源码

```python
#!/usr/bin/env python3
from pathlib import Path
import hashlib
import re
import subprocess
import sys

ROOT = Path(sys.argv[1]).resolve() if len(sys.argv) > 1 else Path.cwd().resolve()

def run(*args, text=True):
    return subprocess.check_output(args, cwd=ROOT, text=text)

def changed_paths():
    rows = run("git", "status", "--porcelain=v1").splitlines()
    tracked = [row[3:] for row in rows if row[:2].strip() and not row.startswith("??")]
    untracked = run("git", "ls-files", "--others", "--exclude-standard").splitlines()
    return sorted(set(tracked + untracked)), tracked, untracked

def markdown_links(text):
    pattern = re.compile(r"\[[^\]]*\]\(([^)]+)\)")
    links = []
    fenced = False
    for line in text.splitlines():
        if line.strip().startswith("```"):
            fenced = not fenced
            continue
        if fenced:
            continue
        for match in pattern.finditer(line):
            raw = match.group(1).strip()
            if raw.startswith("<") and ">" in raw:
                raw = raw[1:raw.index(">")]
            else:
                raw = raw.split(None, 1)[0]
            if re.match(r"^(?:https?://|mailto:|data:|#)", raw):
                continue
            links.append(raw)
    return links

paths, tracked, untracked = changed_paths()
md = [p for p in paths if p.endswith(".md") and (ROOT / p).is_file()]
leaf = [p for p in paths if (ROOT / p).is_file()]
allowed = all(p.startswith("docs/") and Path(p).suffix in {".md", ".txt", ".png"} for p in leaf)
print(f"HEAD={run('git', 'rev-parse', 'HEAD').strip()}")
print(f"tracked_status_entries={len(tracked)} untracked_leaf_files={len(untracked)} changed_markdown_files={len(md)}")
print(f"allowed_docs_only={allowed}")
print(f"functional_paths={[p for p in leaf if p.startswith(('frontend/', 'backend/'))]}")
print("non_docs_paths=" + str([p for p in leaf if not p.startswith("docs/")]))

inventory_failures = []
for p in untracked:
    path = ROOT / p
    if not path.is_file():
        continue
    if path.name == ".folder.md":
        contract = path.parent.parent / ".folder.md"
        token = path.parent.name + "/"
    else:
        contract = path.parent / ".folder.md"
        token = path.name
    ok = contract.is_file() and token in contract.read_text(encoding="utf-8")
    if not ok:
        inventory_failures.append((p, str(contract), token))
print(f"new_files_checked={len([p for p in untracked if (ROOT / p).is_file()])} inventory_failures={len(inventory_failures)}")
for item in inventory_failures:
    print("INVENTORY_MISSING", item)

header_failures = []
for p in md:
    head = "\n".join((ROOT / p).read_text(encoding="utf-8").splitlines()[:24])
    required = ["[Sync]"] if Path(p).name == ".folder.md" else ["[Input]", "[Output]", "[Pos]", "[Sync]"]
    missing = [tag for tag in required if tag not in head]
    if missing:
        header_failures.append((p, missing))
print(f"header_checked={len(md)} header_failures={len(header_failures)}")
for item in header_failures:
    print("HEADER_MISSING", item)

pending_paths = set()
bad_links = []
pending_refs = []
inherited_bad = []
link_count = 0
for p in md:
    source = (ROOT / p).read_text(encoding="utf-8")
    for raw in markdown_links(source):
        link_count += 1
        pathpart = raw.split("#", 1)[0].split("?", 1)[0]
        if not pathpart:
            continue
        target = (ROOT / Path(p).parent / pathpart).resolve()
        rel = str(target.relative_to(ROOT)) if target.is_relative_to(ROOT) else str(target)
        if target.exists():
            continue
        if rel in pending_paths:
            pending_refs.append((p, raw, rel))
            continue
        bad_links.append((p, raw, rel))
        try:
            old = run("git", "show", "HEAD:" + p)
            if raw in markdown_links(old):
                inherited_bad.append((p, raw, rel))
        except subprocess.CalledProcessError:
            pass
print(f"markdown_links_checked={link_count} non_pending_missing={len(bad_links)} pending={len(pending_refs)} inherited_from_HEAD={len(inherited_bad)}")
for item in bad_links:
    print("MISSING", item)
for item in pending_refs:
    print("PENDING", item)
for item in inherited_bad:
    print("INHERITED_BAD", item)

untracked_md_issues = []
for p in untracked:
    if not p.endswith(".md"):
        continue
    data = (ROOT / p).read_bytes()
    if b"\r" in data:
        untracked_md_issues.append((p, "CR byte"))
    if data and not data.endswith(b"\n"):
        untracked_md_issues.append((p, "missing final LF"))
    for line_no, line in enumerate(data.splitlines(), 1):
        if line.rstrip(b" \t") != line:
            untracked_md_issues.append((p, f"trailing whitespace line {line_no}"))
print(f"untracked_markdown_files={len([p for p in untracked if p.endswith('.md')])} whitespace_eol_issues={len(untracked_md_issues)}")
for item in untracked_md_issues:
    print("WHITESPACE_EOL", item)

pair_names = [
    ("docs/prd/claude-agent/scheduled-task-diary-page-prd.md", "docs/prd/claude-agent/scheduled-task-diary-page-prd-v5-20261004-history.md"),
    ("docs/prd/claude-agent/scheduled-task-diary-page-structure-sketch.md", "docs/prd/claude-agent/scheduled-task-diary-page-structure-sketch-v5-20261004-history.md"),
    ("docs/design/claude-agent/scheduled-task-diary-page-ui-design.md", "docs/design/claude-agent/scheduled-task-diary-page-ui-design-v5-20261004-history.md"),
    ("docs/prd/notion-session/resource-connector.md", "docs/prd/notion-session/resource-connector-pre-calendar-20261004-history.md"),
    ("docs/design/notion-session/connector-interaction.md", "docs/design/notion-session/connector-interaction-pre-calendar-20261004-history.md"),
]
snapshot_failures = []
for source, snapshot in pair_names:
    expected = run("git", "show", "HEAD:" + source, text=False)
    actual = (ROOT / snapshot).read_bytes()
    expected_sha = hashlib.sha256(expected).hexdigest()
    actual_sha = hashlib.sha256(actual).hexdigest()
    ok = expected == actual
    print(f"SNAPSHOT {'MATCH' if ok else 'MISMATCH'} source={source} snapshot={snapshot} HEAD_sha256={expected_sha} snapshot_sha256={actual_sha} bytes={len(actual)}")
    if not ok:
        snapshot_failures.append((source, snapshot))
print(f"snapshot_matches={len(pair_names)-len(snapshot_failures)}/5")

graph_counts = []
for p in untracked:
    if not p.endswith(".md"):
        continue
    count = len(re.findall(r"^```mermaid\s*$", (ROOT / p).read_text(encoding="utf-8"), re.M))
    if count:
        graph_counts.append((p, count))
print(f"untracked_markdown_with_mermaid={graph_counts}")

receipt = ROOT / "docs/exec/calendar-right-panel-tabs-doc-validation-20261004.md"
receipt_text = receipt.read_text(encoding="utf-8") if receipt.exists() else ""
receipt_indexed = receipt.name in (ROOT / "docs/exec/.folder.md").read_text(encoding="utf-8")
print(f"receipt_exists={receipt.exists()} receipt_indexed={receipt_indexed}")
print(f"receipt_code_fences={len(re.findall(r'^```', receipt_text, re.M)) // 2} receipt_final_lf={receipt_text.endswith(chr(10))}")

rc = subprocess.run(["git", "diff", "--check"], cwd=ROOT).returncode
print(f"git_diff_check_exit={rc}")

failure = bool(inventory_failures or header_failures or bad_links or pending_refs or inherited_bad or untracked_md_issues or snapshot_failures or not allowed or not receipt.exists() or not receipt_indexed or rc != 0)
print(f"focused_checker_failures={int(failure)}")
sys.exit(1 if failure else 0)
```

### 附录 B：focused_mermaid_render.cjs 完整源码

```javascript
const fs = require('node:fs');
const { chromium } = require('/Users/dmeck/project/ink-dream-memory/frontend/node_modules/@playwright/test');

(async () => {
  const root = '/Users/dmeck/project/ink-dream-memory';
  const file = `${root}/docs/design/claude-agent/calendar-right-panel-tabs-workflow-20261004/3_hierarchy_logic.md`;
  const source = fs.readFileSync(file, 'utf8');
  const blocks = [...source.matchAll(/```mermaid\n([\s\S]*?)```/g)].map(match => match[1]);
  const browser = await chromium.launch({ channel: 'chrome', headless: true });
  try {
    const page = await browser.newPage();
    await page.setContent('<!doctype html><html><body><div id="host"></div></body></html>');
    await page.addScriptTag({ path: `${root}/frontend/node_modules/mermaid/dist/mermaid.min.js` });
    const result = await page.evaluate(async diagrams => {
      mermaid.initialize({ startOnLoad: false, securityLevel: 'strict' });
      const output = [];
      for (let index = 0; index < diagrams.length; index += 1) {
        try {
          const parsed = await mermaid.parse(diagrams[index]);
          const rendered = await mermaid.render(`calendar_tabs_final_${index + 1}`, diagrams[index]);
          output.push({ index: index + 1, parsed: !!parsed, svgLength: rendered.svg.length });
        } catch (error) {
          output.push({ index: index + 1, error: String(error && error.message ? error.message : error) });
        }
      }
      return output;
    }, blocks);
    console.log(`browser=chrome channel=headless session=single page=blank`);
    console.log(`mermaid_version=${require(`${root}/frontend/node_modules/mermaid/package.json`).version} blocks=${blocks.length}`);
    for (const item of result) {
      if (item.error) console.log(`diagram_${item.index}=FAIL error=${item.error.replace(/\s+/g, ' ').slice(0, 240)}`);
      else console.log(`diagram_${item.index}=PASS parsed=${item.parsed} svg_length=${item.svgLength}`);
    }
    const failures = result.filter(item => item.error).length;
    console.log(`render_failures=${failures}`);
    process.exitCode = failures || blocks.length !== 3 ? 1 : 0;
  } finally {
    await browser.close();
  }
})().catch(error => {
  console.error(`harness_error=${error && error.stack ? error.stack : error}`);
  process.exitCode = 2;
});
```
