"""Server-side Deck Plugin capability intersection evaluation."""

from __future__ import annotations

from collections.abc import Iterable


def _normalized(values: Iterable[str]) -> set[str]:
    """Return non-blank capability names without mutating caller-owned sets."""

    return {value.strip() for value in values if value.strip()}


def compute_effective_capabilities(
    manifest_requested: set[str],
    installation_approved: set[str],
    deck_runtime_snapshot_policy: set[str],
    user_and_workspace_grants: set[str],
    claude_agent_runtime_supported: set[str],
    *,
    known_capabilities: set[str] | None = None,
) -> set[str]:
    """Compute the five-domain least-privilege capability intersection.

    ClaudeAgent runtime support is the authoritative default capability registry.
    Callers may supply a narrower server-owned registry via ``known_capabilities``;
    a capability missing from that registry is denied even if another input names it.
    """

    requested = _normalized(manifest_requested)
    approved = _normalized(installation_approved)
    runtime_policy = _normalized(deck_runtime_snapshot_policy)
    grants = _normalized(user_and_workspace_grants)
    runtime_supported = _normalized(claude_agent_runtime_supported)
    known = (
        runtime_supported
        if known_capabilities is None
        else _normalized(known_capabilities) & runtime_supported
    )
    return requested & approved & runtime_policy & grants & runtime_supported & known
