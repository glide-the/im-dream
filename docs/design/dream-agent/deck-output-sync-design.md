# Dream 工作台文件自动同步

> 状态：已实现最小闭环。本文只定义“主 Agent 写工作台文件、服务端同步到当前 Run 的 `.dream`、Dream 页面读取并展示”。命令编排、next action、checkpoint、通用 revision 工作流和 MCP 重同步不属于本方案。

## 1. 业务目标

Dream 用户在共享 Chat thread 中与主 Agent 对话。Agent 使用普通工作台文件保存创作结果；根 turn 正常结束后，服务端自动把可展示内容和 Project/Episode 核心文件同步到当前 Run 的私有 `.dream` 目录。刷新 Dream 页面后仍能看到同一 Run 的人物、场景和分镜。

两个历史任务只用于确认真实产物范围：

| 对照任务 | 真实产物 | 本方案采用部分 |
|---|---|---|
| `019fcb01-c61c-7f22-9d56-fb38660f042a` | 首次空间产出人物卡、场景卡、分镜并在 Dream 页面逐步展示 | 人物、场景、分镜页面投影 |
| `019fd74e-e06f-7073-a714-fe86cdada2ce` | Project/Episode 文件及后续动作、审查产物 | `project.yaml`、`episode-outline.md`、`script.md`、`storyboard.yaml`、`review-report.md` 文件合同 |

不采用历史任务中的固定阶段、推荐动作、checkpoint 或动作完成状态机。

## 2. 工作台与私有目录

### 2.1 Agent 可写的 canonical 工作台

```text
<shared-root>/<server-derived-thread-key>/
  assets/
    characters/*.{md,yaml,yml}
    scenes/*.{md,yaml,yml}
  stories/<project-slug>/
    project.yaml
    episodes/<EPxx>/
      episode-outline.md
      script.md
      storyboard.yaml
      review-report.md
```

源资产兼容真实历史内容：文件名可以是 Unicode；内容可以是标准 frontmatter、plain YAML，或带一级标题及顶层 `id/name` 字段的 Markdown。所有文件必须位于当前 server-derived thread workspace 内，不能是符号链接，必须为 UTF-8 且受大小和数量上限约束。

### 2.2 服务端拥有的 `.dream`

```text
<shared-root>/<server-derived-thread-key>/.dream/runtime/runs/<run-id>/
  run.json
  stages/
    characters.json
    scenes.json
    storyboards.json
  artifact/
    manifest.json
    stories/<project-slug>/
      project.yaml
      episodes/<EPxx>/
        episode-outline.md
        script.md
        storyboard.yaml
        review-report.md
```

Agent 不使用普通文件工具写 `.dream/**`。`DreamArtifactTurnHook` 使用数据库中的 actor、thread、Run 和冻结 Deck binding 验证当前权限，再由服务端文件服务写入。

## 3. 唯一同步链路

```text
ClaudeAgentService.assemble_context
  → 激活当前 Dream Run
  → DreamArtifactTurnHook.before_main_turn
  → ClaudeAgentRunner.run_streaming（入口不变）
  → 根 turn success
  → DreamArtifactTurnHook.after_main_turn
      → 更新页面 stages
      → 复制 Project/Episode allowlist
      → 最后提交 artifact/manifest.json
  → 原 Chat message-final / finish
```

`DreamArtifactTurnHook` 是标准类，不是闭包；它不调用 Agent、不产生 SSE、不改变 Claude session、不推进 Workflow 状态，也不通过 Observer 反向控制 `ClaudeAgentService`。

只有根 turn `success` 执行 after hook。Stop、取消和 runner failure 不发布本轮文件。
Hook 若无法完成权限校验或原子发布，同一 Chat turn 使用既有失败路径结束并保留 last-good；
不得记录成功后继续发出 `finish`，也不得另造第二个终态。下一次成功根 turn 会重新读取
工作台并可自然修复投影。

## 4. 页面投影规则

| 工作台事实 | `.dream` 页面投影 | Dream 页面 |
|---|---|---|
| `assets/characters/*` | `stages/characters.json` | 人物区显示名称、摘要、关系和源文件 |
| `assets/scenes/*` | `stages/scenes.json` | 场景区显示名称、摘要、关系和源文件 |
| `stories/*/episodes/EPxx/storyboard.yaml` | `stages/storyboards.json` | 分镜区显示 Episode、镜头数和时长 |
| Project/Episode 核心文件 | `artifact/stories/**` + `manifest.json` | 当前不另建第二套页面协议；文件作为同一 Run 的私有发布副本 |

Dream 页面继续使用现有 actor-scoped `GET .../dream-files`。该 GET 只读 `run.json` 和 stage 文件，无调度、恢复或启动 Agent 的副作用。页面运行中轮询，根 turn 结束后立即刷新；刷新浏览器或从 Chat 切回 Dream 时仍由同一 thread/run 恢复。

