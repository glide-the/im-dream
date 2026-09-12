<!-- [Input] Runtime's exact research snapshot, Dream project manifests, SDK/Runtime resolver, and public registry observation. -->
<!-- [Output] Explain version changes, source/licensing boundaries, validation, installation blockers, and rollback. -->
<!-- [Pos] Dream integration receipt for the unpublished Runtime 0.1.7 source-structure correction. -->
<!-- [Sync] 2026-09-13: update project metadata and the exact Runtime contract without deploying or changing business semantics. -->

# Runtime 0.1.7 source-structure integration

Runtime now preserves `claude-code-sourcemap/restored-src/src` exactly, rather than treating
an independently designed clean-room tree as the reference structure. The snapshot has 1,902 files,
30,382,832 bytes, and all 35 original module directories. Source commit is
`a8a678cb6244e6770e1e421767ff0987a1d95549`; Git subtree is
`7640f58ea271eb60952ebdbe0dfa173fc96ebe30`. Source files are not rewritten or renamed.

The snapshot is unofficial Anthropic-copyright research material, not MIT code or a redistribution
grant. It is excluded from the independent clean-room compile graph, npm staging/tarballs, and SBOM
provenance. Runtime's mixed-source root is private/`UNLICENSED`; clean-room artifacts remain MIT.
The incomplete unpublished `0.1.6` candidate is superseded by `0.1.7`.

Dream moves the exact Runtime contract, Docker pin, local-core deployment metadata, resolver/test
fixtures, and operator documentation atomically to `0.1.7`. SDK stays `0.2.145`; the compatibility
CLI output stays `2.1.241 (Claude Code)`. The existing strict package-root `cli.js` npm layout and
separately qualified nested-bin local-core layout remain unchanged.

Dream's own metadata receives a patch bump in its existing version sequences: backend `0.1.0` →
`0.1.1` (including the virtual project in `uv.lock`) and frontend `0.0.0` → `0.0.1`. Frontend's lock
does not encode the root project's version. API schema remains `2.0.0` because no API contract changes.
No SDK protocol, Agent lifecycle, MCP Apps work, ZIP policy, Schema, database, or user data is changed.

An explicit official-registry query on 2026-09-13 reports Runtime `latest=0.1.4`. `0.1.7` remains
unpublished with production/publication/redistribution/target gates closed. Current Dream source
rejects an older or fixture-only Runtime. Docker and registry acceptance therefore fail closed until
the same-SHA qualified five-package release exists. Operators should retain their last qualified
branch/image; no ambient CLI fallback or version override is introduced.

Validation must cover project/lock metadata, Docker/version pins, strict resolver layouts/digests,
startup identity, the actual resolver against freshly installed fixture packages, AutoDL topology,
and mirrored README version/command facts. Provider-free fixtures prove technical contracts only.
Historical `0.1.4` release and `0.1.5` acceptance evidence cannot authorize `0.1.7`.

## Local validation on 2026-09-13

The project-version, SDK environment, Docker pin, and registry-verifier tests exited 0:
60 passed plus 13 subtests. The two focused startup identity/factory lifecycle tests passed
(21 existing FastAPI deprecation warnings). AutoDL topology and shell syntax checks passed.
`uv export --locked --offline --no-dev --format requirements-txt` succeeded against the existing
cache; all 1,016 non-comment/non-blank dependency and hash lines match `backend/requirements.txt`.
No dependency install or lock re-resolution was needed.

English/Chinese README checks found the same 26-heading level sequence, 13 code blocks,
15 link targets, and identical version-number multiset. The only code-block differences are
translated comments; the only link-target difference is the matching localized build/test anchor.
Commands, versions, and destination facts therefore remain mirrored.

Runtime's full isolated Node suite passed 132 of 136 tests with zero failures and four external
comparator/pinned-OAuth-fixture skips. The four-target/five-package fresh-install lane ran against
this Dream checkout's actual resolver; temporary fixture packages remain publication-blocked.
Runtime's authorized-source compatibility replay passed 52/52 with no skips. Its SDK contract,
provider-free acceptance, release inventory, and two-pass reproducibility checks passed; the SDK
was not modified. None of these technical checks reopens the real-business/publication gates.

This change is local-only: no push, publish, deploy, service restart, migration, or external mutation.
Rollback is the last qualified Dream branch/image and its exact Runtime, not a mismatched package
on current source or an unreviewed `CLAUDE_CODE_CLI_PATH` bypass.
