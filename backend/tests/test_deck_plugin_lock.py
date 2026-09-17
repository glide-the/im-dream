"""Runtime Plugin Lock pure contract coverage.

[Sync] 2026-09-16: remove the retired Dream SQL release integration fixture.
"""

from __future__ import annotations

import unittest

from backend.models.deck_plugin import DeckPluginManifestV1
from backend.services.deck_plugin.lock_generator import (
    LockGenerator,
    MarketplaceUnavailableError,
    RUNTIME_MARKETPLACE_UNAVAILABLE,
    RUNTIME_PLUGIN_UNRESOLVED,
    RuntimePluginLockError,
    ResolvedPluginArtifact,
    verify_lock_immutability,
    version_satisfies_constraint,
)
from backend.tests.test_deck_plugin_manifest import SOURCE_ALLOWLIST, valid_manifest_data


DIGEST_A = f"sha256:{'a' * 64}"
DIGEST_B = f"sha256:{'b' * 64}"


class FakeResolver:
    def __init__(self, artifacts=None, *, unavailable: bool = False):
        self.artifacts = list(artifacts or [])
        self.unavailable = unavailable

    def available_versions(self, claude_code_plugin_id: str, source_ref: str):
        if self.unavailable:
            raise MarketplaceUnavailableError("test marketplace outage")
        return self.artifacts


def artifact(
    version: str,
    digest: str | None = DIGEST_A,
    *,
    verified: bool = True,
) -> ResolvedPluginArtifact:
    return ResolvedPluginArtifact(
        resolved_version=version,
        source_ref=f"marketplace://voice-decks@{version}",
        artifact_digest=digest or "",
        supply_chain_verified=verified,
    )


def manifest() -> DeckPluginManifestV1:
    return DeckPluginManifestV1.model_validate(valid_manifest_data())


class LockGeneratorTests(unittest.TestCase):
    def test_semver_wildcard_and_comparator_ranges_choose_highest_match(self):
        self.assertTrue(version_satisfies_constraint("1.4.2", "1.4.x"))
        self.assertFalse(version_satisfies_constraint("1.5.0", "1.4.x"))
        self.assertTrue(version_satisfies_constraint("1.9.9", ">=1.0.0 <2.0.0"))
        self.assertFalse(version_satisfies_constraint("2.0.0", ">=1.0.0 <2.0.0"))

        lock = LockGenerator().generate_lock(
            manifest(),
            FakeResolver([artifact("1.4.1"), artifact("1.4.2"), artifact("1.5.0")]),
        )
        self.assertEqual(lock.claude_code_plugins[0].resolved_version, "1.4.2")
        self.assertEqual(lock.claude_code_plugins[0].artifact_digest, DIGEST_A)

    def test_unparseable_and_unmatched_versions_use_unresolved_code(self):
        data = valid_manifest_data()
        data["runtime"]["claude_code_plugins"][0]["version_constraint"] = "latest"
        with self.assertRaises(RuntimePluginLockError) as caught:
            LockGenerator().generate_lock(
                DeckPluginManifestV1.model_validate(data),
                FakeResolver([artifact("1.4.2")]),
            )
        self.assertEqual(caught.exception.code, RUNTIME_PLUGIN_UNRESOLVED)

        with self.assertRaises(RuntimePluginLockError) as caught:
            LockGenerator().generate_lock(manifest(), FakeResolver([artifact("2.0.0")]))
        self.assertEqual(caught.exception.code, RUNTIME_PLUGIN_UNRESOLVED)

    def test_marketplace_unavailable_has_distinct_error_code(self):
        with self.assertRaises(RuntimePluginLockError) as caught:
            LockGenerator().generate_lock(manifest(), FakeResolver(unavailable=True))
        self.assertEqual(caught.exception.code, RUNTIME_MARKETPLACE_UNAVAILABLE)

    def test_missing_digest_forces_non_production_result(self):
        lock = LockGenerator().generate_lock(
            manifest(), FakeResolver([artifact("1.4.2", None)])
        )
        self.assertFalse(lock.production_ready)
        self.assertEqual(lock.claude_code_plugins[0].artifact_digest, "")
        self.assertTrue(
            any("digest missing" in reason for reason in lock.production_readiness_reasons)
        )

    def test_current_supply_chain_gate_forces_verified_digest_non_production(self):
        lock = LockGenerator().generate_lock(
            manifest(), FakeResolver([artifact("1.4.2", verified=True)])
        )
        self.assertFalse(lock.production_ready)
        self.assertIn(
            "production supply-chain gate has not passed",
            lock.production_readiness_reasons,
        )

    def test_lock_immutability_compares_manifest_and_resolved_content(self):
        generator = LockGenerator()
        first = generator.generate_lock(manifest(), FakeResolver([artifact("1.4.2")]))
        equivalent = generator.generate_lock(manifest(), FakeResolver([artifact("1.4.2")]))
        changed = generator.generate_lock(
            manifest(), FakeResolver([artifact("1.4.2", DIGEST_B)])
        )
        self.assertTrue(verify_lock_immutability(first, equivalent))
        self.assertFalse(verify_lock_immutability(first, changed))


if __name__ == "__main__":
    unittest.main()
