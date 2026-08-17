<!-- [Input] Deck CRUD, content-version capability, binding CAS, and deferred Thread apply receipt. -->
<!-- [Output] Nine end-to-end Mermaid business sequences. -->
<!-- [Pos] Deck management/version sequence source of truth. -->
<!-- [Sync] 2026-08-16: implement durable draft/explicit commit and retain explicit-only Thread upgrades. -->
<!-- [Sync] 2026-08-17: add related Chat cleanup before owned Deck deletion. -->

# Deck 业务时序

## 1. 打开管理列表并加载内容版本

```mermaid
sequenceDiagram
  actor U as 用户
  participant UI as 前端
  participant A as Deck API
  participant V as 版本/权限校验
  participant DB as PostgreSQL
  U->>UI: 打开 Deck 管理
  UI->>A: GET /api/decks
  A->>DB: 读取 actor-owned Deck/Agent count
  A->>V: 验证 dream.deck-content-versions.v1
  V->>DB: 读取 latest_version/draft_revision/published_revision
  A->>DB: 读取 active runtime binding
  A-->>UI: 内容 vN/未提交 + 草稿状态 + 可选运行插件 vX
  UI-->>U: 扁平列表；无 capability 不伪造版本
```

## 2. 展开和收起版本记录

```mermaid
sequenceDiagram
  actor U as 用户
  participant UI as 前端
  participant A as Deck API
  participant V as 版本/权限校验
  participant DB as PostgreSQL
  Note over UI: 默认 folded，不请求 history
  U->>UI: 点击版本记录
  UI->>A: GET /api/decks/{id}/versions
  A->>V: capability + owner 权限
  V->>DB: 读取不可变 deck_versions DESC
  A-->>UI: current state + vN history / empty / error
  UI-->>U: 桌面流内 300px / 窄屏同组件全宽
  U->>UI: 再次点击、收起或 Escape
  UI-->>U: 关闭并恢复焦点
  Note over U,DB: 展开/收起零业务写入
```

## 3. 创建、保存草稿并提交新版本

```mermaid
sequenceDiagram
  actor U as 用户
  participant UI as 前端
  participant A as Deck API
  participant V as 版本/权限校验
  participant DB as PostgreSQL
  U->>UI: 创建 Deck
  UI->>A: POST /api/decks
  A->>DB: INSERT Deck durable draft r1
  A-->>UI: deck_id；打开维护弹窗
  U->>UI: 修改 Deck/Agent/插件表单
  UI->>A: 原生产 PUT/POST/DELETE
  A->>V: owner + 字段校验
  V->>DB: 锁 Deck，比较旧值，写入并 draft_revision+1
  U->>UI: 点击提交 v1/vN+1
  UI->>A: POST /versions/preview(expected draft/base)
  A->>V: owner + capability + CAS + snapshot diff/hash
  A-->>UI: target vN + 分类差异 + 影响范围
  U->>UI: 确认并填写可选说明
  UI->>A: POST /versions(expected draft/base)
  A->>DB: BEGIN + FOR UPDATE Deck
  A->>V: 重验权限/CAS/hash/no-op
  alt 冲突或无变化
    V-->>UI: 409；不写版本，刷新后重新预览
  else 提交成功
    A->>DB: INSERT immutable deck_versions vN
    A->>DB: UPDATE latest/published draft revision + COMMIT
    A-->>UI: vN + clean draft state
  end
```

## 4. 历史 Thread 检测可升级版本（后续 capability）

```mermaid
sequenceDiagram
  actor U as 用户
  participant UI as 前端
  participant T as Thread API
  participant V as 版本/权限校验
  participant DB as PostgreSQL
  U->>UI: 打开历史 Thread
  UI->>T: GET Thread
  T->>DB: 校验 owner，读取固定 Deck source version
  T->>V: 比较有权限的 latest Deck content version
  V-->>T: source v9 / target v12 / upgradeable
  T-->>UI: 明确 source/target；不自动应用
  UI-->>U: 当前 v9 + 显式升级入口
```

