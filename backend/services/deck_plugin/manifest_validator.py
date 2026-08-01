"""Validation for Deck Plugin v1 manifests."""

from __future__ import annotations

import re
import sqlite3
from collections.abc import Iterable, Mapping
from typing import Any

from pydantic import ValidationError

try:
    from backend.models.deck_plugin import DeckPluginManifestV1, SEMVER_PATTERN
except ModuleNotFoundError:  # Support the backend directory on PYTHONPATH.
    from models.deck_plugin import DeckPluginManifestV1, SEMVER_PATTERN


DECK_PLUGIN_MANIFEST_INVALID = "DECK_PLUGIN_MANIFEST_INVALID"
DECK_PLUGIN_SOURCE_DENIED = "DECK_PLUGIN_SOURCE_DENIED"

STABLE_ID_PATTERN = re.compile(
    r"^[a-z0-9](?:[a-z0-9-]*[a-z0-9])?"
    r"(?:\.[a-z0-9](?:[a-z0-9-]*[a-z0-9])?)+$"
)
VERSIONED_SCHEMA_REF_PATTERN = re.compile(
    r"^schema://[^\s]+(?:/|@)v?(?:0|[1-9]\d*)"
    r"(?:\.(?:0|[1-9]\d*)){0,2}(?:[-+][0-9A-Za-z.-]+)?$"
)
PLAINTEXT_SECRET_PATTERNS = (
    re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----"),
    re.compile(r"\bsk-ant-[A-Za-z0-9_-]{12,}\b"),
    re.compile(r"\bAKIA[0-9A-Z]{16}\b"),
    re.compile(r"\bBearer\s+[A-Za-z0-9._~+/=-]{12,}\b", re.IGNORECASE),
)
SENSITIVE_KEYS = {
    "api_key",
    "apikey",
    "access_token",
    "auth_token",
    "credential",
    "credentials",
    "password",
    "private_key",
    "secret",
    "secret_key",
    "system_prompt",
    "full_prompt",
    "prompt",
}


class DeckPluginValidationError(ValueError):
    """A manifest validation failure with a stable API error code."""

    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code = code
        self.message = message


def is_valid_semver(value: str) -> bool:
    """Return whether *value* follows SemVer 2.0.0 syntax."""

    return bool(SEMVER_PATTERN.fullmatch(value))


def _invalid(message: str) -> DeckPluginValidationError:
    return DeckPluginValidationError(DECK_PLUGIN_MANIFEST_INVALID, message)


def _assert_no_sensitive_payload(value: Any, path: str = "manifest") -> None:
    if isinstance(value, Mapping):
        for key, nested_value in value.items():
            normalized_key = str(key).strip().lower().replace("-", "_")
            if normalized_key in SENSITIVE_KEYS:
                raise _invalid(f"plaintext secret or prompt field is forbidden at {path}.{key}")
            _assert_no_sensitive_payload(nested_value, f"{path}.{key}")
        return
    if isinstance(value, (list, tuple)):
        for index, nested_value in enumerate(value):
            _assert_no_sensitive_payload(nested_value, f"{path}[{index}]")
        return
    if isinstance(value, str):
        for pattern in PLAINTEXT_SECRET_PATTERNS:
            if pattern.search(value):
                raise _invalid(f"plaintext secret material is forbidden at {path}")


def _source_is_allowed(source_ref: str, allowlist: set[str]) -> bool:
    return any(
        source_ref == allowed or source_ref.startswith(f"{allowed}@")
        for allowed in allowlist
    )


def _assert_unique(
    db: sqlite3.Connection,
    manifest: DeckPluginManifestV1,
    exclude_release_id: str | None,
) -> None:
    query = (
        "SELECT id FROM deck_plugin_releases "
        "WHERE deck_plugin_id = ? AND deck_plugin_version = ?"
    )
    params: list[str] = [manifest.deck_plugin_id, manifest.deck_plugin_version]
    if exclude_release_id is not None:
        query += " AND id <> ?"
        params.append(exclude_release_id)
    if db.execute(query, params).fetchone() is not None:
        raise _invalid(
            "deck_plugin_id and deck_plugin_version must identify a unique release"
        )


