<!-- [Input] Current Git-visible Dream source changes, the assigned Dream/Admin worktrees, and Codex task 01a0a183-883a-7062-b88b-ca441ebafa26. -->
<!-- [Output] Final source-preservation and task-commit reachability audit after all later refactor commits. -->
<!-- [Pos] Coordinator synchronization evidence; it does not authorize normal-database or service mutation. -->
<!-- [Sync] 2026-09-16: verify the original checkout and named task are represented without regressing the final worktrees. -->

# Worktree synchronization final audit

## Scope

- Dream source: `/Users/dmeck/project/ink-dream-memory`, branch `codex/auth-data-coordination`, HEAD `2c61efcfa48058f45c9dfffd8437b7de527a9f7a`.
- Dream target: `/Users/dmeck/.codex/worktrees/ef6e/ink-dream-memory`, branch `codex/dream-admin-auth-data-client`, audited HEAD `5432628fcca3a79cb44582e493af7d3e0263bd29`.
- Admin source: `/Users/dmeck/project/ink-admin-memory`, branch `main`.
- Admin target: `/Users/dmeck/.codex/worktrees/729f/ink-admin-memory`, branch `codex/admin-auth-data-provider`, audited HEAD `f3bb19c8f2ff52cd51c8e776461d44fb7b4611b2`.
- Named Codex task: `01a0a183-883a-7062-b88b-ca441ebafa26`, “修复 v6 模型不可选”.

The original checkouts were read only during this audit. No file was staged, committed, reset, removed or copied from either original checkout.

## Named task commit

The task changed the Admin repository. Its committed result is:

```text
7a6e6c966561beeac7724fd77828a9f4ce3b26ec
feat(subscriptions): enforce enabled model selection and validation for entitlements and publications
```

The commit changes 11 Admin files: the entitlement selector, subscription Service validation, two focused tests, one Playwright flow, folder contracts and subscription design/PRD documents. `git merge-base --is-ancestor 7a6e6c9 HEAD` in the Admin target exited `0`. The commit entered the target through merge commit `151774c87d3a62bd3572343a78dbfc45e284fae2`; therefore no cherry-pick or content copy is required.

## Dream source comparison

Parsing `git status --porcelain=v1 -z --untracked-files=all` in the original Dream checkout produced 399 Git-visible paths:

| Result | Count | Decision |
| --- | ---: | --- |
| Source and target bytes equal | 383 | Already synchronized. |
| Missing from target | 0 | No copy required. |
| Source and target bytes differ | 16 | Review against the common baseline and current target. |

Three differing files are mechanically subsumed: `git merge-file -p <target> <baseline-7d38715c> <source>` exited `0` and reproduced the target byte for byte for `.folder.md`, `backend/tests/test_real_cli_plugin_install.py` and `docs/design/.folder.md`.

The remaining 13 files were reviewed line by line. Every source-only line belongs to an earlier state that the target has replaced:

- `README.md` and `README.zh.md` still describe Runtime `0.1.9`, Dream `DATABASE_URL` loading and older project metadata. The target documents Runtime `0.1.10`, Admin-only database access and current metadata.
- Plugin/test folder contracts and `test_claude_plugin_runtime_pipeline.py` still reference removed production persistence modules, including `backend.schema.legacy_main_sqlite` and `workspace_packer`. The target uses the test-only legacy fixture and current Admin-backed behavior.
- Design, exec and stage indexes contain earlier synchronization headers or interim rows. The target is the later index and retains the corresponding documents.
- `exec_admin-auth-data-coordination.md`, `stage_admin-auth-data-business-validation.md` and `stage_dream-production-database-closure.md` still say implementation or source closure is pending. The target records the completed source cutover while keeping normal migration, service activation and real acceptance pending.
- The Thread SystemConfig plan contains an obsolete same-directory link. The target corrects it to `../../stage/stage_admin-user-system-config-domain.md`.

Copying any of these 16 source versions would reintroduce obsolete configuration, imports or state claims. The correct synchronization result is to retain the current target content.

## Verification

| Command | CWD | Exit/result |
| --- | --- | --- |
| `git merge-base --is-ancestor 7a6e6c9 HEAD` | Admin target | `0` |
| `git show --stat --oneline 7a6e6c9` | Admin source/target object database | 11 expected files |
| NUL-safe source status/hash comparison | Dream source | 399 total, 383 exact, 0 missing, 16 reviewed differences |
| Baseline three-way subsumption check | Dream source/target | 3 current differences reproduced target exactly |
| Source-only line review | Dream source/target | 13 current differences are superseded content; no unmerged business code |

The Dream source remains dirty by design, preserving user and prior-agent work. The Dream target retains its pre-existing untracked `.pnpm-store/`; this audit did not read, modify or remove it.
