<!-- [Sync] 2026-10-07: 独立评审修正一次total、updatedAt强上下文失效及observed/loaded/verification分别去重；最新background成功事实同步，仍待复核。 -->
<!-- [Input] 当前连接器同步策略、公开 DTO、Calendar 快照读取与2026-10-07正常服务观察。 -->
<!-- [Output] 可见面板版本发现、极简正文及跨进程同步恢复能力缺口的待评审合同。 -->
<!-- [Pos] Calendar 同步发现增量设计证据；正文合同归现行 PRD/正式稿。 -->
<!-- [Sync] 2026-10-07: 仅设计与源码诊断，尚未实施或验收；浮空修复另行执行。 -->
# 2 结构增量

Optimized Prompt：保留浮空外壳与原滚动owner，缩减Notion内部信息结构。

```text
P03 原浮空workspace / 原tabs
P04 Notion 文档  2篇                    刷新
    [仅必要的一条错误/partial/同步恢复＋管理入口]
    当日创建（非空）
      文档标题链接
      创建时间〔双命中另保留编辑时间〕
    当日编辑（仅今天且非空）
      文档标题链接 / 编辑时间
```

1440仅active section长列表滚动；1024/430/390原Calendar整体滚动/sticky tab和外部shadow安全留白不改。当前浮空失败另行修复，本稿不重复设计外壳。
