# DramaForge × Deck 工作区初始化 · 交互方案设计稿

> 版本：v1.0 · 2026-08-03
> 上游输入：[drama-forge-gap-analysis.md](./drama-forge-gap-analysis.md)（差距矩阵 / P0 清单）
> 本文决策点均回链差距分析 C 编号。目标读者：任务三实现者。

---

## §1 设计目标与范围

**目标**：drama-forge 作为 Dream 的驱动插件，经打包改造后进入现有 Deck 插件管线；用户点击 Chat 发起 Deck 对话时，后端完成「插件打包 + 工作区初始化（目录骨架 / 注入 CLAUDE.md / Python 运行时）」，Agent 通过 `--plugin-dir` 加载插件，hooks 与 skills 全链路可用。

**做**：C1 路径改写、C2 受管 venv、C4 注入 CLAUDE.md、C5 目录骨架、C8 开发期本地 marketplace、P0 全部。
**不做（防范围蔓延）**：C3 权限映射的策略引擎（P1，先以 runner 既有沙箱兜底）、C7 watchdog 常驻化（降级为 PostToolUse 按需扫描，无需改动）、C9 新绑定机制（复用 deck_claude_plugin_refs）、生产期 marketplace 分发（P2）、前端新页面。

---

## §2 端到端交互时序

```
Dream 页                后端 (routers/services)              受管运行时              Agent 工作区
   │ 选 Deck（前缀匹配下拉，已联动展示 Agent）│                        │                      │
   │ 点击 Chat 发送      │                        │                      │
   │──────────────────▶│ 创建 thread（deck_id 锁定）│                     │
   │                   │ pack_workspace_plugins() │                      │
   │                   │  1. 读 deck refs（digest 固定）                   │
   │                   │  2. 校验制品 → 复制到 ─────┼─────────────────────▶│ .ink/plugins/<name@mp@digest>/
   │                   │  3. 读制品内 .ink/workspace-init.json           │
   │                   │  4. 执行初始化 profile ──┼─────────────────────▶│ stories/ assets/ exports/
   │                   │     （仅首次，冻结后不重复）│                     │ .dramaforge/ CLAUDE.md
   │                   │  5. 确保受管 venv ───────▶│ runtime store:      │
   │                   │                          │ data/claude-plugins/ │
   │                   │                          │ runtime/<digest>/venv│
   │                   │  6. 写 launch-manifest ─┼─────────────────────▶│ .ink/launch-manifest.json
   │                   │    （含 runtime.venv_dirs、init_steps）           │  （plugins + runtime + init）
   │                   │ plugin_launcher 启动 agent│                     │
   │                   │  env: PATH=<venv>/bin:… ─▶│ claude -p …          │
   │                   │  args: --plugin-dir 各槽位 │  --plugin-dir .ink/plugins/…
   │                   │                          │  hooks 触发（bash→    │
   │                   │                          │  python3=venv 解释器） │
   │ ◀─────────────────│ receipt（plugins + init_steps + venv）          │
   │ PluginReceiptBadge 展示                                                  │
```

关键不变量（沿用现有架构，不新增例外）：
- Deck 只存 digest 引用；制品不可变；工作区首次写入 manifest 后**冻结**——初始化步骤同样只执行一次，冻结工作区仅做修复性校验。
- 初始化 profile **随制品 digest 固定**（放在制品内），profile 变更 = 新 digest = 显式更新 Deck 引用，不会出现"同一 digest 两种初始化行为"。

---

## §3 打包侧设计（对应 C1 / B1~B4）

### 3.1 产物布局（仓库内，开发期本地 marketplace）

```
marketplaces/drama-studio/
└── .claude-plugin/
    └── marketplace.json          # name: drama-studio, plugins[0].source: "./plugins/drama-forge"
└── plugins/
    └── drama-forge/              # 打包产物（白名单净化后）
        ├── .claude-plugin/plugin.json
        ├── .claude/{agents,skills,hooks,rules,docs}/
        ├── .ink/workspace-init.json        # ← 新增：初始化 profile（§4）
        ├── .ink/workspace-claude.md        # ← 新增：注入工作区的 CLAUDE.md 内容（C4）
        ├── schemas/ references/ scripts/ docs/
        ├── CLAUDE.md dramaforge.manifest.yaml pyproject.toml
        └── （剔除：.venv/ tests/ evals/ todos/ examples/ logs __MACOSX/
             .pytest_cache/ skill-gen/ .claude/settings.json / .studio-architect/）
```

