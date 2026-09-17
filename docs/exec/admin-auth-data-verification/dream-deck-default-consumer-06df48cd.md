<!-- [Input] Dream Registry104 commit, provider-free Deck/Voice tests and corrected source-only AST inventory. -->
<!-- [Output] Reproducible DTO/evidence/receipt/runtime-fence verification with exact command outcomes. -->
<!-- [Pos] Coordinator technical receipt; no real PostgreSQL, Google account, plugin download or model call. -->
<!-- [Sync] 2026-09-15: record Dream commit 06df48cd and its deterministic validation. -->

# Dream Registry104 Deck-default consumer

## Source

- Worktree: `/Users/dmeck/.codex/worktrees/ef6e/ink-dream-memory`
- Branch: `codex/dream-admin-auth-data-client`
- Commit: `06df48cd` (`refactor: migrate deck defaults to Admin Registry104`)
- Tree: `59d619323a089cc33f0a192ba62e80a38214e523`
- Admin source commit: `27b6fc9e3a7a42ea7329efb6e5832295d04ae346`
- Operations: `deck.default-plugin.resolve`, `deck.create`, `deck.reconcile-default`, `deck.provision-default`

The browser DTO contains only editable Deck fields. Admin selects a nullable six-field ready installation, Dream runs the existing shared-artifact and Claude CLI compatibility checks, then sends the resulting four-field evidence to one Admin write transaction. Admin rechecks the configured package/version and locked installation row. Write transport uncertainty triggers one receipt lookup with the original request ID and never resends the write.

## Validation receipts

All commands ran from the worktree above.

```text
PYTHONPATH=backend uv run --native-tls --project backend --frozen --with pytest==9.1.1 --with pytest-asyncio python -m pytest backend/tests/test_deck_defaults.py backend/tests/test_admin_deck_default_routes.py backend/tests/test_admin_request_auth.py -q
exit: 0
61 passed in 0.72s
```

```text
PYTHONPATH=backend uv run --native-tls --project backend --frozen --with pytest==9.1.1 --with pytest-asyncio python -m pytest backend/tests/test_admin_deck_default_routes.py backend/tests/test_admin_deck_detail_routes.py backend/tests/test_admin_deck_list_routes.py backend/tests/test_admin_deck_mutation_routes.py backend/tests/test_admin_deck_refs_routes.py backend/tests/test_admin_deck_version_routes.py backend/tests/test_admin_voice_routes.py backend/tests/test_deck_defaults.py backend/tests/test_deck_deletion.py backend/tests/test_deck_sharing_policy.py -q
exit: 0
307 passed in 2.60s
```

```text
PYTHONPATH=backend uv run --native-tls --project backend --frozen --with pytest==9.1.1 --with pytest-asyncio python -m pytest backend/tests/test_admin_data_boundary.py backend/tests/test_admin_request_auth.py -q
exit: 0
98 passed in 0.98s
```

```text
python3 /private/tmp/ink-auth-migration-validation/scan-dream-db-closure-after-default-registry104-v2.py
exit: 0
scanned_python_modules: 528
production_entries: 80
production_driver_or_database_import_modules: 31
production_legacy_helper_calls: 56
production_admin_data_import_modules: 28
admin_data_operation_names: 121
parse_errors: []
```

The AST scan explicitly excludes `backend/.venv` and `__pycache__`; the initial unfiltered run counted dependency source and is not acceptance evidence. Relative to commit `101fce6e`, the corrected scan reduces production database-import modules from 32 to 31 and legacy helper calls from 60 to 56 while adding the four Registry104 operation names. `backend/routers/voices.py` retains one `database.DeckDeletionConflict` type/message reference for an already-migrated delete error; the create and default-reconcile execution paths contain no Dream database call.

This is isolated technical verification. It does not claim real Google login, normal PostgreSQL business visibility, a real plugin download, or a real model run.
