# Dream 工作台资产协作合同

本文件定义用户通过 Dream Agent 协作修改人物、场景、道具和分镜时必须执行的文件操作。它随
Dream thread 工作区部署，由宿主维护并在每个 Dream turn 前刷新。Agent 必须读取本文件，
但不得修改本文件或任何 `.dream/**` 内容。

## 操作原则

1. 用户提出新增、修改、删除人物、场景、道具或分镜时，目标是当前工作台的 canonical 文件；
   必须使用 Read、Write、Edit 等内建文件工具真正完成文件变更，不能只返回 JSON、代码块、
   建议或待确认提案。
2. 开始写入前，先读取 `.dream/WORKBENCH.md`、本文件和本次变更涉及的现有 canonical 文件。
3. 只修改用户请求涉及的资产。保留未点名资产、已有丰富字段和 Project/Episode 身份。
4. 内建文件工具写 canonical 工作台；不得用 Bash、通用 shell 或 MCP 修改 `.dream/**`。
   Story Workspace MCP 是可选预览/校验工具，不是完成变更或宿主同步的必要条件。
5. Deck voice 或普通 Chat 的结构化回复格式只能约束最终文字说明，不能替代 Dream 文件操作。
   文件写入成功后，用简短自然语言说明实际变更；不要把完整资产重新输出为 standalone JSON。

## Canonical 路径

```text
assets/
  characters/*.{md,yaml,yml}
  scenes/*.{md,yaml,yml}
  props/*.{md,yaml,yml}
stories/<project-slug>/
  project.yaml
  episodes/<EPxx>/
    episode-outline.md
    script.md
    storyboard.yaml
    review-report.md
```

当前唯一 Project、已有 Episode 和上述路径的实际绝对根目录以 `.dream/WORKBENCH.md` 为准。
不得猜测另一个 project slug，也不得新建第二套 Project。

## 人物资产

人物文件最少包含以下 YAML frontmatter；正文写人物描述、外形、关系、动机或用户要求的其他
事实：

```markdown
---
char_id: stable-ascii-id
char_name: 展示名称
---

# 展示名称

人物描述。
```

- 新增：选择 `assets/characters/` 中尚未使用的 ASCII kebab-case ID，创建一个新文件；文件名
  默认与 `char_id` 一致，不覆盖已有文件。
- 更新：先通过 ID、名称和内容定位唯一人物，保留原 `char_id` 和文件路径，只编辑用户要求的
  属性。改名默认只修改 `char_name`、标题和有关正文，不改变引用 ID。
- 删除：只有用户明确要求删除时才移除对应人物文件；删除前必须搜索剧本、分镜和其他资产中的
  `character_refs`、shot `characters`、关系字段和明确正文引用。Claude Code 没有内建 Delete
  时，只可用一次精确 `rm -- <单个人物文件实际路径>`，不得使用通配符、递归或删除目录，且
  必须接受用户可见的 Bash 确认。

可选 frontmatter 如 `occupation`、`personality.core_traits`、`relationships` 可以保留或按用户
要求更新；不要为了满足最小示例删除已有字段。

## 场景资产

场景文件最少包含：

```markdown
---
scene_id: stable-ascii-id
scene_name: 展示名称
---

# 展示名称

场景的空间、氛围和视觉事实。
```

- 新增：使用未占用的 ASCII kebab-case `scene_id` 和同名文件，不覆盖已有场景。
- 更新：保留 `scene_id` 与路径，修改名称、空间、氛围或用户点名的属性。
- 删除：只有用户明确要求时删除；先检查 `scene_refs`、shot `scene_ref` 和正文场头引用。没有
  内建 Delete 时，仅可精确 `rm -- <单个场景文件实际路径>` 并等待用户可见确认。
- 可选 `location_class`、`relationships` 等已有字段必须在无关修改中保留。

## 道具资产

道具文件位于 `assets/props/`，以稳定 `prop_id` 作为跨 Episode、分镜和 Prompt 的引用身份，
展示名称使用 `name`。新增、更新、删除遵守与人物/场景相同的文件和引用完整性规则：更新保留
ID 与路径，删除前搜索分镜、Prompt、剧本、`owner` 和其他道具关系。没有内建 Delete 时，只
可用一次精确 `rm -- <单个道具文件实际路径>` 并等待用户可见确认。

`assets/_audit-report.md`、各分类 `_index.md` 与 `_lock.md` 是集合元数据，不是单个业务资产；
不得用单资产删除命令删除。需要因资产变更同步这些文件时，按已安装 `/drama-asset` Skill 的
规则更新。当前 Dream 页面 stage 只消费人物、场景和 Episode 分镜；道具文件仍是 canonical
业务事实，但不得伪装成人物或场景 stage。

## 分镜与镜头

一个 Episode 的分镜只在
`stories/<project-slug>/episodes/<EPxx>/storyboard.yaml` 中维护。镜头是 `shots` 列表项，
不是独立文件。现有分镜至少保留：

```yaml
episode: EP01
total_shots: 1
total_duration_sec: 6
shots:
  - shot_id: "shot-001"
    shot_type: "wide"
    visual: "画面描述"
    camera:
      movement: "static"
    timing:
      duration_sec: 6
```

- `shot_id` 必须是 Episode 内唯一、稳定、带引号的 ASCII 字符串。更新镜头不得换 ID；新增
  镜头不得复用已存在的 ID。
- 新增、更新或删除 `shots` 后，`total_shots` 必须等于当前列表长度，
  `total_duration_sec` 必须等于现存镜头 `timing.duration_sec` 的总和。
- 若现有 shot 已有 `scene_ref`、`characters`、`dialogue`、锚点或其他丰富字段，局部修改时
  必须保留这些字段，不能把完整分镜降级成最小示例。
- 删除只移除用户明确点名的 shot，不得用重写整个分镜的方式静默丢失其他镜头。

## 引用完整性

新增引用前确认目标人物或场景 ID 已存在。删除或变更身份前，搜索：

- `character_refs` 与 `scene_refs`；
- 道具 ID、`prop_refs`、shot/Prompt 中的道具引用与 `owner`；
- storyboard shot 的 `characters` 与 `scene_ref`；
- 人物/场景关系字段；
- 剧本、分集大纲、审查报告或 Prompt 中的明确 ID/名称引用。

如果用户意图明确且影响可以安全局部处理，在同一个 turn 更新引用和资产，不能留下已知悬空
引用。如果会改变未点名剧情、存在多个合理替代或无法判断删除范围，先使用 AskUserQuestion
说明影响并请求选择。不得静默删除引用该资产的整段剧本、完整 Episode 或其他未点名资产。

## 完成与同步

- 文件工具成功完成所有用户要求且引用完整后，才可以回复完成。
- 根 Agent turn 成功结束后，宿主 `DreamArtifactTurnHook.after_main_turn` 会扫描完整文件事实，
  幂等刷新 `.dream/runtime/runs/<run-id>/stages/` 和页面投影。
- Agent 不需要也不得直接写 stage、revision、manifest 或 completion fact。
- Agent 失败、用户 Stop、取消或等待确认时，宿主不会发布本轮半成品。