### 3.2 打包脚本 `scripts/pack_drama_forge.py`

输入 `vendor/drama-forge/drama-forge`，输出 §3.1 布局。规则：

| 规则 | 内容 |
|------|------|
| 白名单复制 | 仅 §3.1 列出的顶层条目；`__pycache__`/`*.pyc`/`evals/` 在 `.claude/skills/*/` 下也剔除 |
| C1 路径改写 | 对所有 `.claude/**/*.md`：``python3 scripts/`` → ``python3 "${CLAUDE_PLUGIN_ROOT}/scripts/``；`python3 scripts/dramaforge.py` 等同形一并处理；改写后 grep 断言无残留 |
| settings 剔除 | `.claude/settings.json` 不打包（C3：权限由我方 runner 兜底） |
| profile 注入 | 生成 `.ink/workspace-init.json`（§4 schema）与 `.ink/workspace-claude.md`（从源 CLAUDE.md 提炼：协作协议、目录约定、事实源边界，≤80 行） |
| 事实源刷新 | 若 `file_manifest.json` 存在则跳过（派生物不打包）；打包结束跑 `claude plugin validate` 并输出结果 |

### 3.3 marketplace.json

```json
{
  "name": "drama-studio",
  "owner": { "name": "Ink & Memory" },
  "plugins": [
    {
      "name": "drama-forge",
      "source": "./plugins/drama-forge",
      "description": "AI 短剧全流程协作系统（Dream 驱动插件）",
      "version": "1.0.1"
    }
  ]
}
```

安装走既有真实 CLI 管线：`claude plugin marketplace add ./marketplaces/drama-studio` → `POST /api/claude-plugins/install {package_spec: "drama-forge@drama-studio"}`（C8 开发期形态）。

---

## §4 工作区初始化 profile schema（对应 C2/C4/C5/C9）

位置：制品内 `.ink/workspace-init.json`（随 digest 固定）。packer 读取并校验，非法则 `WorkspacePackError("CLAUDE_PLUGIN_INIT_PROFILE_INVALID")`。

```json
{
  "schema_version": "workspace-init/v1",
  "runtime_dirs": ["stories", "assets", "exports", ".dramaforge"],
  "workspace_files": [
    { "path": "CLAUDE.md", "source": ".ink/workspace-claude.md", "mode": "create-if-missing" }
  ],
  "python": { "requirements": "scripts/requirements.txt", "min_version": "3.11" }
}
```

| 字段 | 语义 | 约束 |
|------|------|------|
| `runtime_dirs` | 在工作区根创建的空目录骨架（C5） | 相对路径；禁止 `..`/绝对路径；缺失才建，不清空已有内容 |
| `workspace_files[]` | 注入文件；`source` 相对制品根；`create-if-missing` 冻结友好（C4） | `path` 限工作区根下一层；不得覆盖 `.ink/` |
| `python.requirements` | 相对制品根的 requirements 文件；存在则触发受管 venv（C2） | 文件必须存在于制品内，参与 digest |

---

## §5 受管 Python venv（C2）

**存放**：制品外共享 store —— `data/claude-plugins/runtime/<artifact_digest>/venv/`。
**寻址键**：`artifact_digest`（requirements 已随制品固定，天然覆盖「依赖变更 → 新 venv」）+ 创建时记录 `python_version`/`requirements_sha256` 于 `<digest>/runtime-receipt.json` 以便审计。
**解释器来源**：受管 Python（与后端同策略），要求 ≥ profile.min_version。
**创建时机**：首次 pack 引用该制品的工作区时（懒创建）；成功后写 receipt；失败即 `WorkspacePackError("CLAUDE_PLUGIN_RUNTIME_FAILED")`，**不降级为系统 python3**（依赖缺失的半可用状态比明确报错更难排查）。
**注入方式**：launch manifest 增加 `runtime.venv_dirs: ["<abs path>/venv"]`；`plugin_launcher` 启动 agent 时 `env.PATH = <venv>/bin:{原PATH}` 且 `VIRTUAL_ENV=<venv>`。hooks 是 claude CLI 的子进程，继承 env，`python3` 与 shebang 均解析到 venv——**无需改写 hooks 内脚本**（C1 只改 skills 文案中的路径假设）。
**幂等**：`<digest>/venv/bin/python3` 存在且 receipt 匹配则直接复用；并发 pack 以 `<digest>.lock` 文件锁串行。

