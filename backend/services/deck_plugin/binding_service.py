"""Persistence, reversible deactivation, and optimistic locking for Deck bindings.

[Sync 2026-08-16] Include every effective binding form change in the Deck draft revision.
"""

from __future__ import annotations

import uuid
from typing import Any

try:
    from backend.models.deck_plugin import (
        BindingApplyTo,
        DeckPluginBinding,
        DeckPluginBindingResponse,
        DeckPluginBindingHistoryEntry,
        DeckPluginBindingHistoryResponse,
        DeckPluginBindingState,
        DeckPluginBindingStatus,
        DeckPluginBindingUpdateRequest,
        SelectionValidationSummary,
    )
    from backend.services.deck_plugin.selection_validation_service import (
        SelectionValidationService,
    )
except ModuleNotFoundError:  # Support the backend directory on PYTHONPATH.
    from models.deck_plugin import (
        BindingApplyTo,
        DeckPluginBinding,
        DeckPluginBindingResponse,
        DeckPluginBindingHistoryEntry,
        DeckPluginBindingHistoryResponse,
        DeckPluginBindingState,
        DeckPluginBindingStatus,
        DeckPluginBindingUpdateRequest,
        SelectionValidationSummary,
    )
    from services.deck_plugin.selection_validation_service import (
        SelectionValidationService,
    )


BINDING_REVISION_CONFLICT = "BINDING_REVISION_CONFLICT"
DECK_ACCESS_DENIED = "DECK_ACCESS_DENIED"
SELECTION_NOT_ALLOWED = "SELECTION_NOT_ALLOWED"


class BindingAccessError(PermissionError):
    code = DECK_ACCESS_DENIED

    def __init__(self) -> None:
        super().__init__("Deck not found or permission denied.")


class BindingRevisionConflict(RuntimeError):
    code = BINDING_REVISION_CONFLICT

    def __init__(self, current_revision: int) -> None:
        self.current_revision = current_revision
        super().__init__(
            "Binding was modified concurrently. Please refresh and confirm your selection."
        )


class BindingSelectionRejected(ValueError):
    code = SELECTION_NOT_ALLOWED

    def __init__(self, validation: SelectionValidationSummary) -> None:
        self.validation = validation
        super().__init__("The selected Deck Plugin release is not selectable.")


