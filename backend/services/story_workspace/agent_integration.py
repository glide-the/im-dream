#!/usr/bin/env python3
# [Input] Consume validated Agent story bundles, a user/workspace identity, and SQLite.
# [Output] Persist idempotent pending-review Story Workspace bundles and relationships.
# [Pos] Story Workspace service boundary between Claude Agent output and canonical tables.
# [Sync] 2026-08-01: add task_204 payload contract, parsing, and transactional persistence.

"""Claude Agent output contract and persistence for Story Workspace."""

from __future__ import annotations

import json
import logging
import sqlite3
from typing import Any, Optional
from uuid import uuid4

from pydantic import ValidationError

from story_workspace.contracts import StoryWorkspaceAgentStoryPayload


logger = logging.getLogger(__name__)


class AgentIntegrationError(Exception):
    """Raised when a validated Agent output bundle cannot be persisted."""


def parse_agent_story_output(
    raw_text: str,
) -> Optional[StoryWorkspaceAgentStoryPayload]:
    """Parse an entire JSON response as a story bundle; ordinary chat is ignored.

    A single ``json`` fenced block is accepted because Agent runners commonly
    wrap structured output that way. Explanatory prose or keyword matches never
    trigger persistence.
    """

    candidate = (raw_text or "").strip()
    if candidate.startswith("```json") and candidate.endswith("```"):
        candidate = candidate[len("```json") : -len("```")].strip()
    if not candidate.startswith("{"):
        return None

    try:
        decoded = json.loads(candidate)
    except (TypeError, ValueError) as exc:
        logger.warning("Agent story output ignored stage=json_parse error=%s", exc)
        return None
    if not isinstance(decoded, dict):
        logger.warning("Agent story output ignored stage=shape expected=object")
        return None

    try:
        return StoryWorkspaceAgentStoryPayload.model_validate(decoded)
    except ValidationError as exc:
        logger.warning("Agent story output ignored stage=validation error=%s", exc)
        return None


def get_or_create_default_workspace(
    db: sqlite3.Connection,
    user_id: int,
) -> str:
    """Return the user's oldest workspace, creating the default when absent."""

    row = db.execute(
        "SELECT id FROM story_workspace_workspaces WHERE owner_id = ? "
        "ORDER BY created_at ASC, id ASC LIMIT 1",
        (user_id,),
    ).fetchone()
    if row is not None:
        return str(row[0])

    workspace_id = str(uuid4())
    try:
        with db:
            db.execute(
                "INSERT INTO story_workspace_workspaces (id, name, owner_id, settings) "
                "VALUES (?, ?, ?, ?)",
                (workspace_id, "默认工作区", user_id, "{}"),
            )
    except Exception as exc:
        raise AgentIntegrationError("Unable to create the default workspace") from exc
    return workspace_id


def _new_identity(prefix: str) -> tuple[str, str]:
    resource_id = str(uuid4())
    return resource_id, f"{prefix}-{resource_id[:8]}"


def _placeholders(values: list[str]) -> str:
    return ", ".join("?" for _ in values)


