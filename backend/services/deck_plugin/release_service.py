"""PostgreSQL-backed lifecycle service for Deck Plugin releases."""

from __future__ import annotations

from psycopg import IntegrityError as PostgresIntegrityError

import hashlib
import json
import uuid
from collections.abc import Iterable
from typing import Any

try:
    from backend import database
    from backend.models.deck_plugin import (
        DeckPluginManifestV1,
        DeckPluginRelease,
        DeckPluginReleaseStatus,
        DeckRuntimePluginLock,
    )
    from backend.services.deck_plugin.lock_generator import (
        LockGenerator,
        MarketplaceResolver,
        verify_lock_immutability,
    )
    from backend.services.deck_plugin.manifest_validator import (
        DeckPluginValidationError,
        validate_manifest,
    )
except ModuleNotFoundError:  # Support the backend directory on PYTHONPATH.
    import database
    from models.deck_plugin import (
        DeckPluginManifestV1,
        DeckPluginRelease,
        DeckPluginReleaseStatus,
        DeckRuntimePluginLock,
    )
    from services.deck_plugin.lock_generator import (
        LockGenerator,
        MarketplaceResolver,
        verify_lock_immutability,
    )
    from services.deck_plugin.manifest_validator import (
        DeckPluginValidationError,
        validate_manifest,
    )


ALLOWED_RELEASE_TRANSITIONS = {
    DeckPluginReleaseStatus.DRAFT: {DeckPluginReleaseStatus.VALIDATING},
    DeckPluginReleaseStatus.VALIDATING: {DeckPluginReleaseStatus.PUBLISHED},
    DeckPluginReleaseStatus.PUBLISHED: {
        DeckPluginReleaseStatus.DEPRECATED,
        DeckPluginReleaseStatus.REVOKED,
    },
    DeckPluginReleaseStatus.DEPRECATED: {DeckPluginReleaseStatus.REVOKED},
    DeckPluginReleaseStatus.REVOKED: set(),
}


class DeckPluginReleaseStateError(ValueError):
    pass


class DeckRuntimePluginLockImmutabilityError(DeckPluginReleaseStateError):
    pass


def assert_release_transition(
    current: DeckPluginReleaseStatus,
    target: DeckPluginReleaseStatus,
) -> None:
    if target not in ALLOWED_RELEASE_TRANSITIONS[current]:
        raise DeckPluginReleaseStateError(
            f"invalid Deck Plugin release transition: {current.value} -> {target.value}"
        )


def _canonical_manifest(manifest: DeckPluginManifestV1) -> str:
    return json.dumps(
        manifest.model_dump(mode="json"),
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    )


def _manifest_hash(manifest_json: str) -> str:
    return f"sha256:{hashlib.sha256(manifest_json.encode('utf-8')).hexdigest()}"


