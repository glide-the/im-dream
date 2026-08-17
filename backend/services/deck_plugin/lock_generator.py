"""Resolve Deck Plugin runtime dependencies into an immutable release lock."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import hashlib
import json
import re
from typing import Iterable, Protocol
import uuid

try:
    from backend.models.deck_plugin import (
        DeckPluginManifestV1,
        DeckRuntimePluginLock,
        RuntimePluginLockEntry,
        SEMVER_PATTERN,
    )
except ModuleNotFoundError:  # Support the backend directory on PYTHONPATH.
    from models.deck_plugin import (
        DeckPluginManifestV1,
        DeckRuntimePluginLock,
        RuntimePluginLockEntry,
        SEMVER_PATTERN,
    )


RUNTIME_PLUGIN_UNRESOLVED = "RUNTIME_PLUGIN_UNRESOLVED"
RUNTIME_MARKETPLACE_UNAVAILABLE = "RUNTIME_MARKETPLACE_UNAVAILABLE"
RUNTIME_PLUGIN_LOCK_IMMUTABLE = "RUNTIME_PLUGIN_LOCK_IMMUTABLE"


class RuntimePluginLockError(ValueError):
    def __init__(self, code: str, message: str) -> None:
        self.code = code
        super().__init__(message)


class MarketplaceUnavailableError(RuntimeError):
    """Raised by a resolver when its backing marketplace cannot be queried."""


@dataclass(frozen=True)
class ResolvedPluginArtifact:
    resolved_version: str
    source_ref: str
    artifact_digest: str = ""
    supply_chain_verified: bool = False


class MarketplaceResolver(Protocol):
    def available_versions(
        self,
        claude_code_plugin_id: str,
        source_ref: str,
    ) -> Iterable[ResolvedPluginArtifact]: ...


@dataclass(frozen=True, order=True)
class _SemVer:
    major: int
    minor: int
    patch: int
    prerelease_rank: tuple = ()

    @classmethod
    def parse(cls, value: str) -> "_SemVer":
        if not SEMVER_PATTERN.fullmatch(value):
            raise ValueError(f"not an exact SemVer version: {value}")
        core_and_prerelease = value.split("+", 1)[0]
        core, separator, prerelease = core_and_prerelease.partition("-")
        major, minor, patch = (int(part) for part in core.split("."))
        if not separator:
            rank = ((2, ""),)
        else:
            rank = tuple(
                (0, int(part)) if part.isdigit() else (1, part)
                for part in prerelease.split(".")
            )
        return cls(major, minor, patch, rank)


def _comparison_predicate(token: str):
    match = re.fullmatch(r"(>=|<=|>|<|=)?(.+)", token)
    if match is None:
        raise ValueError(f"invalid SemVer comparator: {token}")
    operator = match.group(1) or "="
    expected = _SemVer.parse(match.group(2))
    return operator, expected


def version_satisfies_constraint(version: str, constraint: str) -> bool:
    """Return whether an exact SemVer satisfies the supported range syntax."""

    candidate = _SemVer.parse(version)
    wildcard = re.fullmatch(r"(0|[1-9]\d*)\.(0|[1-9]\d*)\.(?:x|X|\*)", constraint)
    if wildcard:
        return candidate.major == int(wildcard.group(1)) and candidate.minor == int(
            wildcard.group(2)
        )

    tokens = constraint.replace(",", " ").split()
    if not tokens:
        raise ValueError("version constraint is empty")
    for token in tokens:
        operator, expected = _comparison_predicate(token)
        if operator == ">=" and not candidate >= expected:
            return False
        if operator == "<=" and not candidate <= expected:
            return False
        if operator == ">" and not candidate > expected:
            return False
        if operator == "<" and not candidate < expected:
            return False
        if operator == "=" and not candidate == expected:
            return False
    return True


def _canonical_manifest_hash(manifest: DeckPluginManifestV1) -> str:
    manifest_json = json.dumps(
        manifest.model_dump(mode="json"),
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    )
    return f"sha256:{hashlib.sha256(manifest_json.encode('utf-8')).hexdigest()}"


def _immutable_lock_content(lock: DeckRuntimePluginLock) -> dict:
    content = lock.model_dump(mode="json")
    content.pop("runtime_plugin_lock_id", None)
    content.pop("created_at", None)
    return content


def verify_lock_immutability(
    existing_lock: DeckRuntimePluginLock,
    new_lock: DeckRuntimePluginLock,
) -> bool:
    """Compare immutable release-bound content, excluding identity/timestamp."""

    return _immutable_lock_content(existing_lock) == _immutable_lock_content(new_lock)


class LockGenerator:
    def __init__(self, *, production_gate_passed: bool = False) -> None:
        self.production_gate_passed = production_gate_passed

    def generate_lock(
        self,
        manifest: DeckPluginManifestV1,
        marketplace_resolver: MarketplaceResolver,
    ) -> DeckRuntimePluginLock:
        """Resolve every declared runtime dependency to the highest matching version."""

        entries: list[RuntimePluginLockEntry] = []
        readiness_reasons: list[str] = []
        for plugin in manifest.runtime.claude_code_plugins:
            try:
                candidates = list(
                    marketplace_resolver.available_versions(
                        plugin.claude_code_plugin_id,
                        plugin.source_ref,
                    )
                )
            except MarketplaceUnavailableError as exc:
                raise RuntimePluginLockError(
                    RUNTIME_MARKETPLACE_UNAVAILABLE,
                    f"marketplace unavailable for {plugin.claude_code_plugin_id}",
                ) from exc
            except Exception as exc:
                raise RuntimePluginLockError(
                    RUNTIME_MARKETPLACE_UNAVAILABLE,
                    f"marketplace resolver failed for {plugin.claude_code_plugin_id}",
                ) from exc

            try:
                matches = [
                    candidate
                    for candidate in candidates
                    if version_satisfies_constraint(
                        candidate.resolved_version,
                        plugin.version_constraint,
                    )
                ]
            except ValueError as exc:
                raise RuntimePluginLockError(
                    RUNTIME_PLUGIN_UNRESOLVED,
                    f"invalid version constraint for {plugin.claude_code_plugin_id}",
                ) from exc
            if not matches:
                raise RuntimePluginLockError(
                    RUNTIME_PLUGIN_UNRESOLVED,
                    f"no version matches {plugin.version_constraint} for "
                    f"{plugin.claude_code_plugin_id}",
                )
            selected = max(matches, key=lambda candidate: _SemVer.parse(candidate.resolved_version))
            digest = selected.artifact_digest.strip().lower()
            if not digest:
                readiness_reasons.append(
                    f"{plugin.claude_code_plugin_id}: immutable artifact digest missing"
                )
            elif not re.fullmatch(r"sha256:[0-9a-f]{64}", digest):
                raise RuntimePluginLockError(
                    RUNTIME_PLUGIN_UNRESOLVED,
                    f"invalid artifact digest for {plugin.claude_code_plugin_id}",
                )
            if not selected.supply_chain_verified:
                readiness_reasons.append(
                    f"{plugin.claude_code_plugin_id}: production supply-chain evidence missing"
                )
            entries.append(
                RuntimePluginLockEntry(
                    claude_code_plugin_id=plugin.claude_code_plugin_id,
                    resolved_version=selected.resolved_version,
                    source_ref=selected.source_ref,
                    artifact_digest=digest,
                    required=plugin.required,
                    capability_bindings=plugin.capability_bindings,
                )
            )

        if not self.production_gate_passed:
            readiness_reasons.append("production supply-chain gate has not passed")
        readiness_reasons = list(dict.fromkeys(readiness_reasons))
        return DeckRuntimePluginLock(
            runtime_plugin_lock_id=f"rpl_{uuid.uuid4().hex}",
            deck_plugin_id=manifest.deck_plugin_id,
            deck_plugin_version=manifest.deck_plugin_version,
            deck_plugin_manifest_hash=_canonical_manifest_hash(manifest),
            claude_code_plugins=entries,
            created_at=datetime.now(timezone.utc),
            production_ready=not readiness_reasons,
            production_readiness_reasons=readiness_reasons,
        )
