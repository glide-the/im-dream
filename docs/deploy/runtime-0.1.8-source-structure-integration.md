<!-- [Input] Canonical Runtime src, its byte-exact reference, source-bound build and Dream version pins. -->
<!-- [Output] Record one original-module implementation and the atomic Dream metadata update. -->
<!-- [Pos] Current source integration note; not a publication, deployment or business acceptance receipt. -->
<!-- [Sync] 2026-09-13: supersede the incorrect 0.1.7 side-snapshot plus parallel Runtime arrangement. -->

# Runtime 0.1.8 — same directories, same modules

> Historical source-only integration, superseded by [Runtime 0.1.9 release and local Dream adoption](runtime-0.1.9-release-and-local-dream-adoption.md). Runtime 0.1.9 removes the duplicate `restored-src` directory and retains canonical original `src`; statements below describe the 0.1.8 stage only.

Runtime `src` and `restored-src/src` now have identical module paths, directory trees,
file modes and initial bytes: 1,902 files, 30,382,832 bytes, 35 original module directories.
Their content/mode inventory SHA-256 is
`40269454cd690c74d129a31699935d6db713f2958aabe4787e01617e1c92a906`.
Reference commit: `a8a678cb6244e6770e1e421767ff0987a1d95549`;
original subtree: `7640f58ea271eb60952ebdbe0dfa173fc96ebe30`.

The default Runtime build compiles `src/entrypoints/cli.tsx`. `src/cleanroom` and its
separate wrapper entrypoints are removed; the previous implementation is recoverable
from Runtime commit `38fdd3c`, not maintained as a second active implementation.
The build applies the existing source-bound headless and MCP compatibility transforms.
An external recovered dependency root supplies only `node_modules`/`vendor`, never another `src`.
The original source retains its copyright; successful integration does not grant redistribution.

Current source versions move atomically:

| Contract | Version |
| --- | --- |
| Runtime root, selector, native package expectations, Dream resolver, Docker and AutoDL | 0.1.8 |
| Dream backend project and uv virtual project lock | 0.1.2 |
| Dream frontend project | 0.0.2 |
| Python SDK (unchanged) | 0.2.145 |
| Dream-facing CLI compatibility (unchanged) | 2.1.241 |
| API schema (unchanged) | 2.0.0 |

Darwin ARM64 original-module compilation verified 1,989 inputs, 48 outputs, zero
resolution gaps and passing DCE assertions. Four native targets, fresh public registry
installation and real Dream business acceptance still require new same-byte receipts;
the old clean-room release/acceptance cannot qualify this implementation.

The 2026-09-13 registry observation `latest=0.1.4` is historical, not a claim that this
candidate has been published. Current exact `0.1.8` installation remains fail closed
until publication is separately authorized and qualified. No API, ZIP policy, database,
production process, installed Runtime, remote branch or release is changed by this source update.

The [0.1.7 note](runtime-0.1.7-source-structure-integration.md) is superseded: restoring a
side snapshot while retaining a redesigned implementation did not meet the requested contract.

## Local validation

Runtime default original-module build, SDK and stdio/HTTP MCP contracts, headless smoke
and two-build output reproducibility passed. Runtime unit suite: 32 passed/4 external
fixtures skipped; MCP compatibility: 52 passed/0 skipped, reading canonical src by default.
Dream project/version, resolver, Docker, synthetic registry verifier and startup suite:
62 passed plus 13 subtests, no failures/skips. Shell syntax and offline uv lock check
passed; only the virtual project's version changed in uv.lock, not SDK/dependency hashes.
README EN/ZH command/version/structure parity and 37 local link targets passed.
These are isolated local fixtures, not real-user business or registry release acceptance.
