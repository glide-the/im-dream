# [Input] Deck capability declarations, server grants and public compatibility result models.
# [Output] Pure least-privilege intersection and canonical model validation evidence.
# [Pos] Provider-free Deck capability policy tests; compatibility persistence belongs to Admin.
# [Sync] 2026-09-16: retire the duplicate SQLite CompatibilityService authority.
"""Pure Deck capability intersection and compatibility-model contracts."""

from __future__ import annotations

import unittest

from pydantic import ValidationError

from backend.models.deck_plugin import (
    CapabilityDiff,
    CompatibilityCheck,
    CompatibilityResult,
)
from backend.services.deck_plugin.capability_evaluator import (
    compute_effective_capabilities,
)


class CapabilityEvaluatorTests(unittest.TestCase):
    def test_effective_capabilities_are_the_strict_five_domain_intersection(self):
        result = compute_effective_capabilities(
            {"story.context.read", "story.result.produce", "unknown.capability"},
            {"story.context.read", "story.result.produce", "unknown.capability"},
            {"story.context.read", "story.result.produce", "unknown.capability"},
            {"story.context.read", "story.result.produce", "unknown.capability"},
            {"story.context.read", "story.result.produce"},
        )
        self.assertEqual(result, {"story.context.read", "story.result.produce"})

    def test_server_registry_can_only_narrow_runtime_supported_capabilities(self):
        common = {"story.context.read", "story.result.produce"}
        result = compute_effective_capabilities(
            common,
            common,
            common,
            common,
            common,
            known_capabilities={"story.context.read", "unknown.capability"},
        )
        self.assertEqual(result, {"story.context.read"})

    def test_result_and_diff_models_enforce_canonical_structured_output(self):
        failure = CompatibilityResult(
            passed=False,
            failed_check=CompatibilityCheck.DECK_HOST_COMPATIBLE,
            error_code="DECK_HOST_INCOMPATIBLE",
            recovery_action="upgrade_deck_host",
        )
        self.assertEqual(failure.model_dump()["effective_capabilities"], [])
        with self.assertRaises(ValidationError):
            CompatibilityResult(passed=False)
        with self.assertRaises(ValidationError):
            CompatibilityResult(
                passed=False,
                failed_check=CompatibilityCheck.DECK_HOST_COMPATIBLE,
                error_code="DECK_HOST_INCOMPATIBLE",
                recovery_action="upgrade_deck_host",
                effective_capabilities=["story.context.read"],
            )
        with self.assertRaises(ValidationError):
            CapabilityDiff(
                added=["b", "a"],
                removed=[],
                requires_approval=True,
            )


if __name__ == "__main__":
    unittest.main()