class DeckPluginReleaseService:
    def __init__(
        self,
        db: Any,
        *,
        source_allowlist: Iterable[str],
        production: bool = True,
    ) -> None:
        self.db = db
        self.source_allowlist = tuple(source_allowlist)
        self.production = production

    def _row_to_release(self, row: Any) -> DeckPluginRelease:
        return DeckPluginRelease(
            id=row["id"],
            deck_plugin_id=row["deck_plugin_id"],
            deck_plugin_version=row["deck_plugin_version"],
            display_name=row["display_name"],
            description=row["description"],
            author=row["author"],
            status=row["status"],
            manifest=DeckPluginManifestV1.model_validate_json(row["manifest_json"]),
            manifest_hash=row["manifest_hash"],
            workflow_definition_ref=row["workflow_definition_ref"],
            created_at=row["created_at"],
            updated_at=row["updated_at"],
            published_at=row["published_at"],
        )

    def _get_by_id(self, release_id: str) -> Any:
        row = self.db.execute(
            "SELECT * FROM deck_plugin_releases WHERE id = %s", (release_id,)
        ).fetchone()
        if row is None:
            raise KeyError(f"Deck Plugin release not found: {release_id}")
        return row

    def create_draft(self, manifest: DeckPluginManifestV1) -> DeckPluginRelease:
        if manifest.status is not DeckPluginReleaseStatus.DRAFT:
            raise DeckPluginReleaseStateError("create_draft requires manifest.status=draft")
        parsed = validate_manifest(
            manifest,
            source_allowlist=self.source_allowlist,
            db=self.db,
            production=self.production,
        )
        manifest_json = _canonical_manifest(parsed)
        release_id = f"dr_{uuid.uuid4().hex}"
        try:
            with self.db:
                self.db.execute(
                    """
                    INSERT INTO deck_plugin_releases (
                        id, deck_plugin_id, deck_plugin_version, display_name,
                        description, author, status, manifest_json, manifest_hash,
                        workflow_definition_ref, input_schema_ref, output_schema_ref,
                        capabilities_json, compatibility_json,
                        deck_runtime_contract_json, runtime_spec_json,
                        dependencies_json
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    """,
                    (
                        release_id,
                        parsed.deck_plugin_id,
                        parsed.deck_plugin_version,
                        parsed.display_name,
                        parsed.description,
                        parsed.author,
                        DeckPluginReleaseStatus.DRAFT.value,
                        manifest_json,
                        _manifest_hash(manifest_json),
                        parsed.workflow.workflow_definition_ref,
                        parsed.workflow.input_schema_ref,
                        parsed.workflow.output_schema_ref,
                        json.dumps(parsed.capabilities, ensure_ascii=False),
                        parsed.compatibility.model_dump_json(),
                        json.dumps(
                            {
                                "profile_contract": parsed.runtime_configuration.profile_contract,
                                "deck_runtime_snapshot_contract": (
                                    parsed.compatibility.deck_runtime_snapshot_contract
                                ),
                            },
                            ensure_ascii=False,
                        ),
                        parsed.runtime.model_dump_json(),
                        parsed.dependencies.model_dump_json(),
                    ),
                )
        except PostgresIntegrityError as exc:
            raise DeckPluginValidationError(
                "DECK_PLUGIN_MANIFEST_INVALID",
                "deck_plugin_id and deck_plugin_version must identify a unique release",
            ) from exc
        return self._row_to_release(self._get_by_id(release_id))

    def validate_release(self, release_id: str) -> DeckPluginRelease:
        """Retain the deck_001 validation-only transition for compatibility.

        New runtime-plugin releases must use ``publish_with_lock``. This legacy
        method does not create a lock and therefore never produces a
        production-ready runtime result.
        """
        with self.db:
            row = self._get_by_id(release_id)
            current = DeckPluginReleaseStatus(row["status"])
            assert_release_transition(current, DeckPluginReleaseStatus.VALIDATING)
            self.db.execute(
                "UPDATE deck_plugin_releases SET status = 'validating', "
                "updated_at = CURRENT_TIMESTAMP WHERE id = %s",
                (release_id,),
            )
            draft_manifest = DeckPluginManifestV1.model_validate_json(row["manifest_json"])
            validate_manifest(
                draft_manifest,
                source_allowlist=self.source_allowlist,
                db=self.db,
                exclude_release_id=release_id,
                production=self.production,
            )
            assert_release_transition(
                DeckPluginReleaseStatus.VALIDATING,
                DeckPluginReleaseStatus.PUBLISHED,
            )
            published_manifest = draft_manifest.model_copy(
                update={"status": DeckPluginReleaseStatus.PUBLISHED}
            )
            manifest_json = _canonical_manifest(published_manifest)
            self.db.execute(
                """
                UPDATE deck_plugin_releases
                SET status = 'published', manifest_json = %s, manifest_hash = %s,
                    updated_at = CURRENT_TIMESTAMP,
                    published_at = CURRENT_TIMESTAMP
                WHERE id = %s
                """,
                (manifest_json, _manifest_hash(manifest_json), release_id),
            )
        return self._row_to_release(self._get_by_id(release_id))

    def publish_with_lock(
        self,
        release_id: str,
        marketplace_resolver: MarketplaceResolver,
        *,
        lock_generator: LockGenerator | None = None,
    ) -> tuple[DeckPluginRelease, DeckRuntimePluginLock]:
        """Atomically resolve, persist, and publish one immutable release lock."""

        generator = lock_generator or LockGenerator()
        with self.db:
            row = self._get_by_id(release_id)
            current = DeckPluginReleaseStatus(row["status"])
            assert_release_transition(current, DeckPluginReleaseStatus.VALIDATING)
            self.db.execute(
                "UPDATE deck_plugin_releases SET status = 'validating', "
                "updated_at = CURRENT_TIMESTAMP WHERE id = %s",
                (release_id,),
            )
            draft_manifest = DeckPluginManifestV1.model_validate_json(row["manifest_json"])
            validate_manifest(
                draft_manifest,
                source_allowlist=self.source_allowlist,
                db=self.db,
                exclude_release_id=release_id,
                production=self.production,
            )
            published_manifest = draft_manifest.model_copy(
                update={"status": DeckPluginReleaseStatus.PUBLISHED}
            )
            manifest_json = _canonical_manifest(published_manifest)
            manifest_hash = _manifest_hash(manifest_json)
            runtime_lock = generator.generate_lock(
                published_manifest,
                marketplace_resolver,
            )
            if runtime_lock.deck_plugin_manifest_hash != manifest_hash:
                raise DeckRuntimePluginLockImmutabilityError(
                    "generated runtime lock does not match the published manifest hash"
                )

            existing_row = self.db.execute(
                """
                SELECT lock_json FROM deck_runtime_plugin_locks
                WHERE deck_plugin_id = %s AND deck_plugin_version = %s
                """,
                (published_manifest.deck_plugin_id, published_manifest.deck_plugin_version),
            ).fetchone()
            if existing_row is not None:
                existing_lock = DeckRuntimePluginLock.model_validate_json(
                    existing_row["lock_json"]
                )
                changed = not verify_lock_immutability(existing_lock, runtime_lock)
                detail = "content changed" if changed else "already exists"
                raise DeckRuntimePluginLockImmutabilityError(
                    f"runtime lock for this release {detail}"
                )

            self.db.execute(
                """
                INSERT INTO deck_runtime_plugin_locks (
                    id, deck_plugin_id, deck_plugin_version,
                    deck_plugin_manifest_hash, lock_json, created_at
                ) VALUES (%s, %s, %s, %s, %s, %s)
                """,
                (
                    runtime_lock.runtime_plugin_lock_id,
                    runtime_lock.deck_plugin_id,
                    runtime_lock.deck_plugin_version,
                    runtime_lock.deck_plugin_manifest_hash,
                    runtime_lock.model_dump_json(),
                    runtime_lock.created_at.isoformat(),
                ),
            )
            assert_release_transition(
                DeckPluginReleaseStatus.VALIDATING,
                DeckPluginReleaseStatus.PUBLISHED,
            )
            self.db.execute(
                """
                UPDATE deck_plugin_releases
                SET status = 'published', manifest_json = %s, manifest_hash = %s,
                    updated_at = CURRENT_TIMESTAMP,
                    published_at = CURRENT_TIMESTAMP
                WHERE id = %s
                """,
                (manifest_json, manifest_hash, release_id),
            )
        return self._row_to_release(self._get_by_id(release_id)), runtime_lock

    def get_runtime_plugin_lock(
        self,
        deck_plugin_id: str,
        version: str,
    ) -> DeckRuntimePluginLock | None:
        row = self.db.execute(
            """
            SELECT lock_json FROM deck_runtime_plugin_locks
            WHERE deck_plugin_id = %s AND deck_plugin_version = %s
            """,
            (deck_plugin_id, version),
        ).fetchone()
        if row is None:
            return None
        return DeckRuntimePluginLock.model_validate_json(row["lock_json"])

    def deprecate_release(self, release_id: str) -> DeckPluginRelease:
        return self._transition_published_release(
            release_id, DeckPluginReleaseStatus.DEPRECATED
        )

    def revoke_release(self, release_id: str, reason: str) -> DeckPluginRelease:
        if not reason.strip():
            raise ValueError("revocation reason is required")
        return self._transition_published_release(
            release_id, DeckPluginReleaseStatus.REVOKED
        )

    def _transition_published_release(
        self,
        release_id: str,
        target: DeckPluginReleaseStatus,
    ) -> DeckPluginRelease:
        with self.db:
            row = self._get_by_id(release_id)
            current = DeckPluginReleaseStatus(row["status"])
            assert_release_transition(current, target)
            self.db.execute(
                "UPDATE deck_plugin_releases SET status = %s, "
                "updated_at = CURRENT_TIMESTAMP WHERE id = %s",
                (target.value, release_id),
            )
        return self._row_to_release(self._get_by_id(release_id))

    def get_release(
        self, deck_plugin_id: str, version: str
    ) -> DeckPluginRelease | None:
        row = self.db.execute(
            """
            SELECT * FROM deck_plugin_releases
            WHERE deck_plugin_id = %s AND deck_plugin_version = %s
            """,
            (deck_plugin_id, version),
        ).fetchone()
        return self._row_to_release(row) if row is not None else None