class BindingService:
    def __init__(
        self,
        db: Any,
        *,
        selection_validator: SelectionValidationService,
    ) -> None:
        self.db = db
        self._selection_validator = selection_validator

    def resolve_workspace_access(
        self,
        *,
        deck_id: str,
        actor_id: str,
        requested_workspace_id: str | None = None,
    ) -> str:
        deck = self.db.execute(
            "SELECT id FROM decks WHERE id = %s AND owner_id = %s",
            (deck_id, actor_id),
        ).fetchone()
        if deck is None:
            raise BindingAccessError()

        if requested_workspace_id:
            workspace = self.db.execute(
                """
                SELECT id FROM story_workspace_workspaces
                WHERE id = %s AND owner_id = %s
                """,
                (requested_workspace_id, actor_id),
            ).fetchone()
        else:
            workspace = self.db.execute(
                """
                SELECT id FROM story_workspace_workspaces
                WHERE owner_id = %s
                ORDER BY created_at, id
                LIMIT 1
                """,
                (actor_id,),
            ).fetchone()
        if workspace is None:
            raise BindingAccessError()
        return str(workspace["id"])

    async def get_current_state(
        self,
        *,
        deck_id: str,
        actor_id: str,
        requested_workspace_id: str | None = None,
    ) -> DeckPluginBindingState:
        workspace_id = self.resolve_workspace_access(
            deck_id=deck_id,
            actor_id=actor_id,
            requested_workspace_id=requested_workspace_id,
        )
        row = self._current_row(deck_id)
        if row is None:
            return DeckPluginBindingState(
                deck_id=deck_id,
                binding_revision=self.latest_revision(deck_id),
            )
        validation = await self._selection_validator.validate(
            deck_plugin_id=row["deck_plugin_id"],
            deck_plugin_version=row["deck_plugin_version"],
            workspace_id=workspace_id,
            actor_id=actor_id,
        )
        response = self._response(row, validation)
        return DeckPluginBindingState(
            deck_id=deck_id,
            binding_revision=response.binding_revision,
            binding=response,
        )

    def list_history(
        self,
        *,
        deck_id: str,
        actor_id: str,
        requested_workspace_id: str | None = None,
        limit: int = 50,
    ) -> DeckPluginBindingHistoryResponse:
        """Return persisted binding revisions without rewriting runtime history."""

        self.resolve_workspace_access(
            deck_id=deck_id,
            actor_id=actor_id,
            requested_workspace_id=requested_workspace_id,
        )
        rows = self.db.execute(
            """
            SELECT deck_plugin_binding_id, deck_plugin_id, deck_plugin_version,
                   binding_revision, status, applied_to, created_at, updated_at
            FROM deck_plugin_bindings
            WHERE deck_id = %s
            ORDER BY binding_revision DESC
            LIMIT %s
            """,
            (deck_id, limit),
        ).fetchall()
        return DeckPluginBindingHistoryResponse(
            deck_id=deck_id,
            current_binding_revision=self.latest_revision(deck_id),
            entries=[
                DeckPluginBindingHistoryEntry(
                    deck_plugin_binding_id=row["deck_plugin_binding_id"],
                    deck_plugin_id=row["deck_plugin_id"],
                    deck_plugin_version=row["deck_plugin_version"],
                    binding_revision=row["binding_revision"],
                    status=DeckPluginBindingStatus(row["status"]),
                    applied_to=BindingApplyTo(row["applied_to"]),
                    created_at=row["created_at"],
                    updated_at=row["updated_at"],
                )
                for row in rows
            ],
        )

    async def save(
        self,
        *,
        deck_id: str,
        actor_id: str,
        request: DeckPluginBindingUpdateRequest,
        requested_workspace_id: str | None = None,
    ) -> DeckPluginBindingResponse:
        if self.db.in_transaction:
            raise RuntimeError("binding save requires a clean transaction boundary")
        self.db.execute("BEGIN")
        try:
            self._lock_owned_deck(deck_id=deck_id, actor_id=actor_id)
            workspace_id = self.resolve_workspace_access(
                deck_id=deck_id,
                actor_id=actor_id,
                requested_workspace_id=requested_workspace_id,
            )
            current = self._current_row(deck_id)
            current_revision = self.latest_revision(deck_id)
            if request.expected_binding_revision != current_revision:
                raise BindingRevisionConflict(current_revision)

            validation = await self._selection_validator.validate(
                deck_plugin_id=request.deck_plugin_id,
                deck_plugin_version=request.deck_plugin_version,
                workspace_id=workspace_id,
                actor_id=actor_id,
            )
            if not validation.selectable:
                raise BindingSelectionRejected(validation)

            if (
                current is not None
                and current["deck_plugin_id"] == request.deck_plugin_id
                and current["deck_plugin_version"] == request.deck_plugin_version
            ):
                self.db.commit()
                return self._response(current, validation)

            next_revision = current_revision + 1
            if current is not None:
                cursor = self.db.execute(
                    """
                    UPDATE deck_plugin_bindings
                    SET status = 'stale', updated_at = CURRENT_TIMESTAMP
                    WHERE deck_plugin_binding_id = %s
                      AND status = 'active'
                      AND binding_revision = %s
                    """,
                    (current["deck_plugin_binding_id"], current_revision),
                )
                if cursor.rowcount != 1:
                    raise BindingRevisionConflict(self._current_revision(deck_id))

            binding_id = f"dpb_{uuid.uuid4().hex}"
            self.db.execute(
                """
                INSERT INTO deck_plugin_bindings (
                    deck_plugin_binding_id, deck_id, workspace_id, creator_id,
                    deck_plugin_id, deck_plugin_version, binding_revision,
                    status, applied_to
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, 'active', 'next_run')
                """,
                (
                    binding_id,
                    deck_id,
                    workspace_id,
                    actor_id,
                    request.deck_plugin_id,
                    request.deck_plugin_version,
                    next_revision,
                ),
            )
            created = self.db.execute(
                """
                SELECT * FROM deck_plugin_bindings
                WHERE deck_plugin_binding_id = %s
                """,
                (binding_id,),
            ).fetchone()
            try:
                from backend.services.deck.content_versioning import advance_deck_draft_revision
            except ModuleNotFoundError:  # pragma: no cover
                from services.deck.content_versioning import advance_deck_draft_revision
            advance_deck_draft_revision(self.db, deck_id)
            self.db.commit()
            assert created is not None
            return self._response(created, validation)
        except Exception:
            self.db.rollback()
            raise

    def clear(
        self,
        *,
        deck_id: str,
        actor_id: str,
        expected_binding_revision: int,
        requested_workspace_id: str | None = None,
    ) -> DeckPluginBindingState:
        """Deactivate the workflow binding while preserving its audit history."""

        if self.db.in_transaction:
            raise RuntimeError("binding clear requires a clean transaction boundary")
        self.db.execute("BEGIN")
        try:
            self._lock_owned_deck(deck_id=deck_id, actor_id=actor_id)
            self.resolve_workspace_access(
                deck_id=deck_id,
                actor_id=actor_id,
                requested_workspace_id=requested_workspace_id,
            )
            current = self._current_row(deck_id)
            current_revision = self.latest_revision(deck_id)
            if expected_binding_revision != current_revision:
                raise BindingRevisionConflict(current_revision)
            if current is not None:
                cursor = self.db.execute(
                    """
                    UPDATE deck_plugin_bindings
                    SET status = 'stale', updated_at = CURRENT_TIMESTAMP
                    WHERE deck_plugin_binding_id = %s
                      AND status = 'active'
                      AND binding_revision = %s
                    """,
                    (current["deck_plugin_binding_id"], current["binding_revision"]),
                )
                if cursor.rowcount != 1:
                    raise BindingRevisionConflict(self.latest_revision(deck_id))
                try:
                    from backend.services.deck.content_versioning import advance_deck_draft_revision
                except ModuleNotFoundError:  # pragma: no cover
                    from services.deck.content_versioning import advance_deck_draft_revision
                advance_deck_draft_revision(self.db, deck_id)
            self.db.commit()
            return DeckPluginBindingState(
                deck_id=deck_id,
                binding_revision=current_revision,
            )
        except Exception:
            self.db.rollback()
            raise

    def _lock_owned_deck(self, *, deck_id: str, actor_id: str) -> None:
        row = self.db.execute(
            "SELECT id FROM decks WHERE id = %s AND owner_id = %s FOR UPDATE",
            (deck_id, actor_id),
        ).fetchone()
        if row is None:
            raise BindingAccessError()

    def _current_row(self, deck_id: str) -> Any | None:
        return self.db.execute(
            """
            SELECT * FROM deck_plugin_bindings
            WHERE deck_id = %s AND status = 'active'
            """,
            (deck_id,),
        ).fetchone()

    def _current_revision(self, deck_id: str) -> int:
        row = self._current_row(deck_id)
        return int(row["binding_revision"]) if row else 0

    def latest_revision(self, deck_id: str) -> int:
        row = self.db.execute(
            "SELECT MAX(binding_revision) AS binding_revision "
            "FROM deck_plugin_bindings WHERE deck_id = %s",
            (deck_id,),
        ).fetchone()
        return int(row["binding_revision"] or 0) if row is not None else 0

    @staticmethod
    def _model(row: Any) -> DeckPluginBinding:
        return DeckPluginBinding(
            deck_plugin_binding_id=row["deck_plugin_binding_id"],
            deck_id=row["deck_id"],
            workspace_id=row["workspace_id"],
            creator_id=str(row["creator_id"]),
            deck_plugin_id=row["deck_plugin_id"],
            deck_plugin_version=row["deck_plugin_version"],
            binding_revision=row["binding_revision"],
            status=DeckPluginBindingStatus(row["status"]),
            applied_to=BindingApplyTo(row["applied_to"]),
            created_at=row["created_at"],
            updated_at=row["updated_at"],
        )

    @classmethod
    def _response(
        cls,
        row: Any,
        validation: SelectionValidationSummary,
    ) -> DeckPluginBindingResponse:
        binding = cls._model(row)
        return DeckPluginBindingResponse(
            deck_plugin_binding_id=binding.deck_plugin_binding_id,
            deck_id=binding.deck_id,
            deck_plugin_id=binding.deck_plugin_id,
            deck_plugin_version=binding.deck_plugin_version,
            binding_revision=binding.binding_revision,
            status=binding.status,
            applied_to=binding.applied_to,
            selection_validation_summary=validation,
        )
