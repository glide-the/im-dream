"""Runtime Plugin Lock unit and SQLite integration coverage."""

from __future__ import annotations

import sqlite3
import unittest

from backend import database
from backend.schema import legacy_main_sqlite
from backend.models.deck_plugin import DeckPluginManifestV1, DeckPluginReleaseStatus
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
from backend.services.deck_plugin.release_service import (
    DeckPluginReleaseService,
    DeckPluginReleaseStateError,
    DeckRuntimePluginLockImmutabilityError,
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


class RuntimeLockReleaseIntegrationTests(unittest.TestCase):
    def setUp(self):
        self.db = sqlite3.connect(":memory:")
        self.db.row_factory = sqlite3.Row
        self.db.execute("PRAGMA foreign_keys=ON")
        legacy_main_sqlite.create_tables(self.db)
        self.service = DeckPluginReleaseService(
            self.db,
            source_allowlist=SOURCE_ALLOWLIST,
        )

    def tearDown(self):
        self.db.close()

    def test_draft_validating_published_and_lock_are_atomic(self):
        draft = self.service.create_draft(manifest())
        published, runtime_lock = self.service.publish_with_lock(
            draft.id,
            FakeResolver([artifact("1.4.1"), artifact("1.4.2")]),
        )
        self.assertEqual(published.status, DeckPluginReleaseStatus.PUBLISHED)
        self.assertEqual(runtime_lock.deck_plugin_manifest_hash, published.manifest_hash)
        self.assertTrue(runtime_lock.runtime_plugin_lock_id.startswith("rpl_"))
        self.assertFalse(runtime_lock.production_ready)

        row = self.db.execute(
            "SELECT * FROM deck_runtime_plugin_locks WHERE id = ?",
            (runtime_lock.runtime_plugin_lock_id,),
        ).fetchone()
        self.assertEqual(row["deck_plugin_id"], published.deck_plugin_id)
        self.assertEqual(row["deck_plugin_version"], published.deck_plugin_version)
        with self.assertRaises(sqlite3.IntegrityError):
            self.db.execute(
                """
                INSERT INTO deck_runtime_plugin_locks (
                    id, deck_plugin_id, deck_plugin_version,
                    deck_plugin_manifest_hash, lock_json
                ) VALUES ('rpl_duplicate', ?, ?, ?, ?)
                """,
                (
                    published.deck_plugin_id,
                    published.deck_plugin_version,
                    published.manifest_hash,
                    runtime_lock.model_dump_json(),
                ),
            )
        with self.assertRaises(sqlite3.IntegrityError):
            self.db.execute(
                "DELETE FROM deck_plugin_releases WHERE id = ?",
                (published.id,),
            )

    def test_resolver_failure_rolls_release_back_to_draft_without_lock(self):
        draft = self.service.create_draft(manifest())
        with self.assertRaises(RuntimePluginLockError):
            self.service.publish_with_lock(draft.id, FakeResolver(unavailable=True))
        self.assertEqual(
            self.service.get_release(draft.deck_plugin_id, draft.deck_plugin_version).status,
            DeckPluginReleaseStatus.DRAFT,
        )
        self.assertIsNone(
            self.service.get_runtime_plugin_lock(
                draft.deck_plugin_id, draft.deck_plugin_version
            )
        )

    def test_repeat_publish_and_changed_existing_lock_are_rejected(self):
        draft = self.service.create_draft(manifest())
        self.service.publish_with_lock(draft.id, FakeResolver([artifact("1.4.2")]))
        with self.assertRaises(DeckPluginReleaseStateError):
            self.service.publish_with_lock(draft.id, FakeResolver([artifact("1.4.2")]))

        other_data = valid_manifest_data()
        other_data["deck_plugin_version"] = "3.2.0"
        other_data["workflow"]["workflow_definition_ref"] = (
            "deck://voice-decks.story-dramatize/3.2.0/workflow.json"
        )
        other_draft = self.service.create_draft(
            DeckPluginManifestV1.model_validate(other_data)
        )
        stale_lock = LockGenerator().generate_lock(
            DeckPluginManifestV1.model_validate(other_data),
            FakeResolver([artifact("1.4.2", DIGEST_A)]),
        )
        self.db.execute(
            """
            INSERT INTO deck_runtime_plugin_locks (
                id, deck_plugin_id, deck_plugin_version,
                deck_plugin_manifest_hash, lock_json, created_at
            ) VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                stale_lock.runtime_plugin_lock_id,
                stale_lock.deck_plugin_id,
                stale_lock.deck_plugin_version,
                stale_lock.deck_plugin_manifest_hash,
                stale_lock.model_dump_json(),
                stale_lock.created_at.isoformat(),
            ),
        )
        self.db.commit()
        with self.assertRaises(DeckRuntimePluginLockImmutabilityError):
            self.service.publish_with_lock(
                other_draft.id,
                FakeResolver([artifact("1.4.2", DIGEST_B)]),
            )
        self.assertEqual(
            self.service.get_release(other_draft.deck_plugin_id, "3.2.0").status,
            DeckPluginReleaseStatus.DRAFT,
        )

    def test_deprecated_and_revoked_releases_keep_historical_lock_readable(self):
        draft = self.service.create_draft(manifest())
        published, runtime_lock = self.service.publish_with_lock(
            draft.id, FakeResolver([artifact("1.4.2")])
        )
        self.service.deprecate_release(published.id)
        self.assertEqual(
            self.service.get_runtime_plugin_lock(
                published.deck_plugin_id, published.deck_plugin_version
            ).runtime_plugin_lock_id,
            runtime_lock.runtime_plugin_lock_id,
        )
        self.service.revoke_release(published.id, "security policy")
        self.assertEqual(
            self.service.get_runtime_plugin_lock(
                published.deck_plugin_id, published.deck_plugin_version
            ).runtime_plugin_lock_id,
            runtime_lock.runtime_plugin_lock_id,
        )

    def test_sqlite_constraints_foreign_key_index_and_idempotent_initialization(self):
        legacy_main_sqlite.create_tables(self.db)
        indexes = {
            row["name"]
            for row in self.db.execute("PRAGMA index_list('deck_runtime_plugin_locks')")
        }
        self.assertIn("idx_runtime_locks_deck_plugin", indexes)
        self.assertTrue(
            any(
                row["unique"]
                for row in self.db.execute("PRAGMA index_list('deck_runtime_plugin_locks')")
            )
        )
        foreign_keys = list(
            self.db.execute("PRAGMA foreign_key_list('deck_runtime_plugin_locks')")
        )
        self.assertEqual({row["from"] for row in foreign_keys}, {
            "deck_plugin_id", "deck_plugin_version"
        })
        self.assertEqual({row["on_delete"] for row in foreign_keys}, {"RESTRICT"})

        with self.assertRaises(sqlite3.IntegrityError):
            self.db.execute(
                """
                INSERT INTO deck_runtime_plugin_locks (
                    id, deck_plugin_id, deck_plugin_version,
                    deck_plugin_manifest_hash, lock_json
                ) VALUES ('rpl_missing', 'missing.plugin', '1.0.0', ?, '{}')
                """,
                (DIGEST_A,),
            )


if __name__ == "__main__":
    unittest.main()
