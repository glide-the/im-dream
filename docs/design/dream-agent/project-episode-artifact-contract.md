# Project / Episode Artifact 合同

跨系统权威文档是
`/Users/dmeck/project/ink-admin-memory/docs/design/modules/story-business/admin-dream-interaction-design.md`。
本文只定义 Dream 当前最小闭环使用的概念和边界；若出现冲突，以 Admin 权威合同为准。

## 1. 概念

| 概念 | 含义 | 不是 |
|---|---|---|
| Project | 稳定的创作容器，由 `project_id/project_slug` 标识 | Workflow Run 或 thread |
| Episode | Project 中的分集，目录身份为 `EP01`–`EP99` | 一次 Agent turn |
| Thread | Chat/Dream 共用的对话与 Claude session 容器 | Story 身份或浏览器路径 |
| Workflow Run | 一次可审计执行尝试 | Project/Episode 稳定身份 |
| Run preview | 当前 Run 工作台文件的私有发布副本 | Admin sealed Artifact |

## 2. canonical 工作台合同

```text
<thread-workspace>/
  assets/
    characters/*.{md,yaml,yml}
    scenes/*.{md,yaml,yml}
  stories/<project-id>/
    project.yaml
    episodes/<EPxx>/
      episode-outline.md
      script.md
      storyboard.yaml
      review-report.md
```

- `project.yaml` 的 `project_id` 和 `project_slug` 必须与目录完全一致。
- Project ID 必须匹配 `^[a-z0-9]+(?:-[a-z0-9]+)*$`。
- Episode 目录必须匹配 `^EP[0-9]{2}$`。
- 当前同步只复制上述五类 Project/Episode 核心文件；资产卡只生成页面 stage。
- 浏览器、模型正文和绝对路径都不能覆盖服务端派生的 thread/run 根目录。

## 3. 当前 Run 私有发布

```text
<thread-workspace>/.dream/runtime/runs/<run-id>/
  run.json
  stages/
    characters.json
    scenes.json
    storyboards.json
  artifact/
    manifest.json
    stories/<project-id>/
      project.yaml
      episodes/<EPxx>/
        episode-outline.md
        script.md
        storyboard.yaml
        review-report.md
```

`manifest.json` 使用 `dream-artifact-manifest/v1`，记录当前 Run、内容 revision、每个
已发布文件的相对路径、大小和 SHA-256。文件先写，manifest 最后原子提交；manifest
未引用的旧物理文件不属于当前发布集合。

```mermaid
sequenceDiagram
    participant W as canonical 工作台
    participant H as DreamArtifactTurnHook
    participant P as Run preview

    H->>W: 校验并读取 allowlist
    H->>P: 写内容文件
    H->>P: fsync 文件和目录
    H->>P: 原子替换 manifest
    Note over P: manifest 是当前 preview 的提交标记
```

## 4. 与 Admin sealed Artifact 的区别

当前 preview 只证明“这个 Run 已把哪些工作台字节发布给 Dream 页面”。它不会：

- 创建或切换 Admin canonical Story；
- 生成权威 `episode.json` / `episode-workflow.json`；
- 完成 Source Message authority、完整 Artifact 校验或 Story CAS；
- 把 Chat finish、stage revision 或 preview manifest 当作业务发布完成。

未来实现 sealed Artifact 时，必须直接遵循 Admin 权威合同，不得把当前 preview 扩展
成第二套版本账本或 lifecycle truth source。

## 5. 权限与一致性

发布前必须证明：Run 属于当前用户和 Workspace；source message 属于同一 owned
thread；冻结 Deck binding 与 Run 一致；Project/Episode 目录和文件身份一致。任何不一致
都 fail closed，不扫描替代目录、不按文件名合并跨 thread 内容。

成功后重复同步相同字节必须是 no-op；failed/cancelled turn 不提交新 manifest。