def _with_default_db(callback):
    db = database.get_db()
    try:
        return callback(db)
    finally:
        db.close()


def create_draft(
    manifest: DeckPluginManifestV1,
    *,
    source_allowlist: Iterable[str],
    production: bool = True,
) -> DeckPluginRelease:
    return _with_default_db(
        lambda db: DeckPluginReleaseService(
            db, source_allowlist=source_allowlist, production=production
        ).create_draft(manifest)
    )


def validate_release(
    release_id: str,
    *,
    source_allowlist: Iterable[str],
    production: bool = True,
) -> DeckPluginRelease:
    return _with_default_db(
        lambda db: DeckPluginReleaseService(
            db, source_allowlist=source_allowlist, production=production
        ).validate_release(release_id)
    )


def publish_with_lock(
    release_id: str,
    marketplace_resolver: MarketplaceResolver,
    *,
    source_allowlist: Iterable[str],
    production: bool = True,
    lock_generator: LockGenerator | None = None,
) -> tuple[DeckPluginRelease, DeckRuntimePluginLock]:
    return _with_default_db(
        lambda db: DeckPluginReleaseService(
            db, source_allowlist=source_allowlist, production=production
        ).publish_with_lock(
            release_id,
            marketplace_resolver,
            lock_generator=lock_generator,
        )
    )


def deprecate_release(release_id: str) -> DeckPluginRelease:
    return _with_default_db(
        lambda db: DeckPluginReleaseService(db, source_allowlist=()).deprecate_release(
            release_id
        )
    )


def revoke_release(release_id: str, reason: str) -> DeckPluginRelease:
    return _with_default_db(
        lambda db: DeckPluginReleaseService(db, source_allowlist=()).revoke_release(
            release_id, reason
        )
    )


def get_release(deck_plugin_id: str, version: str) -> DeckPluginRelease | None:
    return _with_default_db(
        lambda db: DeckPluginReleaseService(db, source_allowlist=()).get_release(
            deck_plugin_id, version
        )
    )


def get_runtime_plugin_lock(
    deck_plugin_id: str,
    version: str,
) -> DeckRuntimePluginLock | None:
    return _with_default_db(
        lambda db: DeckPluginReleaseService(
            db, source_allowlist=()
        ).get_runtime_plugin_lock(deck_plugin_id, version)
    )
