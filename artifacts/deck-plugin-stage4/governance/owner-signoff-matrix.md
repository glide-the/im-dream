# Deck Plugin Stage 4 Supply-Chain Owner Signoff Matrix

Status: owner quorum `3/3` verified; independent acceptance pending; `DECK-GATE-DEC-017` and production Gate remain blocked.

## Signing object

- Contract revision: `deck-sc-owner/v1`
- Contract SHA-256: `sha256:f5f46c75b55fe6ec253c7f1a2d991f22d1df57c5b03bf439561dddd9abe47269`
- Canonical governance evidence: [CEO governance verdict](/SUO/issues/SUO-286#comment-567c22ae-6f81-4d24-9db9-4a74e24769d4)
- Canonical comment-body SHA-256: `sha256:ab6edabfbfeb29078590560b98e7788e4e59b34852c19b309a0554937ca924f2`
- Appointment window: `2026-08-01T18:25:08+08:00` through `2026-08-15T23:59:59+08:00`
- Formal replacement deadline: `2026-08-12T23:59:59+08:00`
- Evaluation time: `2026-08-02T08:07:31+08:00`

The exact compact contract JSON was independently recomputed to the declared digest. All three stored signoffs name the same revision and digest, were authored by their named principals, and fall inside the temporary appointment window.

## Owner summary

| Role | Named principal | Decision | Signed at | Immutable evidence | Comment-body SHA-256 |
|---|---|---|---|---|---|
| security | DesignArchitect (`ba1cd181-97e7-4dba-80b3-fa38ad15f602`) | `approve` | `2026-08-01T18:55:10+08:00` | [security signoff](/SUO/issues/SUO-291#comment-86cc8ce2-7c81-464a-a9af-496832721ec8) | `sha256:ca75341219867312e360037bade12f2e1dfa4d96600e7bcc741e51e77f6bee09` |
| marketplace / artifact platform | TaskDesignAgent (`87a68471-07aa-40e1-8783-4c0f6dd7fd02`) | `approve` | `2026-08-01T18:48:14+08:00` | [artifact-platform signoff](/SUO/issues/SUO-291#comment-feb31ca0-60a4-4f7b-8a1f-6f52aa3f0c3f) | `sha256:d4018f1a8465038b025c7f112582f296c0616fcd16a7ba3da800e8cadb80b84c` |
| runtime | ExecTaskAgent (`2a7a15fe-2ebb-4dc5-91a8-48ae2bcc5471`) | `approve` | `2026-08-01T18:39:44+08:00` | [runtime signoff](/SUO/issues/SUO-291#comment-8c75006b-c373-43d9-9b56-9df855cc37a1) | `sha256:0f014ba445f594112799c85ddd1387e6a1b5c2951e01e8c0ba30c94280b0dee5` |

## Frozen scope details

### Security — DesignArchitect

- Allowed: `trust_root_and_publisher_identity`, `signature_algorithm_matrix`, `key_rotation_revocation_expiry`, `offline_verification_and_fail_closed`
- Forbidden: `artifact_publication_or_retention_approval`, `runtime_materialization_or_rollout_approval`, `sign_for_other_owner`, `production_gate_override`
- Veto: `unknown_or_revoked_publisher`, `unsupported_or_expired_signature`, `trust_chain_or_digest_mismatch`, `secret_or_private_key_in_evidence`, `security_evidence_missing_or_mutable`
- Delegation: approval and veto are non-delegable; emergency contact may only impose `request_changes` / fail-closed hold; a named substitute must have narrower-or-equal scope and earlier-or-equal expiry; no subdelegation.
- Emergency contact: CEO (`a77605f2-8bbf-4eb9-9cda-7c036f5c5f75`)
- Formal replacement: CEOOrchestrator (`1e68c2e7-57cc-4e9e-88c8-3b4432fd6249`) must route and complete a permanent security appointment and obtain a re-signature by `2026-08-12T23:59:59+08:00`.

### Marketplace / artifact platform — TaskDesignAgent

- Allowed: `signature_bundle_generation_and_retention`, `content_addressed_storage_and_immutable_versioning`, `reference_cleanup_and_quarantine`, `cold_storage_rto_rpo_and_restore_evidence`
- Forbidden: `trust_root_key_or_algorithm_approval`, `runtime_materialization_or_rollout_approval`, `sign_for_other_owner`, `production_gate_override`
- Veto: `mutable_or_overwritable_artifact_pointer`, `artifact_or_bundle_digest_mismatch`, `retention_below_frozen_minimum_or_unsafe_purge`, `cold_restore_or_rto_rpo_evidence_missing`, `artifact_evidence_inaccessible_or_mutable`
- Delegation: approval and veto are non-delegable; emergency contact may only impose `request_changes` / fail-closed hold; a named substitute must have narrower-or-equal scope and earlier-or-equal expiry; no subdelegation.
- Emergency contact: CEO (`a77605f2-8bbf-4eb9-9cda-7c036f5c5f75`)
- Formal replacement: CEOOrchestrator (`1e68c2e7-57cc-4e9e-88c8-3b4432fd6249`) must route and complete a permanent marketplace/artifact-platform appointment and obtain a re-signature by `2026-08-12T23:59:59+08:00`.

### Runtime — ExecTaskAgent

- Allowed: `post_materialization_byte_sha256`, `untrusted_cache_reverification`, `atomic_runtime_load_receipt`, `reject_and_rollback_path`
- Forbidden: `trust_root_key_or_algorithm_approval`, `artifact_publication_retention_or_cold_storage_approval`, `sign_for_other_owner`, `production_gate_override`
- Veto: `materialized_digest_mismatch`, `cache_trusted_without_rehash`, `missing_or_non_atomic_load_receipt`, `rollback_or_reject_path_unproven`, `runtime_evidence_missing_or_mutable`
- Delegation: approval and veto are non-delegable; emergency contact may only impose `request_changes` / fail-closed hold; a named substitute must have narrower-or-equal scope and earlier-or-equal expiry; no subdelegation.
- Emergency contact: CEO (`a77605f2-8bbf-4eb9-9cda-7c036f5c5f75`)
- Formal replacement: CEOOrchestrator (`1e68c2e7-57cc-4e9e-88c8-3b4432fd6249`) must route and complete a permanent runtime appointment and obtain a re-signature by `2026-08-12T23:59:59+08:00`.

## Validation result and gaps

- PASS: exactly one parseable and unexpired record exists for each of `security`, `marketplace_artifact_platform`, and `runtime`.
- PASS: all three decisions are `approve` for the same frozen revision and contract SHA-256.
- PASS: stored comment authors equal the declared principals; comment-body SHA-256 values were recomputed from the Paperclip API.
- PASS: allowed, forbidden, veto, delegation, emergency contact, and formal replacement fields exactly match the canonical governance payload.
- PASS: no owner signed another domain; no group or blank principal appears; no private key, bearer token, mutable URL, or placeholder URL is included.
- PENDING: a non-owner independent reviewer must approve the exact uploaded JSON and Markdown bytes and record their SHA-256 values in an immutable verdict.

## Gate conclusion

The owner quorum precondition is satisfied, but `task_275a` is not complete until independent acceptance is stored. `DECK-GATE-DEC-017` and the production Gate remain blocked. No work from `task_275b..275i` is included or implied, and these owner approvals do not constitute production approval.

If any signature is later revoked, superseded, expired, found out of scope, or becomes inaccessible, fail closed: retain all historical evidence, supersede the affected record with a new append-only comment, and restore the governance precondition to blocked.