## 5. 正常业务时序

```mermaid
sequenceDiagram
    actor U as 用户
    participant D as Dream 页面
    participant S as ClaudeAgentService
    participant A as 主 Agent
    participant W as canonical 工作台
    participant H as DreamArtifactTurnHook
    participant P as .dream 私有 Run

    U->>D: 在同一 thread 发送创作要求
    D->>S: 共享 Chat thread SSE 请求
    S->>H: before_main_turn(actor/thread/run/workspace)
    S->>A: run_streaming（原入口）
    A->>W: 写人物、场景或 Episode 文件
    A-->>S: 根 turn success
    S->>H: after_main_turn(ticket)
    H->>H: 重验 DB 权限和冻结 binding
    H->>W: 安全读取 allowlist 文件
    H->>P: 幂等写 stages 和 artifact 文件
    H->>P: 最后原子替换 manifest.json
    S-->>D: 原 Chat message-final + 唯一 finish
    D->>P: 通过 dream-files GET 刷新
    P-->>D: 当前人物、场景、分镜投影
```

## 6. 重复、失败与取消

```mermaid
sequenceDiagram
    participant S as ClaudeAgentService
    participant A as 主 Agent
    participant H as DreamArtifactTurnHook
    participant P as .dream 私有 Run

    alt 成功且内容变化
        A-->>S: success
        S->>H: after_main_turn
        H->>P: 写变化文件并提交新 manifest 内容摘要
    else 成功但字节与页面来源均未变化
        A-->>S: success
        S->>H: after_main_turn
        H-->>S: no-op，不增加 stage revision
    else Stop、取消或 runner failure
        A-->>S: cancelled / failed
        Note over S,P: 不调用 after_main_turn，不发布半成品
    else 同步器异常
        A-->>S: success
        S->>H: after_main_turn
        H--xS: 安全错误并记录日志
        Note over S,P: 旧 manifest 保持权威；同一 Chat turn 失败且不产生第二终态
    end
```

私有发布在 Run 目录锁内进行。源文件按 allowlist 复制，`manifest.json` 最后写入，是已发布快照的提交标记。中途失败不会让 manifest 宣称半成品存在。旧但未被新 manifest 引用的物理文件不再属于当前发布集合。

## 7. 页面恢复时序

```mermaid
sequenceDiagram
    actor U as 用户
    participant D as Dream 页面
    participant API as dream-files API
    participant P as .dream 私有 Run
    participant C as Chat 页面

    U->>D: 刷新或打开 Dream
    D->>API: GET(run-id)，携带当前身份
    API->>P: 校验 thread/Run 所有权并只读投影
    P-->>API: run + characters/scenes/storyboards
    API-->>D: 当前投影
    D-->>U: 正常显示已有产物
    U->>C: 切到 Chat（同一 thread）
    U->>D: 切回 Dream（同一 thread/run）
    D->>API: 再次 GET
    API-->>D: 相同或更新后的投影
```

## 8. Project/Episode 发布限制

- 一个 Run 最多解析一个 canonical project；`project.yaml` 中的 Project ID 必须与目录 slug 一致。
- Episode 目录必须是 `EP` 加两位数字。
- 只复制本文列出的五种核心文件，不接受 Agent 提交任意目标路径。
- 私有目标路径只由服务端根据 thread/run/project/episode 派生。
- 不执行数据库 DDL，不削弱 workflow 权限，不更改 Story current source。

## 9. 明确不实现

- 不由页面维护 `/drama-*` 固定清单；Slash 建议只读取实际安装 inventory。
- 不按 `/drama-*` 建立服务端顺序、禁用规则或推荐状态。
- 不使用 next action、recommended action 或 checkpoint 决定同步。
- 不要求 Agent 调用 MCP 才同步，也不增加专用 resync MCP。
- 不使用文件 watcher、PostToolUse 或子 Agent 回调提前发布。
- 不让 `DreamObserver` 读取工作台或成为同步 owner。
- 不增加 Dream SSE、Dream reducer、第二套 session 或第二终态。
- 不修改 `ClaudeAgentRunner.run_streaming` 或原始 `claude_session_id` 语义。

## 10. 验收

- 真实主 Agent 能在 canonical 工作台产生人物、场景、分镜及 Project/Episode 文件。
- 根 turn success 后，对应 stages 和 private artifact 自动出现；Agent 没调用 Dream MCP 也成立。
- 重复内容同步为 no-op；修改文件后 manifest 内容摘要变化。
- Stop、取消、输出失败不发布本轮半成品。
- 页面无需新协议即可显示人物、场景和分镜；刷新和 Chat↔Dream 切换后仍一致。
- Chat 输入 `/` 时只推荐当前 Deck/thread 实际安装的 Skill，并只插入普通文本。
- Admin 服务端日志包含同步结果或明确异常，日志不进入 SSE 正文。
