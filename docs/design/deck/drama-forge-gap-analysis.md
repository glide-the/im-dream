# DramaForge 插件化差距分析 · Deck 插件初始化工作空间任务清单

> 版本：v1.0 · 2026-08-03
> 输入：`vendor/drama-forge/drama-forge`（drama-forge.zip 解压，8532 文件 / 20.3MB，含大量开发产物）
> 对照：[Claude Code 官方 plugin-marketplaces 文档](https://code.claude.com/docs/zh-CN/plugin-marketplaces)
> 参照系：本仓库已验证的 `superpowers@claude-plugins-official` 真实安装/digest/`--plugin-dir` 加载链路

---

## §0 结论（任务一：如何处理）

**drama-forge 不需要重写，但必须经过「打包改造 + marketplace 包装 + 工作区初始化协议」三步二次设计，才能进入 ink-dream-memory 现有的 Deck 插件管线。**

它已经具备插件化的好底子：`.claude-plugin/plugin.json`（v1.0.1，自定义组件路径）、hooks 全部使用 `${CLAUDE_PLUGIN_ROOT}`、12 agents / 14 skills / 6 hooks / 8 rules / 19 templates / 12 schemas 组件齐全且有 `dramaforge.manifest.yaml` 单一事实源。

但它目前是一个**项目仓库布局**而非**可分发插件包**：混入了 .venv/tests/evals/日志等开发产物；skills 内以 CWD 相对方式调用 `python3 scripts/dramaforge.py`；依赖 9 个第三方 Python 包；`.claude/settings.json` 与根 `CLAUDE.md` 是项目级配置，`--plugin-dir` 加载时不会生效；`stories/ assets/ exports/` 是运行时工作目录，必须由 Deck 对话的工作区初始化来脚手架。

---

## §1 现状清单（勘察事实）

| 维度 | 事实 |
|------|------|
| plugin manifest | `.claude-plugin/plugin.json` ✅ 存在；`agents` 显式列出 12 个 md；`skills: "./.claude/skills/"`；`hooks: "./.claude/hooks/hooks.json"` |
| marketplace | ❌ 无 `marketplace.json`，不在任何 marketplace 中 |
| hooks | 6 个 bash 脚本 + hook_lib.sh，hooks.json 全部 `${CLAUDE_PLUGIN_ROOT}` 引用 ✅；事件覆盖 SessionStart / PreToolUse(Write\|Edit, Bash) / PostToolUse |
| skills | 14 个（13 个业务 + `skill-gen` 标注 `kind: development`）；每个带 `evals/` 开发资产；frontmatter 含非标准字段（`category` `agents` `inputs` `outputs` `required_reviews`） |
| agents | 12 个 md，五条业务线（编剧/视觉/整合/守护/研究/审查） |
| 非标组件 | `.claude/rules/`（8）、`.claude/docs/`（templates 19 + genres 24 题材包 + 2 协作规则）、`schemas/story-system/`（12 个 JSON Schema）、`references/`（9 个知识库 md/json） |
| 脚本层 | `scripts/` 17 个 py（`dramaforge.py` 统一 CLI 入口：init/commit/doctor/query/retcon…），**9 个第三方依赖**：PyYAML、python-frontmatter、markdown-it-py、click、rich、jsonschema、Jinja2、rapidfuzz、watchdog |
| 运行时目录 | `stories/{project}/`、`assets/`、`exports/`、`.dramaforge/state.yaml` —— 由 skills 在工作过程中读写 |
| 项目级配置 | 根 `CLAUDE.md`（251 行主配置/设计原则/规范目录）；`.claude/settings.json`（permissions allow/deny/ask，仅服务原仓库） |
| 开发产物 | `.venv/`、`.pytest_cache/`、`tests/`（58 个测试文件）、`evals/`、`build_mode3*.log`、`todos/`、`examples/`、`__MACOSX/`、`file_manifest.json`（派生物） |
| skills 内脚本调用 | `python3 scripts/dramaforge.py doctor/commit/retcon ...` —— **CWD 相对路径**，未走 `${CLAUDE_PLUGIN_ROOT}` |

---

## §2 差距矩阵（对照官方标准）

### A. 已符合（直接可用）

| # | 项 | 说明 |
|---|-----|------|
| A1 | plugin.json 存在且字段合法 | name/version/description/author/license/keywords + 自定义组件路径（官方支持 `agents`/`skills`/`hooks` 自定义路径字段） |
| A2 | hooks 注册方式 | 独立 hooks.json + `${CLAUDE_PLUGIN_ROOT}` 引用，符合缓存复制模型 |
| A3 | 组件在插件根内 | 无运行时 `../` 越界引用（`../` 仅出现在 evals 开发脚本注释中） |
| A4 | 版本字段 | plugin.json 固定 `1.0.1`，配合我方 digest 固定策略一致 |

### B. 需打包改造（机械性工作，无设计争议）

| # | 项 | 现状 | 改造 |
|---|-----|------|------|
| B1 | 开发产物剔除 | .venv/tests/evals/logs/todos/examples/__MACOSX/.pytest_cache 约占总包体绝大部分 | 打包白名单：`.claude-plugin/ .claude/ schemas/ references/ scripts/ docs/ CLAUDE.md dramaforge.manifest.yaml pyproject.toml` |
| B2 | `skill-gen` 剔除 | `kind: development`，仅供插件作者使用 | 不进入发行包 |
| B3 | `file_manifest.json` 派生物 | 要求由 `sync_inventory.py` 生成 | 打包时重新生成并校验 `--check` |
| B4 | marketplace 包装 | 无 | 创建 `marketplaces/drama-studio/.claude-plugin/marketplace.json`，`source` 相对路径指向打包产物；本地 `claude plugin marketplace add` + `claude plugin install drama-forge@drama-studio` 走真实 CLI 验证 |
| B5 | frontmatter 非标准字段 | skills 带 category/inputs/outputs 等扩展字段 | 以 `claude plugin validate .` 实测；若报警告则保留（不阻塞），报错则收敛到 name/description 并把扩展信息移入正文 |

### C. 需二次设计（有架构决策）

| # | 项 | 问题 | 决策方向（设计稿详述） |
|---|-----|------|----------------------|
| C1 | **Python 脚本调用路径** | skills 写死 `python3 scripts/dramaforge.py ...`（CWD 相对）；`--plugin-dir` 加载时插件在缓存/制品目录，CWD 是 Agent 工作空间，`scripts/` 不存在 | 三选一：①skills 文案批量改写为 `python3 "${CLAUDE_PLUGIN_ROOT}/scripts/dramaforge.py"`；②工作区初始化时把 scripts/ 软链/复制进工作区；③packer 生成 wrapper。推荐 ①（与 hooks 同款机制，官方标准变量） |
| C2 | **Python 运行时与 9 个第三方依赖** | Agent 工作空间的 `python3` 不保证有 PyYAML/jsonschema/watchdog 等 | 工作区初始化协议增加「插件运行时准备」步骤：受管 venv（每插件 digest 固定）或宿主受管 Python 预装；hook/skill 调用统一指向该解释器 |
| C3 | **`.claude/settings.json` 权限模型** | 插件不能携带项目 settings；我方 agent runner 有自己的权限/沙箱语义 | 不生效、不打包 settings.json；把 allow/deny 意图翻译为我方 workspace 的权限策略（如允许写 stories/assets/exports，禁写插件目录） |
| C4 | **根 CLAUDE.md** | `--plugin-dir` 不会把它当项目 CLAUDE.md 加载 | 工作区初始化时由 packer 把「精简版工作区 CLAUDE.md」注入 Agent 工作空间根（内容从 drama-forge CLAUDE.md 提炼：协作协议、目录约定、事实源优先级） |
| C5 | **运行时目录脚手架** | `stories/ assets/ exports/ .dramaforge/` 是技能读写的工作区目录，不属于插件制品 | packer 在打包阶段创建空骨架 + `.gitkeep`；`drama-init` skill 的 `init_project.py` 负责项目级初始化，二者职责分离 |
| C6 | **hooks 在非交互 SDK 运行的生效性** | 我方运行时是 claude-agent-sdk + `--plugin-dir`（非交互 `-p`），SessionStart/PreToolUse/PostToolUse 是否按预期触发未验证 | 列入 P0 验证项：真实跑一次带 hooks 的 Deck 对话，观察 hook 日志与副作用（backup/state 文件） |
| C7 | **watchdog 文件监控假设** | hooks 设计假定长会话文件监控；Deck 对话是按需启动的短生命周期进程 | 降级策略：continuity_guard 改为按需扫描（PostToolUse 触发即可），不依赖常驻 watch |
| C8 | **marketplace 分发形态** | 本地目录 marketplace 只适合开发期 | 开发期：仓库内 `marketplaces/drama-studio`；生产期候选：git 仓库托管（github/url 源）或 CLAUDE_CODE_PLUGIN_SEED_DIR 预填充 |
| C9 | **Deck↔插件绑定语义** | 我方模型：Deck 只存 digest 引用，对话发起时 pack + `--plugin-dir` | drama-forge 作为「Dream 驱动插件」与 Deck 的绑定走既有 `deck_claude_plugin_refs`，无需新机制；需要新增的是「该插件要求的工作区初始化 profile」（C2/C4/C5 的声明式描述） |
| C10 | **dramaforge.manifest.yaml 事实源体系** | 其内部 sync_inventory/doctor 体系假定仓库可写 | 插件缓存只读 ⇒ doctor/sync 类命令的目标必须是工作区 stories/，而非插件目录；skills 文案需明确此边界 |

---

## §3 关键风险与决策建议

1. **最大风险是 C1+C2（脚本可执行性）**：hooks 和 skills 的能力大半挂在 `scripts/` 的 Python 工具链上。若解释器/依赖/路径任一缺失，插件"能加载但瘫痪"。建议 P0 先打通「最小闭环」：drama-init 在工作区内完整跑通一次 init_project + doctor。
2. **不要整体照搬 zip**：20MB 中绝大多数是 .venv 与测试资产。打包白名单（B1）是硬要求，否则 digest 制品仓库被污染且无关变更会震碎 digest。
3. **hooks 验证先于推广（C6）**：若 SDK 非交互模式下 hook 不触发，连续性守护/备份链全部失效，需要 fallback 设计（技能内显式调用校验脚本）。
4. **版本治理**：drama-forge 上游迭代时，plugin.json version 与 digest 双轨——version 面向用户更新语义，digest 面向我方制品不可变性，二者都进 installations 表。

---

## §4 Deck 插件初始化工作空间 · 任务清单

### P0 — 最小可行闭环（drama-forge 能在 Deck 对话里跑起来）

| ID | 任务 | 层 | 依赖 | 验收标准 |
|----|------|-----|------|---------|
| P0-1 | 打包白名单脚本：zip → 干净插件目录（剔除 B1/B2，重建 file_manifest） | 打包 | — | 产物 < 3MB；`claude plugin validate <dir>` 通过 |
| P0-2 | 仓库内本地 marketplace `marketplaces/drama-studio`（marketplace.json + 相对路径 source） | marketplace | P0-1 | `claude plugin marketplace add` + `install drama-forge@drama-studio` 真实 CLI 成功 |
| P0-3 | skills/hooks 脚本路径改造：`scripts/` → `${CLAUDE_PLUGIN_ROOT}/scripts/`（C1） | 打包 | P0-1 | grep 无裸 `python3 scripts/`；validate 通过 |
| P0-4 | 插件 Python 运行时：受管 venv 创建器（按 digest 缓存，pip 安装 requirements） | 后端 | — | 新 digest 首次 pack 时建成 venv；复用命中缓存 |
| P0-5 | 工作区初始化 profile：声明式描述 runtime 目录骨架（stories/assets/exports/.dramaforge）+ 注入版 CLAUDE.md + venv 路径（C2/C4/C5） | 后端 | P0-4 | packer 按 profile 产出工作区；receipt 记录初始化步骤 |
| P0-6 | packer 扩展：执行初始化 profile（建目录、写 CLAUDE.md、软链 venv、写入 launch manifest） | 后端 | P0-5 | 工作区含完整骨架；manifest 可审计 |
| P0-7 | hooks 生效性实测：真实 Deck 对话触发 SessionStart/PreToolUse，确认副作用文件出现（C6/C7） | 测试 | P0-6 | hook 日志/副作用可观测；不生效则产出 fallback 决策记录 |
| P0-8 | 真实 CLI 集成测试：install → pack → 工作区骨架 → `drama-init` 最小流程（init_project + doctor 通过） | 测试 | P0-7 | 测试独立可重复，证据落 output/ |

### P1 — 体验与治理

| ID | 任务 | 层 | 依赖 | 验收标准 |
|----|------|-----|------|---------|
| P1-1 | 权限策略映射：`.claude/settings.json` 意图 → 我方 workspace 权限声明（C3） | 后端 | P0-5 | stories/assets/exports 可写、插件目录只读由 runner 强制 |
| P1-2 | 工作区 CLAUDE.md 提炼版（协作协议/目录约定/事实源，中文，≤80 行） | 内容 | P0-5 | Deck 对话首轮 agent 自述遵循协议 |
| P1-3 | Deck 编辑器的插件引用 UI 标注「需工作区初始化 profile」状态 | 前端 | P0-5 | 缺 profile 的引用有明确提示 |
| P1-4 | digest/version 双轨展示：installations 与 receipt 中可见 drama-forge 版本 | 前端 | P0-2 | 设置页与对话 receipt 一致 |

### P2 — 分发与演进

| ID | 任务 | 层 | 依赖 | 验收标准 |
|----|------|-----|------|---------|
| P2-1 | marketplace 生产形态选型（git 托管 vs SEED_DIR 预填充）并落地（C8） | 运维 | P0-2 | 新机器一条命令可装 |
| P2-2 | 上游同步流程：zip/仓库更新 → 重打包 → 新 digest → Deck 引用迁移指南 | 运维 | P0-1 | 有 runbook；旧 digest 对话可回放 |
| P2-3 | `claude plugin validate` 纳入 CI（B5 结论固化） | 测试 | P0-1 | CI 红绿可查 |
| P2-4 | 非标准 frontmatter 字段治理决策落地 | 打包 | B5 | validate 输出零 error |

---

## §5 下一步

任务二（交互方案设计稿）以本文档 §2-C 系列决策为输入，重点展开：C1 路径改造方案、C2 受管 venv 设计、C4/C5 工作区初始化 profile schema、Dream 页「Deck→插件→工作区初始化→对话」的完整时序。
