<!-- [Input] Shared Dream Thread, successful after-turn Hook, Workflow Run facts, Episode registry, Execution route selection, and Episode artifact readers. -->
<!-- [Output] Business sequence for EP02 registration, index-first navigation, per-Episode reads, branches, and return behavior. -->
<!-- [Pos] Mermaid sequence companion to episode-sync-index.md. -->
<!-- [Sync] 2026-09-02: cover changed or uniquely discovered EP02 activation through isolated artifact reading without EP01 fallback. -->

# Episode 同步索引业务时序

```mermaid
sequenceDiagram
    autonumber
    actor U as 用户
    participant C as 共享 Chat / Dream 页面
    participant A as 同一 Dream Agent
    participant H as Dream after-turn Hook
    participant R as Episode registry
    participant W as Workflow Run 状态来源
    participant P as Execution 页面
    participant Q as Router / 页面选择状态
    participant I as Episode index API
    participant E as Episode artifact API
    participant F as Episode artifact reader

    U->>C: 在现有 Thread 开启 EP02 创作任务
    C->>A: 通过现有 turn / resume 路径发送用户请求
    A->>A: 创建或更新 canonical EP02 文件
    A-->>H: 同一主 Agent turn 成功结束
    H->>H: 校验 allowlist，并比较本轮前后 Episode 文件事实
    H->>R: 幂等补齐连续 Episode registry（EP01、EP02）
    alt 本轮只改变 EP02
        H->>R: 将 EP02 记为 active Episode
    else 文件未变化但只补注册一个既有 EP02
        H->>R: 将唯一新发现的 EP02 记为 active Episode
    else 同时改变多集或同时补注册多个 Episode
        H->>R: 保留原 active Episode，不猜测
    end
    H->>H: 原子发布当前 Run-private artifact manifest
    H->>W: 沿用现有 Run/Thread 记录，不创建新任务

    U->>C: 进入 Execution 并选择“同步”
    C->>P: 打开同一 Run 的同步视图
    P->>Q: 读取 URL（无 episode 参数）
    Q-->>P: 页面状态 = Episode 索引
    P->>I: GET Run Episode index
    I->>W: 校验 actor、Run、Thread 与冻结 provenance
    I->>R: 读取 registry revision、active UID 和 Episode 列表
    loop 每个已注册 Episode
        I->>F: 读取该 Episode 的 allowlist 可用性摘要
        F-->>I: 可用项、问题项、更新时间
    end
    I-->>P: EP01 / EP02 索引（稳定 UID + 用户可见 code）
    P-->>U: 先显示 Episode 索引，不直接进入 EP01

    U->>P: 选择 EP02
    P->>Q: 写入 ?episode=<EP02 stable UID>
    Q-->>P: Selected Episode = EP02
    P->>E: GET Episode artifacts（Run + EP02 UID）
    E->>W: 校验 actor 与 Run provenance
    E->>R: 验证 EP02 UID 属于当前 Run registry
    E->>F: 只读取 EP02 canonical artifact roots
    F-->>E: EP02 surface / availability / revision
    E-->>P: 回显 EP02 UID、EP02 code 和 EP02 产物

    alt EP02 正在执行
        P-->>U: 显示 EP02、执行中及当前已到达产物
    else EP02 已有产物
        P-->>U: 显示 EP02 产物工作台
    else EP02 暂无产物
        P-->>U: 显示“EP02 暂无产物”
        Note over P,F: 禁止读取或回退展示 EP01
    else EP02 读取失败
        P-->>U: 保留 EP02 身份并显示失败/重试；仅允许 EP02 自身 LKG
    else EP02 UID 不存在或已失效
        E-->>P: registry membership 失败
        P-->>U: 显示“当前 Episode 不存在或已失效”
    end

    U->>P: 激活顶部“返回 Episode 索引”
    P->>Q: 删除 episode 参数，保留 Run 路径
    Q-->>P: 页面状态 = Episode 索引
    P-->>U: 返回原索引，并将焦点恢复到 EP02 行
    Note over U,W: 不创建任务、不重启 Agent、不改变 Thread/Run
```

## 不变量

- Router、index response、artifact request 与 artifact response 必须引用同一个 Episode UID。
- Artifact ETag 与 last-known-good cache 的 identity 是 `Run ID + Episode UID`。
- URL 没有 Episode UID 时只显示索引；无条件数组首项不是合法默认值。
- EP02 不存在、无产物或失败时，页面不得显示 EP01 的标题、状态、正文或镜头。
