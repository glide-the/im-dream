# Dream 工作台上下文

本文件是 Story Workspace 随 Dream thread 工作区部署的 Agent 业务合同。服务端负责初始化、
校验和刷新本文件；Agent 每轮可以读取，但不得修改本文件或其他 `.dream/**` 私有发布内容。

## 每轮操作前提

- 每个 Dream 用户 turn 都会在消息上下文中给出本文件经过服务端校验的实际路径。
- 开始处理用户请求前，必须使用 `Read` 读取该实际路径以及同目录下经服务端指明的
  `ASSET-COLLABORATION.md`，确认本轮 run、thread、Project、Episode 和资产编辑规则；不能只
  依赖上一轮记忆。
- 如果文件无法读取，或者文件事实与本轮服务端指令不一致，停止文件修改并明确报告工作区
  上下文不可用；不得自行猜测或新建另一套 Project。
- Dream 与 Chat 共用同一 thread 和 Claude Code session。自然语言中的“继续”“当前项目”或
  “当前 Episode”都指本文件列出的 canonical 工作台。

## 业务原则

- `/drama-init` 只在首次项目初始化时默认执行；其余已安装的 `/drama-*` Skill 由用户按需、
  任意顺序和次数调用，不存在服务端 Skill 阶段状态机。
- Skill 负责创作；根 Agent turn 成功结束后，宿主 Hook 只根据当前文件事实同步 `.dream`
  页面投影。
- Story Workspace MCP 写入或校验工具是即时预览、显式修复的辅助能力；最终同步正确性不依赖
  Agent 主动调用 MCP。
- Observer 只做非控制型业务投影，不推进 Agent、Workflow 或文件状态。

## Canonical 工作台

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

`project.yaml` 是项目属性的 canonical 文件。用户要求修改标题、项目名称或其他项目属性时，
必须直接编辑唯一项目 `project.yaml` 的对应字段；例如“修改标题”应更新 `project_name`。
不能用 Chat thread 标题替代项目标题，也不能只返回结构化 JSON、建议或文字说明。

人物、场景或分镜源文件被删除时，删除本身就是当前文件事实。宿主 Hook 会移除对应旧页面
stage；新文件出现时再按新事实生成 stage。Agent 不得为保留旧页面而恢复已被 Skill 删除的
launch seed 文件。

用户自然语言要求新增、修改或删除人物、场景、道具、分镜时，必须按
`ASSET-COLLABORATION.md` 使用内建文件工具修改 canonical 文件。普通 Chat 的 standalone
proposal JSON 不能替代 Dream 文件写入。

## 私有发布路径

```text
.dream/runtime/runs/<run-id>/
  run.json
  stages/
    characters.json
    scenes.json
    storyboards.json
  artifact/
    manifest.json
    stories/<project-slug>/...
```

Agent 可以读取 `.dream` 了解宿主发布结果，但不得使用 Write、Edit 或 Bash 修改 `.dream/**`。
发布只由宿主 Hook 在成功根 turn 后完成；Stop、取消或失败 turn 不发布半成品。

## 当前服务端事实

本节由 `ClaudeAgentService.assemble_context` 在每个 Dream turn 调用模型前刷新。

当本轮是服务器自动发起的项目根修正时，事实 JSON 中的 `auto_repair` 不是普通业务状态，
而是本轮唯一可信的修正权限边界：

- `trusted_project_slug` / `trusted_project_path` 指定必须保留的服务器可信项目根；
- `stale_project_slugs` / `stale_project_paths` 指定核对并完成内容合并后才允许清理的旧根；
- `merge_direction` 固定为旧根到可信根，禁止根据文件时间、内容多少或目录名称反向猜测；
- `trusted_root_delete_allowed` 必须为 `false`，Agent 不得删除可信根；
- `validation_code`、`repair_attempt` 必须与当前自动 user 消息一致，不一致时立即停止修改。

项目根修正应使用 Read/Glob 与文件编辑工具核对和合并内容；普通 Bash 探测不是事实来源。
只有 `.dream` 事实和自动 user 消息给出的精确旧根目录删除命令可以进入受限清理校验。