def validate_manifest(
    manifest: DeckPluginManifestV1 | Mapping[str, Any],
    *,
    source_allowlist: Iterable[str],
    db: sqlite3.Connection | None = None,
    exclude_release_id: str | None = None,
    production: bool = True,
) -> DeckPluginManifestV1:
    """Validate schema, references, capabilities, sources, and integrity."""

    raw_manifest: Any
    if isinstance(manifest, DeckPluginManifestV1):
        raw_manifest = manifest.model_dump(mode="json")
    else:
        raw_manifest = manifest
    _assert_no_sensitive_payload(raw_manifest)

    try:
        parsed = (
            manifest
            if isinstance(manifest, DeckPluginManifestV1)
            else DeckPluginManifestV1.model_validate(manifest)
        )
    except ValidationError as exc:
        raise _invalid(f"manifest schema validation failed: {exc}") from exc

    if not STABLE_ID_PATTERN.fullmatch(parsed.deck_plugin_id):
        raise _invalid("deck_plugin_id must be a stable dotted lowercase identifier")
    if not is_valid_semver(parsed.deck_plugin_version):
        raise _invalid("deck_plugin_version must follow SemVer 2.0.0")

    workflow_ref = parsed.workflow.workflow_definition_ref
    expected_prefix = f"deck://{parsed.deck_plugin_id}/{parsed.deck_plugin_version}/"
    if "latest" in workflow_ref.lower() or not workflow_ref.startswith(expected_prefix):
        raise _invalid(
            "workflow_definition_ref must be a controlled, version-pinned deck:// reference"
        )
    for field_name, schema_ref in (
        ("input_schema_ref", parsed.workflow.input_schema_ref),
        ("output_schema_ref", parsed.workflow.output_schema_ref),
    ):
        if "latest" in schema_ref.lower() or not VERSIONED_SCHEMA_REF_PATTERN.fullmatch(
            schema_ref
        ):
            raise _invalid(f"{field_name} must be an explicitly versioned schema:// reference")
    if not is_valid_semver(parsed.compatibility.deck_runtime_snapshot_contract):
        raise _invalid("deck_runtime_snapshot_contract must be an explicit SemVer version")

    capabilities = set(parsed.capabilities)
    for step in parsed.workflow.steps:
        missing = set(step.required_capabilities) - capabilities
        if missing:
            raise _invalid(
                f"workflow step {step.step_id!r} requires undeclared capabilities: "
                f"{sorted(missing)}"
            )
    for plugin in parsed.runtime.claude_code_plugins:
        missing = set(plugin.capability_bindings) - capabilities
        if missing:
            raise _invalid(
                f"runtime plugin {plugin.claude_code_plugin_id!r} binds undeclared "
                f"capabilities: {sorted(missing)}"
            )

    optional_plugins = [
        plugin.claude_code_plugin_id
        for plugin in parsed.runtime.claude_code_plugins
        if not plugin.required
    ]
    if optional_plugins and not parsed.runtime.degraded_modes:
        raise _invalid("optional runtime plugins require an explicit degraded mode")

    if production:
        allowlist = {source.rstrip("/") for source in source_allowlist if source.strip()}
        for plugin in parsed.runtime.claude_code_plugins:
            source_ref = plugin.source_ref.rstrip("/")
            if source_ref.startswith(("file://", "local://", "/")):
                raise DeckPluginValidationError(
                    DECK_PLUGIN_SOURCE_DENIED,
                    f"local source is forbidden in production: {plugin.source_ref}",
                )
            if not _source_is_allowed(source_ref, allowlist):
                raise DeckPluginValidationError(
                    DECK_PLUGIN_SOURCE_DENIED,
                    f"runtime source is not in the administrator allowlist: {plugin.source_ref}",
                )

    if db is not None:
        _assert_unique(db, parsed, exclude_release_id)
    return parsed
