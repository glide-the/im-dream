"""Fail-closed Deck Plugin degradation evaluation.

The manifest only names degraded modes.  The server-owned mode catalogue below
supplies the replacement steps and the exact omissions each named mode permits;
callers cannot invent those details at preflight time.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

try:
    from backend.models.deck_plugin import DeckPluginManifestV1
except ModuleNotFoundError:  # Support running with ``backend`` on PYTHONPATH.
    from models.deck_plugin import DeckPluginManifestV1


DEGRADATION_NOT_DECLARED = "DEGRADATION_NOT_DECLARED"
DEGRADATION_REQUIRED_PLUGIN_MISSING = "DEGRADATION_REQUIRED_PLUGIN_MISSING"
DEGRADATION_PERMISSION_DENIED = "DEGRADATION_PERMISSION_DENIED"
DEGRADATION_SECURITY_REVOCATION = "SECURITY_REVOCATION"
DEGRADATION_OUTPUT_SCHEMA_MISMATCH = "DEGRADATION_OUTPUT_SCHEMA_MISMATCH"
DEGRADATION_NO_MATCHING_MODE = "DEGRADATION_NO_MATCHING_MODE"


@dataclass(frozen=True)
class DegradedModeDefinition:
    """Server-owned semantics for one manifest-declared mode."""

    degraded_mode_id: str
    optional_plugin_ids: frozenset[str]
    omittable_capabilities: frozenset[str]
    replacement_steps: tuple[str, ...]
    output_schema_ref: str
    user_confirmation_required: bool = True

    def __post_init__(self) -> None:
        if not self.degraded_mode_id.strip():
            raise ValueError("degraded_mode_id is required")
        if not self.replacement_steps:
            raise ValueError("a degraded mode must define replacement steps")
        if not self.output_schema_ref.strip():
            raise ValueError("output_schema_ref is required")


@dataclass(frozen=True)
class DegradationResult:
    allowed: bool
    degraded_mode_id: str | None
    replacement_steps: tuple[str, ...]
    missing_plugins: tuple[str, ...]
    missing_capabilities: tuple[str, ...]
    output_schema_ref: str
    user_confirmation_required: bool
    runtime_load_receipt_required: bool
    error_code: str | None = None
    reason: str | None = None


class DegradationService:
    """Choose only an explicitly declared and schema-preserving degraded mode."""

    def __init__(self, mode_definitions: Iterable[DegradedModeDefinition] = ()) -> None:
        definitions = tuple(mode_definitions)
        self._definitions = {item.degraded_mode_id: item for item in definitions}
        if len(self._definitions) != len(definitions):
            raise ValueError("degraded_mode_id values must be unique")

    async def evaluate_degradation(
        self,
        manifest: DeckPluginManifestV1,
        missing_plugins: list[str],
        missing_capabilities: list[str],
        *,
        capability_authorization_satisfied: bool = True,
        security_revoked: bool = False,
    ) -> DegradationResult:
        """Return a deterministic preflight result without weakening policy.

        A successful result still requires explicit user confirmation and a
        runtime load receipt carrying ``degraded_mode_id``.  This service does
        not mutate a Workflow Run.
        """

        missing_plugin_set = self._normalized(missing_plugins, "missing_plugins")
        missing_capability_set = self._normalized(
            missing_capabilities, "missing_capabilities"
        )
        output_schema = manifest.workflow.output_schema_ref

        if security_revoked:
            return self._denied(
                DEGRADATION_SECURITY_REVOCATION,
                "security-revoked objects cannot be automatically degraded",
                missing_plugin_set,
                missing_capability_set,
                output_schema,
            )
        if not capability_authorization_satisfied:
            return self._denied(
                DEGRADATION_PERMISSION_DENIED,
                "missing capability authorization cannot be bypassed by degradation",
                missing_plugin_set,
                missing_capability_set,
                output_schema,
            )

        declared_modes = tuple(dict.fromkeys(manifest.runtime.degraded_modes))
        if not declared_modes:
            return self._denied(
                DEGRADATION_NOT_DECLARED,
                "the manifest declares no degraded_modes",
                missing_plugin_set,
                missing_capability_set,
                output_schema,
            )

        plugins = {
            item.claude_code_plugin_id: item
            for item in manifest.runtime.claude_code_plugins
        }
        required_missing = sorted(
            plugin_id
            for plugin_id in missing_plugin_set
            if plugin_id not in plugins or plugins[plugin_id].required
        )
        if required_missing:
            return self._denied(
                DEGRADATION_REQUIRED_PLUGIN_MISSING,
                "required or unknown runtime plugins cannot be omitted",
                missing_plugin_set,
                missing_capability_set,
                output_schema,
            )

        candidates: list[DegradedModeDefinition] = []
        schema_mismatch = False
        for mode_id in sorted(declared_modes):
            definition = self._definitions.get(mode_id)
            if definition is None:
                continue
            if definition.output_schema_ref != output_schema:
                schema_mismatch = True
                continue
            if not missing_plugin_set.issubset(definition.optional_plugin_ids):
                continue
            if not missing_capability_set.issubset(
                definition.omittable_capabilities
            ):
                continue
            candidates.append(definition)

        if not candidates:
            error_code = (
                DEGRADATION_OUTPUT_SCHEMA_MISMATCH
                if schema_mismatch
                else DEGRADATION_NO_MATCHING_MODE
            )
            reason = (
                "declared degraded modes do not preserve the workflow output schema"
                if schema_mismatch
                else "no declared degraded mode permits the exact missing inputs"
            )
            return self._denied(
                error_code,
                reason,
                missing_plugin_set,
                missing_capability_set,
                output_schema,
            )

        # Prefer the least permissive matching definition, then a stable ID.
        selected = min(
            candidates,
            key=lambda item: (
                len(item.optional_plugin_ids) + len(item.omittable_capabilities),
                item.degraded_mode_id,
            ),
        )
        return DegradationResult(
            allowed=True,
            degraded_mode_id=selected.degraded_mode_id,
            replacement_steps=selected.replacement_steps,
            missing_plugins=tuple(sorted(missing_plugin_set)),
            missing_capabilities=tuple(sorted(missing_capability_set)),
            output_schema_ref=output_schema,
            user_confirmation_required=selected.user_confirmation_required,
            runtime_load_receipt_required=True,
        )

    @staticmethod
    def _normalized(values: Iterable[str], field: str) -> frozenset[str]:
        normalized = frozenset(item.strip() for item in values)
        if "" in normalized:
            raise ValueError(f"{field} must not contain blank values")
        return normalized

    @staticmethod
    def _denied(
        error_code: str,
        reason: str,
        missing_plugins: frozenset[str],
        missing_capabilities: frozenset[str],
        output_schema_ref: str,
    ) -> DegradationResult:
        return DegradationResult(
            allowed=False,
            degraded_mode_id=None,
            replacement_steps=(),
            missing_plugins=tuple(sorted(missing_plugins)),
            missing_capabilities=tuple(sorted(missing_capabilities)),
            output_schema_ref=output_schema_ref,
            user_confirmation_required=False,
            runtime_load_receipt_required=False,
            error_code=error_code,
            reason=reason,
        )
