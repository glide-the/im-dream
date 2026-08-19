<!-- [Input] Historical Chat Thread binding and future Deck snapshot/apply capability. -->
<!-- [Output] Explicit single-Thread Deck upgrade confirmation and recovery design. -->
<!-- [Pos] Historical Thread version-upgrade functional-unit design. -->

# 历史 Thread 显式升级

## 功能单元合同

| 项 | 定义 |
|---|---|
| 场景 | 历史 Thread 固定旧 Deck revision，服务端证明存在可升级目标 |
| 目标 | 看清当前/目标和影响后，只升级当前一个 Thread |
| 入口 | 历史 Chat 顶部 Deck 上下文；无自动弹窗 |
| 数据 | Thread source revision、current target revision、upgrade eligibility、snapshot/apply receipt |
| 权限 | Thread 所有权、Deck 可见性、目标有效、Thread idle、expected source/target CAS |
| 对应代码 | capability 发布后扩展 Thread API、Chat 顶部上下文和 E2E；当前全部 fail closed |

## 版本提示

```text
编剧 · 剧本创作团队 · 当前 Thread 使用 v9
可升级到 v12。 [继续使用 v9] [升级版本]
```

“继续使用”只收起当前页面提示；发送消息仍使用 v9，刷新可再次显示。不得自动切换或批量升级。

## 确认弹窗文字草图

```text
┌──────────────────────────────────────────────────────────┐
│ 升级此 Thread 的 Deck 版本？                        [×] │
├──────────────────────────────────────────────────────────┤
│ 当前版本 v9  ───────────────────────────→  目标版本 v12 │
│                                                          │
│ 影响范围                                                 │
│ • 仅此 Thread 后续请求使用目标版本对应的服务端配置。     │
│ • 服务端完整应用目标版本后，才切换 Thread 版本。          │
│                                                          │
│ 不会发生                                                 │
│ • 不改写已有消息或历史结果。                             │
│ • 不改变 Deck 当前运行版本，不影响其他 Thread。          │
│ • 不提交草稿，不执行批量升级。                           │
├──────────────────────────────────────────────────────────┤
│ [取消]                                  [确认升级到 v12] │
└──────────────────────────────────────────────────────────┘
```

## 状态草图

| 状态 | UI | 持久化结果 |
|---|---|---|
| 初始 | 显示明确 `v9 → v12` | 零写入 |
| 取消/关闭/Escape | 关闭，焦点回升级入口 | 零写入，仍为 v9 |
| 升级中 | 禁用重复提交，“正在升级到 v12…” | 对外仍为 v9 |
| 成功 | 重新 GET Thread，显示 v12，live region 宣告 | receipt 一致后才提交/呈现 |
| 目标漂移 | 重绘 `v9 → v13`，要求再次确认 | 旧授权失效，零升级写入 |
| Thread 冲突 | 显示最新 source，要求重新查看 | 不覆盖并发事实 |
| 应用失败 | 弹窗保留、可重试错误 | 保持 v9 和旧应用状态 |
| 权限不足/运行中 | 禁用确认或只读提示 | 零写入 |

窄屏保留完整 source/target、影响/不影响事项和操作，不简化成“发现新版/立即升级”。

## 验收标准

1. 版本 capability 不完整时，不显示版本、升级入口或成功反馈。
2. 取消不发升级写请求；失败时 Thread 和工作台仍使用来源 revision。
3. 确认请求包含 expected source、expected current target、明确 target 与幂等键。
4. 目标漂移、权限变化、运行中和并发更新均要求重新读取，不自动追随最新版。
5. 新 Thread 固定创建时版本；历史 Thread 保持原版本，二者不共用“自动最新版”流程。