## 5. 用户确认升级历史 Thread（后续 capability）

```mermaid
sequenceDiagram
  actor U as 用户
  participant UI as 前端
  participant T as Thread API
  participant V as 版本/权限校验
  participant DB as PostgreSQL
  U->>UI: 确认 v9 → v12
  UI->>T: source/target/expected Thread revision/idempotency key
  T->>V: owner、target 可见、Thread idle、CAS
  alt 冲突/目标漂移
    V-->>UI: 409 + 最新事实；重新确认
  else apply 失败
    T->>DB: ROLLBACK
    T-->>UI: 原 v9 保持 + 可重试错误
  else 成功
    T->>DB: 原子写 apply receipt 并 CAS v9→v12
    T-->>UI: Thread 当前 v12
  end
```

## 6. 用户取消升级

```mermaid
sequenceDiagram
  actor U as 用户
  participant UI as 前端
  participant T as Thread API
  participant DB as PostgreSQL
  U->>UI: 打开 v9 → v12 确认
  U->>UI: 取消/关闭/Escape
  UI-->>U: 关闭并恢复焦点
  Note over UI,T: 不发送升级请求
  Note over T,DB: Thread 保持 v9，零业务写入
```

## 7. 升级失败并保留原版本

```mermaid
sequenceDiagram
  actor U as 用户
  participant UI as 前端
  participant T as Thread API
  participant V as 版本/权限校验
  participant DB as PostgreSQL
  U->>UI: 确认 v9 → v12
  UI->>T: 定向 apply
  T->>V: 权限、source/target、冲突校验
  V->>DB: 尝试准备 v12 receipt
  DB-->>V: 失败
  V->>DB: ROLLBACK
  T-->>UI: error + source remains v9
  UI-->>U: 明确仍使用 v9，可重试
```

## 8. 新 Thread 与历史 Thread 选择版本差异

```mermaid
sequenceDiagram
  actor U as 用户
  participant UI as 前端
  participant T as Thread API
  participant V as 版本/权限校验
  participant DB as PostgreSQL
  alt 新 Thread
    U->>UI: 选择 Deck/Agent 并创建
    UI->>T: POST Thread
    T->>V: 权限 + 当前已提交 Deck v12
    V->>DB: 同事务固定 v12 snapshot identity
    T-->>UI: 新 Thread 使用 v12
  else 历史 Thread
    U->>UI: 打开固定 v9 的 Thread
    T-->>UI: source v9 / available v12
    Note over UI,DB: 默认继续使用 v9；绝不自动或批量升级
    U->>UI: 可选显式确认升级
  end
```

## 9. 查看并删除相关对话后删除 Deck

```mermaid
sequenceDiagram
  actor U as 用户
  participant UI as Settings / Work
  participant T as Thread API
  participant D as Deck API
  participant V as 权限/依赖校验
  participant DB as PostgreSQL
  U->>UI: 更多 → 相关对话
  UI->>T: GET /threads?deck_id=deck-a&limit=20
  T->>V: 校验当前 actor
  V->>DB: user_id + deck_id 查询，按 updated_at 降序
  T-->>UI: Chat 历史预览
  loop 用户逐条确认删除
    U->>UI: 删除一条对话
    UI->>T: DELETE /threads/thread-a
    T->>V: thread owner 校验
    V->>DB: 删除 thread 并级联 messages
    T-->>UI: 从预览移除
  end
  U->>UI: 删除 Deck
  UI->>D: DELETE /decks/deck-a
  D->>V: owner + child + related thread + runtime snapshot
  alt 仍有关联对话
    V-->>UI: 409 related_threads；Deck 与绑定保持
  else 存在不可变 runtime snapshot
    V-->>UI: 409 runtime_history；不伪装成 Chat
  else 可以删除
    V->>DB: BEGIN；删除 refs + 未使用 bindings + Deck；COMMIT
    D-->>UI: success；刷新 Work 列表
  end
```
