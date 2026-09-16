<!-- [Input] User-selected Codex task and verified clean Admin main commit 7a6e6c9. -->
<!-- [Output] Fast-forwarded matching Admin worktree with all existing dirty files preserved. -->
<!-- [Pos] Coordinator-owned commit synchronization; original auth/data migration goal remains active. -->
<!-- [Sync] 2026-09-15: record one Prompt Architect pass before the authorized Git mutation. -->

# Admin 模型权益提交同步

## 背景与问题

用户指定任务“修复 v6 模型不可选”（01a0a183-883a-7062-b88b-ca441ebafa26）的提交同步到对应迁移 worktree，并继续原任务。实际 Admin main 已提交且 clean；目标 worktree 含正在实现的认证与数据接口，不能暂存、提交或覆盖这些修改。

## 目标与边界

源 commit `7a6e6c966561beeac7724fd77828a9f4ce3b26ec` 的唯一 parent 是目标 HEAD `ca681ce9e3199ac67180d891bab9aea671424c34`。目标为 Admin `codex/admin-auth-data-provider` worktree729f。核验11个 commit 变更文件和273个现有 dirty 文件没有交集；Admin 任务已暂停写入。仅 fast-forward 既有 commit，不创建合并提交或变更发布基线。

## 概念与规则

先验证源/目标 HEAD、源 clean、parent、目标分支、dirty/commit 无交集，再将现有 dirty 文件和状态快照保存到本轮0700目录。执行 `git merge --ff-only` 后核验11文件等于源 commit 的 blob、273现有 dirty 文件 bytes/类型/权限及Git状态不变、源 HEAD/状态不变。失败保留快照和命令，不 reset/stash/cherry-pick 用户修改。同步改变订阅模型权益选择和发布前校验，数据库/认证/API capability与Runtime/共享FS协议没有本轮设计变化。原任务的技术与真实验收仍分别跟踪。

## Optimized Prompt:

You are the primary coordinator and synchronize the user-selected existing Admin commit into the matching auth/data worktree. Evidence proves clean main at 7a6e6c966561beeac7724fd77828a9f4ce3b26ec, its single parent equal to target ca681ce9e3199ac67180d891bab9aea671424c34, and eleven changed paths disjoint from 273 existing dirty paths. The Admin task has paused all writes. Revalidate every Git fact immediately, snapshot dirty bytes/types/modes and porcelain/index state into a newly named 0700 task-owned directory, and execute only git merge --ff-only with the exact existing commit. Preserve every uncommitted tracked/untracked/deleted file, branch identity and source checkout; do not stage, commit, stash, reset, clean, move tags or publish. Verify the target HEAD/branch, all eleven commit blobs and all original dirty bytes/types/modes/status, then record command/cwd/exit and a sanitized durable receipt. Update this coordinator-owned plan/folder index and exact Dream document mirror without touching either task's owned implementation. Resume the paused Admin task and continue full original auth/data migration and required acceptance; commit synchronization is not overall completion. On any mismatch keep evidence, stop only the dependent Git mutation and resolve the concrete conflict. Do not repeat unrelated tests that already passed; validate the exact sync scope and report any unavailable validation distinctly.

USER REQUIREMENT:
把任务01a0a183-883a-7062-b88b-ca441ebafa26的commit改动同步到对应worktree，然后继续原跨项目重构。

## 验收与当前状态

read-only preflight 退出0：source clean、single-parent=target、11 changed/273 protected、intersection为空。实际 `python3 /private/tmp/ink-sync-admin-entitlement-commit.py` cwd Dream root，退出0；`git merge --ff-only 7a6e6c966561beeac7724fd77828a9f4ce3b26ec` cwd Admin729f，退出0。目标HEAD已更新，11 blob和273旧dirty bytes/类型/权限/Git状态/cached diff逐项吻合，源HEAD/clean状态不变，两个diff checks均0。0700快照与实际命令见[同步回执](../exec/admin-auth-data-verification/admin-entitlement-commit-worktree-sync.json)。Admin已通知恢复文件写入，两任务继续原认证与数据迁移，goal保持active。
