"""Shared Claude Code plugin installation, artifact store, and workspace packing.

Architecture (deck-integration-delta §Plugin Install & Pack):

    Settings / Plugin Admin
        → shared managed install workspace (real `claude plugin install`)
        → shared immutable artifact store (<pkg>@<marketplace>@sha256-<digest>)
        → Deck stores installation *references* only
        → Deck Chat creation packs artifacts into the agent workspace
        → Claude CLI launches with literal `--plugin-dir` args

Nothing in this package accepts a filesystem path, settings JSON, or
``--plugin-dir`` value from a client request.  Every artifact is produced by
the real Claude CLI inside the server-managed runtime root (or by a
server-declared platform-builtin source) and pinned by SHA-256 digest.
"""