---

## §6 packer 扩展点（对应 P0-5/P0-6）

`pack_workspace_plugins` 在现有第 3 步（复制制品）之后、写 manifest 之前插入：

```
for each packed plugin:
    profile = read_and_validate(packed_dir/.ink/workspace-init.json)   # 无 profile → 跳过
    if not frozen_workspace:
        init_steps += execute_init_profile(workspace, packed_dir, profile)
        # create runtime_dirs / workspace_files(create-if-missing)
    if profile.python:
        venv = plugin_runtime.ensure_venv(artifact_digest, packed_dir, profile.python)
        venv_dirs.append(venv)
manifest["runtime"] = {"venv_dirs": venv_dirs}        # venv_dirs 非空才写
manifest["init_steps"] = init_steps                    # 审计用；receipt 同步透出
```

冻结分支（已有 manifest）：不重复 init；仅校验 manifest 中 `runtime.venv_dirs` 指向的 venv 仍存在，缺失则按 digest 重建（视为可修复的运行时缓存，不违反冻结语义——冻结的是插件版本与初始化结果，venv 是派生物）。
函数签名（新增模块 `backend/services/claude_plugin/workspace_init.py`）：

```python
def load_init_profile(packed_dir: Path) -> InitProfile | None      # 校验 + 解析
def execute_init_profile(workspace: Path, packed_dir: Path, profile: InitProfile) -> list[dict]
def ensure_plugin_venv(runtime_root: Path, digest: str, packed_dir: Path, spec: PythonSpec) -> Path
```

---

## §7 错误模型与降级

| 场景 | 行为 | 用户可见 |
|------|------|---------|
| profile JSON 非法 / 路径越界 | pack 失败 `CLAUDE_PLUGIN_INIT_PROFILE_INVALID` | 对话创建失败 + receipt 错误码 |
| venv 构建失败（网络/编译） | pack 失败 `CLAUDE_PLUGIN_RUNTIME_FAILED`；重试随下次 pack 自动发生 | 同上，附 pip 尾部日志摘要 |
| 插件无 profile | 跳过初始化，行为与现状完全一致（向后兼容 superpowers 等） | 无 |
| hooks 在 SDK 非交互下不触发（C6 待验证） | 不阻塞对话；P0-7 实测若失败，fallback = skills 文案引导 agent 显式运行校验脚本（仅改打包文案，不改架构） | receipt 记录 hook 观测结果 |
| 冻结工作区 venv 丢失 | pack 时按 digest 重建 | 无感 |

---

## §8 测试矩阵

| 层 | 用例 | 依据 |
|----|------|------|
| 单测 `test_workspace_init.py` | profile 解析/非法拒绝/路径越界拒绝；init 幂等（不覆盖已有 stories/）；venv receipt 复用与锁 | §4/§5 |
| 单测 packer 扩展 | 有/无 profile 两路；冻结工作区不重复 init；venv 缺失重建 | §6 |
| 打包脚本单测 | 白名单、C1 改写断言、settings 剔除、profile 生成 | §3 |
| 真实 CLI 集成 `test_real_cli_drama_forge.py` | marketplace add → install → 制品 digest → pack → 工作区骨架/CLAUDE.md/venv → `claude plugin validate` 制品 | P0-8 |
| e2e（顺延既有设施） | Deck 绑定 drama-forge → 发起 Dream 对话 → receipt 含 init_steps | P0-7 观察位 |

---

## §9 任务三实现顺序

1. `scripts/pack_drama_forge.py` + marketplace 布局（§3）
2. `workspace_init.py`（§4/§5）+ packer 集成（§6）+ `plugin_launcher` PATH 注入（§5）
3. 单测（§8 前 3 行）→ 真实 CLI 集成（§8 第 4 行）→ 全套件回归
