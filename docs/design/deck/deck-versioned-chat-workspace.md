<!-- [Input] Implemented Deck aggregate commits and missing Thread apply capability. -->
<!-- [Output] Boundary between content vN and future immutable Thread binding. -->
<!-- [Pos] Deck aggregate/Thread version architecture contract. -->

# Deck 内容版本与历史 Thread 边界

## 已实现的 Deck 内容能力

Admin Drizzle `0036` 发布 `dream.deck-content-versions.v1`：

1. `decks.draft_revision/latest_version/published_draft_revision`；
2. append-only `deck_versions` JSONB snapshot/hash；
3. 数据库 no-update/no-delete triggers；
4. Dream state/preview/commit/history API；
5. 所有 Deck 表单有效变更在同一事务锁 aggregate 并推进 revision；
6. commit 通过 expected draft/base CAS，冲突/失败不破坏草稿和旧版本。

snapshot 包含 Deck 元数据、Agent/Voice、memory config 数据、Claude plugin refs/provenance、Chat/Dream
类型和 active runtime binding。图标、颜色、启停、排序既然在 Deck 表单可维护，也进入内容 snapshot；
Voice 的运行时 thread association 与市场统计不进入。

## 尚未实现的 Thread capability

现有历史 Thread 尚无 Admin-owned `deck_content_version_id`/snapshot Agent key/apply receipt。因此：

- 历史 Thread 不自动、批量或静默切换到新 Deck vN；
- 当前页面不宣称某个旧 Thread 已完成内容版本升级；
- 新 Thread 固定 vN、旧 Thread 显式 source/target、apply CAS/receipt 需要后续 Admin expand；
- 缺少历史证据时显示“版本未记录”，不猜为 v1。

后续实现必须先由 Admin Drizzle扩展 Thread FK/receipt，然后 Dream 双版本读取、backfill/validate，最后
才开放 [`thread-version-upgrade.md`](./thread-version-upgrade.md) 的显式单 Thread 确认入口。任何失败保留
source version；取消零写；不得提供“全部更新到最新版”。

## 版本概念分层

| 概念 | 含义 | UI 层级 |
|---|---|---|
| Deck 内容 vN | 用户显式提交的完整配置 snapshot | 主版本、列表/头部/历史时间线 |
| draft revision | 未提交表单写的聚合 CAS token | “草稿 rN”，不叫发布版本 |
| runtime plugin semver | 当前 Dream 运行制品精确版本 | 次级运行配置；同时固定进内容 snapshot |
| binding revision | 运行选择 CAS/history | 次级折叠记录，不冒充 Deck vN |
| Thread source version | 单 Thread 固定的 Deck 内容版本 | 后续 capability；显式升级 |

市场分发继续延期至 [`../deck-register/README.md`](../deck-register/README.md)。