def store_agent_story_output(
    db: sqlite3.Connection,
    user_id: int,
    workspace_id: str,
    agent_session_id: str,
    payload: StoryWorkspaceAgentStoryPayload,
) -> dict[str, Any]:
    """Persist one Agent-generated story bundle in a single SQLite savepoint.

    Story identity is stable for ``author_id + agent_session_id + title``.
    Characters are reconciled by name within the current story and scenes by
    order index. Because the minimum task_205 payload has no per-scene cast,
    every story character is related to every scene in the generated bundle.
    """

    agent_session_id = agent_session_id.strip()
    if not agent_session_id:
        raise AgentIntegrationError("agent_session_id must not be blank")

    workspace = db.execute(
        "SELECT id FROM story_workspace_workspaces WHERE id = ? AND owner_id = ?",
        (workspace_id, user_id),
    ).fetchone()
    if workspace is None:
        raise AgentIntegrationError("Workspace is not owned by the current user")

    duplicate_orders = len({scene.order_index for scene in payload.scenes}) != len(
        payload.scenes
    )
    if duplicate_orders:
        raise AgentIntegrationError("Scene order_index values must be unique")
    duplicate_names = len({item.name for item in payload.characters}) != len(
        payload.characters
    )
    if duplicate_names:
        raise AgentIntegrationError("Character names must be unique within a bundle")

    savepoint = "story_workspace_agent_output"
    db.execute(f"SAVEPOINT {savepoint}")
    try:
        story_row = db.execute(
            "SELECT id FROM story_workspace_stories "
            "WHERE agent_session_id = ? AND title = ? AND author_id = ? "
            "ORDER BY created_at ASC, id ASC LIMIT 1",
            (agent_session_id, payload.title, user_id),
        ).fetchone()
        if story_row is None:
            story_id, story_identifier = _new_identity("story")
            db.execute(
                """INSERT INTO story_workspace_stories
                   (id, identifier, title, description, status, review_status, type,
                    content, author_id, workspace_id, character_count, scene_count,
                    agent_generated, agent_session_id)
                   VALUES (?, ?, ?, ?, 'draft', 'pending', ?, ?, ?, ?, 0, 0, 1, ?)""",
                (
                    story_id,
                    story_identifier,
                    payload.title,
                    payload.description,
                    payload.type,
                    payload.content,
                    user_id,
                    workspace_id,
                    agent_session_id,
                ),
            )
        else:
            story_id = str(story_row[0])
            db.execute(
                """UPDATE story_workspace_stories
                   SET description = ?, status = 'draft', review_status = 'pending',
                       type = ?, content = ?, workspace_id = ?, agent_generated = 1,
                       review_notes = NULL, confirmed_at = NULL, published_at = NULL,
                       updated_at = CURRENT_TIMESTAMP
                   WHERE id = ? AND author_id = ?""",
                (
                    payload.description,
                    payload.type,
                    payload.content,
                    workspace_id,
                    story_id,
                    user_id,
                ),
            )

        existing_character_rows = db.execute(
            "SELECT c.id, c.name FROM story_workspace_characters c "
            "JOIN story_workspace_story_characters sc ON sc.character_id = c.id "
            "WHERE sc.story_id = ? AND c.author_id = ?",
            (story_id, user_id),
        ).fetchall()
        existing_characters = {str(row[1]): str(row[0]) for row in existing_character_rows}
        old_character_ids = [str(row[0]) for row in existing_character_rows]

        existing_scene_rows = db.execute(
            "SELECT id, order_index FROM story_workspace_scenes "
            "WHERE story_id = ? AND author_id = ? AND agent_generated = 1 "
            "ORDER BY created_at ASC, id ASC",
            (story_id, user_id),
        ).fetchall()
        existing_scenes: dict[int, str] = {}
        duplicate_scene_ids: list[str] = []
        for row in existing_scene_rows:
            order_index, scene_id = int(row[1]), str(row[0])
            if order_index in existing_scenes:
                duplicate_scene_ids.append(scene_id)
            else:
                existing_scenes[order_index] = scene_id

        all_existing_scene_ids = [str(row[0]) for row in existing_scene_rows]
        if all_existing_scene_ids:
            db.execute(
                "DELETE FROM story_workspace_scene_characters "
                f"WHERE scene_id IN ({_placeholders(all_existing_scene_ids)})",
                tuple(all_existing_scene_ids),
            )
        db.execute(
            "DELETE FROM story_workspace_story_characters WHERE story_id = ?",
            (story_id,),
        )

        character_ids: list[str] = []
        for character in payload.characters:
            character_id = existing_characters.get(character.name)
            serialized_tags = json.dumps(character.tags, ensure_ascii=False)
            if character_id is None:
                character_id, character_identifier = _new_identity("character")
                db.execute(
                    """INSERT INTO story_workspace_characters
                       (id, identifier, name, identity, personality, background,
                        catchphrase, tags, author_id, workspace_id, story_count,
                        review_status, agent_generated)
                       VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 0, 'pending', 1)""",
                    (
                        character_id,
                        character_identifier,
                        character.name,
                        character.identity,
                        character.personality,
                        character.background,
                        character.catchphrase,
                        serialized_tags,
                        user_id,
                        workspace_id,
                    ),
                )
            else:
                db.execute(
                    """UPDATE story_workspace_characters
                       SET identity = ?, personality = ?, background = ?,
                           catchphrase = ?, tags = ?, workspace_id = ?,
                           review_status = 'pending', agent_generated = 1,
                           updated_at = CURRENT_TIMESTAMP
                       WHERE id = ? AND author_id = ?""",
                    (
                        character.identity,
                        character.personality,
                        character.background,
                        character.catchphrase,
                        serialized_tags,
                        workspace_id,
                        character_id,
                        user_id,
                    ),
                )
            character_ids.append(character_id)
            db.execute(
                "INSERT INTO story_workspace_story_characters "
                "(story_id, character_id, role_type) VALUES (?, ?, NULL)",
                (story_id, character_id),
            )

        scene_ids: list[str] = []
        retained_scene_ids: set[str] = set()
        for scene in payload.scenes:
            scene_id = existing_scenes.get(scene.order_index)
            if scene_id is None:
                scene_id, scene_identifier = _new_identity("scene")
                db.execute(
                    """INSERT INTO story_workspace_scenes
                       (id, identifier, name, description, story_id, author_id,
                        workspace_id, character_count, order_index, review_status,
                        agent_generated)
                       VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 'pending', 1)""",
                    (
                        scene_id,
                        scene_identifier,
                        scene.name,
                        scene.description,
                        story_id,
                        user_id,
                        workspace_id,
                        len(character_ids),
                        scene.order_index,
                    ),
                )
            else:
                db.execute(
                    """UPDATE story_workspace_scenes
                       SET name = ?, description = ?, workspace_id = ?,
                           character_count = ?, review_status = 'pending',
                           agent_generated = 1, updated_at = CURRENT_TIMESTAMP
                       WHERE id = ? AND author_id = ?""",
                    (
                        scene.name,
                        scene.description,
                        workspace_id,
                        len(character_ids),
                        scene_id,
                        user_id,
                    ),
                )
            scene_ids.append(scene_id)
            retained_scene_ids.add(scene_id)
            for character_id in character_ids:
                db.execute(
                    "INSERT INTO story_workspace_scene_characters "
                    "(scene_id, character_id) VALUES (?, ?)",
                    (scene_id, character_id),
                )

        stale_scene_ids = duplicate_scene_ids + [
            scene_id
            for scene_id in all_existing_scene_ids
            if scene_id not in retained_scene_ids and scene_id not in duplicate_scene_ids
        ]
        if stale_scene_ids:
            db.execute(
                "DELETE FROM story_workspace_scenes "
                f"WHERE id IN ({_placeholders(stale_scene_ids)}) "
                "AND story_id = ? AND author_id = ? AND agent_generated = 1",
                tuple(stale_scene_ids) + (story_id, user_id),
            )

        db.execute(
            "UPDATE story_workspace_stories "
            "SET character_count = ?, scene_count = ?, review_status = 'pending', "
            "agent_generated = 1, updated_at = CURRENT_TIMESTAMP "
            "WHERE id = ? AND author_id = ?",
            (len(character_ids), len(scene_ids), story_id, user_id),
        )

        affected_character_ids = sorted(set(old_character_ids + character_ids))
        for character_id in affected_character_ids:
            db.execute(
                "UPDATE story_workspace_characters SET story_count = ("
                "SELECT COUNT(*) FROM story_workspace_story_characters "
                "WHERE character_id = ?), updated_at = CURRENT_TIMESTAMP WHERE id = ?",
                (character_id, character_id),
            )

        db.execute(f"RELEASE SAVEPOINT {savepoint}")
    except Exception as exc:
        try:
            db.execute(f"ROLLBACK TO SAVEPOINT {savepoint}")
            db.execute(f"RELEASE SAVEPOINT {savepoint}")
        except sqlite3.Error:
            logger.exception("Failed to roll back Agent story bundle savepoint")
        if isinstance(exc, AgentIntegrationError):
            raise
        raise AgentIntegrationError("Unable to persist Agent story bundle") from exc

    return {
        "story_id": story_id,
        "review_status": "pending",
        "character_ids": character_ids,
        "scene_ids": scene_ids,
    }
