#!/usr/bin/env python3
"""Test deck and voice CRUD functions."""

import sys
import os
import sqlite3
import unittest
from unittest import mock
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import database as db
import auth
from schema import legacy_main_sqlite


STORY_WORKSPACE_COLUMNS = {
    "story_workspace_workspaces": {
        "id", "name", "owner_id", "settings", "created_at", "updated_at",
    },
    "story_workspace_stories": {
        "id", "identifier", "title", "description", "status", "review_status",
        "type", "content", "author_id", "workspace_id", "character_count",
        "scene_count", "agent_generated", "agent_session_id", "review_notes",
        "created_at", "updated_at", "confirmed_at", "published_at",
    },
    "story_workspace_characters": {
        "id", "identifier", "name", "avatar_url", "identity", "personality",
        "background", "catchphrase", "tags", "notes", "author_id",
        "workspace_id", "story_count", "review_status", "agent_generated",
        "created_at", "updated_at", "status", "review_notes", "confirmed_at",
        "archived_at",
    },
    "story_workspace_scenes": {
        "id", "identifier", "name", "description", "story_id", "author_id",
        "workspace_id", "character_count", "order_index", "review_status",
        "agent_generated", "created_at", "updated_at", "status", "review_notes",
        "confirmed_at", "archived_at",
    },
    "story_workspace_story_characters": {
        "story_id", "character_id", "role_type", "created_at",
    },
    "story_workspace_scene_characters": {
        "scene_id", "character_id", "created_at",
    },
}

STORY_WORKSPACE_INTEGER_COLUMNS = {
    "story_workspace_workspaces": {"owner_id"},
    "story_workspace_stories": {
        "author_id", "character_count", "scene_count", "agent_generated",
    },
    "story_workspace_characters": {"author_id", "story_count", "agent_generated"},
    "story_workspace_scenes": {
        "author_id", "character_count", "order_index", "agent_generated",
    },
}

STORY_WORKSPACE_DATETIME_COLUMNS = {
    "story_workspace_workspaces": {"created_at", "updated_at"},
    "story_workspace_stories": {
        "created_at", "updated_at", "confirmed_at", "published_at",
    },
    "story_workspace_characters": {
        "created_at", "updated_at", "confirmed_at", "archived_at",
    },
    "story_workspace_scenes": {
        "created_at", "updated_at", "confirmed_at", "archived_at",
    },
    "story_workspace_story_characters": {"created_at"},
    "story_workspace_scene_characters": {"created_at"},
}

STORY_WORKSPACE_NOT_NULL_COLUMNS = {
    "story_workspace_workspaces": {
        "name", "owner_id", "created_at", "updated_at",
    },
    "story_workspace_stories": {
        "identifier", "title", "status", "review_status", "type", "author_id",
        "workspace_id", "character_count", "scene_count", "agent_generated",
        "created_at", "updated_at",
    },
    "story_workspace_characters": {
        "identifier", "name", "author_id", "workspace_id", "story_count",
        "review_status", "agent_generated", "created_at", "updated_at", "status",
    },
    "story_workspace_scenes": {
        "identifier", "name", "author_id", "workspace_id", "character_count",
        "order_index", "review_status", "agent_generated", "created_at", "updated_at",
        "status",
    },
    "story_workspace_story_characters": {
        "story_id", "character_id", "created_at",
    },
    "story_workspace_scene_characters": {
        "scene_id", "character_id", "created_at",
    },
}

STORY_WORKSPACE_DEFAULTS = {
    "story_workspace_workspaces": {
        "settings": "'{}'", "created_at": "CURRENT_TIMESTAMP",
        "updated_at": "CURRENT_TIMESTAMP",
    },
    "story_workspace_stories": {
        "status": "'draft'", "review_status": "'pending'", "type": "'short'",
        "character_count": "0", "scene_count": "0", "agent_generated": "1",
        "created_at": "CURRENT_TIMESTAMP", "updated_at": "CURRENT_TIMESTAMP",
    },
    "story_workspace_characters": {
        "tags": "'[]'", "story_count": "0", "review_status": "'pending'",
        "agent_generated": "1", "created_at": "CURRENT_TIMESTAMP",
        "updated_at": "CURRENT_TIMESTAMP", "status": "'active'",
    },
    "story_workspace_scenes": {
        "character_count": "0", "order_index": "0", "review_status": "'pending'",
        "agent_generated": "1", "created_at": "CURRENT_TIMESTAMP",
        "updated_at": "CURRENT_TIMESTAMP", "status": "'active'",
    },
    "story_workspace_story_characters": {"created_at": "CURRENT_TIMESTAMP"},
    "story_workspace_scene_characters": {"created_at": "CURRENT_TIMESTAMP"},
}

STORY_WORKSPACE_PRIMARY_KEYS = {
    "story_workspace_workspaces": {"id": 1},
    "story_workspace_stories": {"id": 1},
    "story_workspace_characters": {"id": 1},
    "story_workspace_scenes": {"id": 1},
    "story_workspace_story_characters": {"story_id": 1, "character_id": 2},
    "story_workspace_scene_characters": {"scene_id": 1, "character_id": 2},
}

STORY_WORKSPACE_FOREIGN_KEYS = {
    "story_workspace_workspaces": {("owner_id", "users", "id")},
    "story_workspace_stories": {
        ("author_id", "users", "id"),
        ("workspace_id", "story_workspace_workspaces", "id"),
    },
    "story_workspace_characters": {
        ("author_id", "users", "id"),
        ("workspace_id", "story_workspace_workspaces", "id"),
    },
    "story_workspace_scenes": {
        ("story_id", "story_workspace_stories", "id"),
        ("author_id", "users", "id"),
        ("workspace_id", "story_workspace_workspaces", "id"),
    },
    "story_workspace_story_characters": {
        ("story_id", "story_workspace_stories", "id"),
        ("character_id", "story_workspace_characters", "id"),
    },
    "story_workspace_scene_characters": {
        ("scene_id", "story_workspace_scenes", "id"),
        ("character_id", "story_workspace_characters", "id"),
    },
}

STORY_WORKSPACE_INDEXES = {
    "idx_sw_workspaces_owner": (("owner_id", 0),),
    "idx_sw_stories_author": (("author_id", 0), ("updated_at", 1)),
    "idx_sw_stories_review_status": (("review_status", 0), ("updated_at", 1)),
    "idx_sw_stories_status": (("status", 0), ("updated_at", 1)),
    "idx_sw_stories_type": (("type", 0), ("updated_at", 1)),
    "idx_sw_stories_search": (("title", 0),),
    "idx_sw_stories_agent": (("agent_session_id", 0),),
    "idx_sw_characters_author": (("author_id", 0), ("updated_at", 1)),
    "idx_sw_characters_name": (("name", 0),),
    "idx_sw_characters_review": (("review_status", 0), ("updated_at", 1)),
    "idx_sw_scenes_story": (("story_id", 0), ("order_index", 0)),
    "idx_sw_scenes_author": (("author_id", 0), ("updated_at", 1)),
    "idx_sw_scenes_review": (("review_status", 0), ("updated_at", 1)),
}

@unittest.skip("legacy file-backed CRUD demo is superseded by the isolated PostgreSQL runtime contract")
def test_crud():
    print("🧪 Testing Deck & Voice CRUD functions...\n")

    # Create a test user first with proper password hash
    try:
        password_hash = auth.hash_password("test123")
        user_id = db.create_user("test@example.com", password_hash, "Test User")
        print(f"✅ Created test user: {user_id}")
    except ValueError:
        # User already exists, get by email
        user = db.get_user_by_email("test@example.com")
        user_id = user['id']
        print(f"✅ Using existing test user: {user_id}")

    print("\n--- Test 1: Get system decks ---")
    decks = db.get_user_decks(user_id)
    print(f"Found {len(decks)} decks:")
    for deck in decks:
        print(f"  - {deck['name']} ({deck['id']}) - {deck['voice_count']} voices")

    print("\n--- Test 2: Get deck with voices ---")
    # Seeded system decks use UUID ids (the old slug id 'introspection_deck'
    # no longer exists); resolve the introspection deck dynamically by name.
    introspection = next(
        (d for d in decks if d['name'] == '内省卡组'),
        next((d for d in decks if d['voice_count'] > 0), None),
    )
    assert introspection is not None, "no system deck available for CRUD test"
    introspection_deck_id = introspection['id']
    deck_detail = db.get_deck_with_voices(user_id, introspection_deck_id)
    assert deck_detail is not None, f"deck {introspection_deck_id} not found"
    print(f"Introspection deck has {len(deck_detail['voices'])} voices:")
    for voice in deck_detail['voices']:
        print(f"  - {voice['name']} ({voice['id']})")

    print("\n--- Test 3: Fork a deck ---")
    new_deck_id = db.fork_deck(user_id, introspection_deck_id)
    print(f"Forked introspection_deck → {new_deck_id}")

    # Verify fork
    forked_deck = db.get_deck_with_voices(user_id, new_deck_id)
    print(f"Forked deck has {len(forked_deck['voices'])} voices")
    print(f"Parent ID: {forked_deck['parent_id']}")

    print("\n--- Test 4: Update deck ---")
    success = db.update_deck(user_id, new_deck_id, {
        'name': 'My Custom Introspection Deck',
        'description': 'This is my personal copy'
    })
    print(f"Update success: {success}")

    # Verify update
    updated = db.get_deck_with_voices(user_id, new_deck_id)
    print(f"Updated name: {updated['name']}")
    print(f"Updated description: {updated['description']}")

    print("\n--- Test 5: Create a voice in forked deck ---")
    new_voice_id = db.create_voice(
        user_id, new_deck_id,
        name="Test Voice",
        system_prompt="This is a test voice prompt.",
        icon="fire",
        color="blue"
    )
    print(f"Created voice: {new_voice_id}")

    # Verify creation
    updated_deck = db.get_deck_with_voices(user_id, new_deck_id)
    print(f"Deck now has {len(updated_deck['voices'])} voices")

    print("\n--- Test 6: Update voice ---")
    success = db.update_voice(user_id, new_voice_id, {
        'name': 'Updated Test Voice',
        'system_prompt': 'Updated prompt text'
    })
    print(f"Update success: {success}")

    print("\n--- Test 7: Fork a voice ---")
    source_voice_id = deck_detail['voices'][0]['id']
    forked_voice_id = db.fork_voice(user_id, source_voice_id, new_deck_id)
    print(f"Forked voice {source_voice_id} → {forked_voice_id}")

    # Verify fork
    final_deck = db.get_deck_with_voices(user_id, new_deck_id)
    print(f"Deck now has {len(final_deck['voices'])} voices")

    print("\n--- Test 8: Delete voice ---")
    success = db.delete_voice(user_id, new_voice_id)
    print(f"Delete voice success: {success}")

    # Verify deletion
    after_delete = db.get_deck_with_voices(user_id, new_deck_id)
    print(f"Deck now has {len(after_delete['voices'])} voices")

    print("\n--- Test 9: Delete deck (cascade) ---")
    success = db.delete_deck(user_id, new_deck_id)
    print(f"Delete deck success: {success}")

    # Verify deletion
    final_decks = db.get_user_decks(user_id)
    print(f"User now has {len(final_decks)} decks")

    print("\n✅ All CRUD tests passed!")


def test_fork_voice_binds_native_boolean_parameters():
    class Result:
        def __init__(self, row=None):
            self.row = row

        def fetchone(self):
            return self.row

    class Connection:
        def __init__(self):
            self.executions = []
            self.committed = False
            self.closed = False

        def execute(self, statement, parameters=()):
            self.executions.append((statement, parameters))
            if "SELECT owner_id FROM decks" in statement:
                return Result({"owner_id": 7})
            if "SELECT * FROM voices" in statement:
                return Result({
                    "name": "Source",
                    "name_zh": None,
                    "name_en": None,
                    "system_prompt": "Prompt",
                    "icon": "spark",
                    "color": "blue",
                    "memory_workspace_config": "{}",
                })
            if "SELECT MAX(order_index)" in statement:
                return Result({"max_order": 2})
            return Result()

        def commit(self):
            self.committed = True

        def close(self):
            self.closed = True

    connection = Connection()
    with mock.patch.object(db, "get_db", return_value=connection):
        voice_id = db.fork_voice(7, "source-voice", "target-deck")

    insert = next(
        parameters
        for statement, parameters in connection.executions
        if "INSERT INTO voices" in statement
    )
    assert insert[0] == voice_id
    assert insert[8] is False
    assert insert[11] is True
    assert connection.committed is True
    assert connection.closed is True


class StoryWorkspaceDatabaseTestCase(unittest.TestCase):
    """Verify the Story Workspace SQLite migration contract in isolation."""

    def setUp(self):
        self.connection = sqlite3.connect(":memory:")
        self.connection.row_factory = sqlite3.Row
        self.connection.execute("PRAGMA foreign_keys=ON")
        legacy_main_sqlite.create_tables(self.connection)

    def tearDown(self):
        self.connection.close()

    def _insert_required_parents(self):
        cursor = self.connection.execute(
            "INSERT INTO users (email, password_hash) VALUES (?, ?)",
            ("story-schema@example.com", "test-hash"),
        )
        user_id = cursor.lastrowid
        self.connection.execute(
            "INSERT INTO story_workspace_workspaces (id, name, owner_id) VALUES (?, ?, ?)",
            ("workspace-1", "Test Workspace", user_id),
        )
        return user_id

    @staticmethod
    def _legacy_review_connection():
        connection = sqlite3.connect(":memory:")
        connection.row_factory = sqlite3.Row
        connection.executescript(
            """
            CREATE TABLE story_workspace_characters (
              id TEXT PRIMARY KEY,
              identifier TEXT NOT NULL,
              name TEXT NOT NULL,
              avatar_url TEXT,
              identity TEXT,
              personality TEXT,
              background TEXT,
              catchphrase TEXT,
              tags TEXT DEFAULT '[]',
              notes TEXT,
              author_id INTEGER NOT NULL,
              workspace_id TEXT NOT NULL,
              story_count INTEGER NOT NULL DEFAULT 0,
              review_status TEXT NOT NULL DEFAULT 'pending'
                CHECK(review_status IN ('pending', 'confirmed', 'rejected')),
              agent_generated INTEGER NOT NULL DEFAULT 1
                CHECK(agent_generated IN (0, 1)),
              created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
              updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
              FOREIGN KEY (author_id) REFERENCES users (id),
              FOREIGN KEY (workspace_id) REFERENCES story_workspace_workspaces (id)
            );

            CREATE TABLE story_workspace_scenes (
              id TEXT PRIMARY KEY,
              identifier TEXT NOT NULL,
              name TEXT NOT NULL,
              description TEXT,
              story_id TEXT,
              author_id INTEGER NOT NULL,
              workspace_id TEXT NOT NULL,
              character_count INTEGER NOT NULL DEFAULT 0,
              order_index INTEGER NOT NULL DEFAULT 0,
              review_status TEXT NOT NULL DEFAULT 'pending'
                CHECK(review_status IN ('pending', 'confirmed', 'rejected')),
              agent_generated INTEGER NOT NULL DEFAULT 1
                CHECK(agent_generated IN (0, 1)),
              created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
              updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
              FOREIGN KEY (story_id) REFERENCES story_workspace_stories (id),
              FOREIGN KEY (author_id) REFERENCES users (id),
              FOREIGN KEY (workspace_id) REFERENCES story_workspace_workspaces (id)
            );
            """
        )
        for resource in ("character", "scene"):
            table = f"story_workspace_{resource}s"
            for review_status in ("pending", "confirmed", "rejected"):
                connection.execute(
                    f"""
                    INSERT INTO {table}
                        (id, identifier, name, author_id, workspace_id, review_status)
                    VALUES (?, ?, ?, ?, ?, ?)
                    """,
                    (
                        f"legacy-{resource}-{review_status}",
                        f"legacy-{resource}-{review_status}",
                        f"Legacy {resource} {review_status}",
                        1,
                        "legacy-workspace",
                        review_status,
                    ),
                )
        return connection

    def test_story_workspace_tables_exist(self):
        rows = self.connection.execute(
            """
            SELECT name
            FROM sqlite_master
            WHERE type = 'table' AND name LIKE 'story_workspace_%'
            """
        ).fetchall()

        self.assertEqual({row["name"] for row in rows}, set(STORY_WORKSPACE_COLUMNS))

    def test_story_workspace_schema_contract(self):
        for table, expected_columns in STORY_WORKSPACE_COLUMNS.items():
            with self.subTest(table=table):
                rows = self.connection.execute(f"PRAGMA table_info({table})").fetchall()
                actual = {row["name"]: row for row in rows}
                self.assertEqual(set(actual), expected_columns)

                expected_not_null = STORY_WORKSPACE_NOT_NULL_COLUMNS[table]
                expected_defaults = STORY_WORKSPACE_DEFAULTS[table]
                expected_primary_keys = STORY_WORKSPACE_PRIMARY_KEYS[table]
                integer_columns = STORY_WORKSPACE_INTEGER_COLUMNS.get(table, set())
                datetime_columns = STORY_WORKSPACE_DATETIME_COLUMNS.get(table, set())

                for column, row in actual.items():
                    expected_type = "INTEGER" if column in integer_columns else (
                        "DATETIME" if column in datetime_columns else "TEXT"
                    )
                    self.assertEqual(row["type"], expected_type, f"{table}.{column} type")
                    self.assertEqual(
                        bool(row["notnull"]), column in expected_not_null,
                        f"{table}.{column} NOT NULL",
                    )
                    self.assertEqual(
                        row["dflt_value"], expected_defaults.get(column),
                        f"{table}.{column} default",
                    )
                    self.assertEqual(
                        row["pk"], expected_primary_keys.get(column, 0),
                        f"{table}.{column} primary-key position",
                    )

                foreign_key_rows = self.connection.execute(
                    f"PRAGMA foreign_key_list({table})"
                ).fetchall()
                actual_foreign_keys = {
                    (row["from"], row["table"], row["to"])
                    for row in foreign_key_rows
                }
                self.assertEqual(actual_foreign_keys, STORY_WORKSPACE_FOREIGN_KEYS[table])

    def test_story_workspace_review_persistence_schema_contract(self):
        expected = {
            "status": ("TEXT", True, "'active'"),
            "review_notes": ("TEXT", False, None),
            "confirmed_at": ("DATETIME", False, None),
            "archived_at": ("DATETIME", False, None),
        }
        for table in ("story_workspace_characters", "story_workspace_scenes"):
            with self.subTest(table=table):
                rows = {
                    row["name"]: row
                    for row in self.connection.execute(
                        f"PRAGMA table_info({table})"
                    ).fetchall()
                }
                actual = {
                    column: (
                        rows[column]["type"],
                        bool(rows[column]["notnull"]),
                        rows[column]["dflt_value"],
                    )
                    for column in expected
                }
                self.assertEqual(actual, expected)

                table_sql = self.connection.execute(
                    "SELECT sql FROM sqlite_master WHERE type = 'table' AND name = ?",
                    (table,),
                ).fetchone()[0]
                normalized_sql = " ".join(table_sql.lower().split())
                self.assertIn(
                    "check(status in ('active', 'archived'))", normalized_sql
                )
                self.assertIn(
                    "check(review_notes is null or length(review_notes) <= 2000)",
                    normalized_sql,
                )

    def test_story_workspace_review_persistence_fresh_defaults(self):
        user_id = self._insert_required_parents()
        for resource in ("character", "scene"):
            table = f"story_workspace_{resource}s"
            self.connection.execute(
                f"""
                INSERT INTO {table}
                    (id, identifier, name, author_id, workspace_id)
                VALUES (?, ?, ?, ?, ?)
                """,
                (
                    f"fresh-{resource}",
                    f"fresh-{resource}",
                    f"Fresh {resource}",
                    user_id,
                    "workspace-1",
                ),
            )
            row = self.connection.execute(
                f"""
                SELECT status, review_notes, confirmed_at, archived_at
                FROM {table} WHERE id = ?
                """,
                (f"fresh-{resource}",),
            ).fetchone()
            self.assertEqual(tuple(row), ("active", None, None, None))

    def test_story_workspace_review_persistence_migrates_legacy_rows(self):
        legacy = self._legacy_review_connection()
        self.addCleanup(legacy.close)
        legacy_main_sqlite.create_tables(legacy)

        for table in ("story_workspace_characters", "story_workspace_scenes"):
            with self.subTest(table=table):
                fresh_schema = [
                    tuple(row)
                    for row in self.connection.execute(
                        f"PRAGMA table_info({table})"
                    ).fetchall()
                ]
                legacy_schema = [
                    tuple(row)
                    for row in legacy.execute(f"PRAGMA table_info({table})").fetchall()
                ]
                self.assertEqual(legacy_schema, fresh_schema)
                self.assertEqual(
                    [tuple(row) for row in legacy.execute(
                        f"PRAGMA foreign_key_list({table})"
                    ).fetchall()],
                    [tuple(row) for row in self.connection.execute(
                        f"PRAGMA foreign_key_list({table})"
                    ).fetchall()],
                )

                rows = legacy.execute(
                    f"""
                    SELECT review_status, status, review_notes,
                           confirmed_at, archived_at
                    FROM {table}
                    ORDER BY review_status
                    """
                ).fetchall()
                self.assertEqual(
                    {row["review_status"] for row in rows},
                    {"pending", "confirmed", "rejected"},
                )
                self.assertTrue(
                    all(
                        tuple(row)[1:] == ("active", None, None, None)
                        for row in rows
                    )
                )

    def test_story_workspace_review_persistence_migration_idempotent(self):
        legacy = self._legacy_review_connection()
        self.addCleanup(legacy.close)
        legacy_main_sqlite.create_tables(legacy)
        first_schema = {
            table: [tuple(row) for row in legacy.execute(
                f"PRAGMA table_info({table})"
            ).fetchall()]
            for table in ("story_workspace_characters", "story_workspace_scenes")
        }
        first_rows = {
            table: [tuple(row) for row in legacy.execute(
                f"SELECT * FROM {table} ORDER BY id"
            ).fetchall()]
            for table in ("story_workspace_characters", "story_workspace_scenes")
        }

        legacy_main_sqlite.create_tables(legacy)

        for table in ("story_workspace_characters", "story_workspace_scenes"):
            self.assertEqual(
                [tuple(row) for row in legacy.execute(
                    f"PRAGMA table_info({table})"
                ).fetchall()],
                first_schema[table],
            )
            self.assertEqual(
                [tuple(row) for row in legacy.execute(
                    f"SELECT * FROM {table} ORDER BY id"
                ).fetchall()],
                first_rows[table],
            )

    def test_story_workspace_review_notes_length_constraint(self):
        user_id = self._insert_required_parents()
        valid_notes = "界" * 2000
        invalid_notes = "界" * 2001
        for resource in ("character", "scene"):
            table = f"story_workspace_{resource}s"
            row_id = f"notes-{resource}"
            self.connection.execute(
                f"""
                INSERT INTO {table}
                    (id, identifier, name, author_id, workspace_id, review_notes)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (row_id, row_id, f"Notes {resource}", user_id, "workspace-1", valid_notes),
            )
            with self.assertRaises(sqlite3.IntegrityError):
                self.connection.execute(
                    f"UPDATE {table} SET review_notes = ? WHERE id = ?",
                    (invalid_notes, row_id),
                )
            stored = self.connection.execute(
                f"SELECT review_notes FROM {table} WHERE id = ?", (row_id,)
            ).fetchone()[0]
            self.assertEqual(stored, valid_notes)

    def test_story_workspace_asset_status_constraint(self):
        user_id = self._insert_required_parents()
        for resource in ("character", "scene"):
            table = f"story_workspace_{resource}s"
            row_id = f"status-{resource}"
            self.connection.execute(
                f"""
                INSERT INTO {table}
                    (id, identifier, name, author_id, workspace_id)
                VALUES (?, ?, ?, ?, ?)
                """,
                (row_id, row_id, f"Status {resource}", user_id, "workspace-1"),
            )
            self.connection.execute(
                f"UPDATE {table} SET status = 'archived' WHERE id = ?", (row_id,)
            )
            for invalid_status in ("published", "deleted"):
                with self.subTest(table=table, status=invalid_status):
                    with self.assertRaises(sqlite3.IntegrityError):
                        self.connection.execute(
                            f"UPDATE {table} SET status = ? WHERE id = ?",
                            (invalid_status, row_id),
                        )
                    stored = self.connection.execute(
                        f"SELECT status FROM {table} WHERE id = ?", (row_id,)
                    ).fetchone()[0]
                    self.assertEqual(stored, "archived")

    def test_story_workspace_review_persistence_round_trip(self):
        user_id = self._insert_required_parents()
        expected = (
            "archived",
            "需要补充细节",
            "2026-08-01 12:00:00",
            "2026-08-01 13:00:00",
        )
        for resource in ("character", "scene"):
            table = f"story_workspace_{resource}s"
            row_id = f"round-trip-{resource}"
            self.connection.execute(
                f"""
                INSERT INTO {table}
                    (id, identifier, name, author_id, workspace_id)
                VALUES (?, ?, ?, ?, ?)
                """,
                (row_id, row_id, f"Round trip {resource}", user_id, "workspace-1"),
            )
            self.connection.execute(
                f"""
                UPDATE {table}
                SET status = ?, review_notes = ?, confirmed_at = ?, archived_at = ?
                WHERE id = ?
                """,
                (*expected, row_id),
            )
            stored = self.connection.execute(
                f"""
                SELECT status, review_notes, confirmed_at, archived_at
                FROM {table} WHERE id = ?
                """,
                (row_id,),
            ).fetchone()
            self.assertEqual(tuple(stored), expected)

    def test_story_workspace_indexes_exist(self):
        rows = self.connection.execute(
            "SELECT name FROM sqlite_master WHERE type = 'index'"
        ).fetchall()
        actual_names = {row["name"] for row in rows}
        self.assertTrue(set(STORY_WORKSPACE_INDEXES).issubset(actual_names))

        for index_name, expected_columns in STORY_WORKSPACE_INDEXES.items():
            with self.subTest(index=index_name):
                index_rows = self.connection.execute(
                    f"PRAGMA index_xinfo({index_name})"
                ).fetchall()
                actual_columns = tuple(
                    (row["name"], row["desc"])
                    for row in index_rows
                    if row["key"]
                )
                self.assertEqual(actual_columns, expected_columns)

    def test_story_workspace_defaults_and_constraints(self):
        user_id = self._insert_required_parents()
        self.connection.execute(
            """
            INSERT INTO story_workspace_stories
                (id, identifier, title, author_id, workspace_id)
            VALUES (?, ?, ?, ?, ?)
            """,
            ("story-1", "story-001", "Test Story", user_id, "workspace-1"),
        )
        self.connection.execute(
            """
            INSERT INTO story_workspace_characters
                (id, identifier, name, author_id, workspace_id)
            VALUES (?, ?, ?, ?, ?)
            """,
            ("character-1", "character-001", "Test Character", user_id, "workspace-1"),
        )
        self.connection.execute(
            """
            INSERT INTO story_workspace_scenes
                (id, identifier, name, story_id, author_id, workspace_id)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            ("scene-1", "scene-001", "Test Scene", "story-1", user_id, "workspace-1"),
        )

        workspace = self.connection.execute(
            "SELECT * FROM story_workspace_workspaces WHERE id = 'workspace-1'"
        ).fetchone()
        story = self.connection.execute(
            "SELECT * FROM story_workspace_stories WHERE id = 'story-1'"
        ).fetchone()
        character = self.connection.execute(
            "SELECT * FROM story_workspace_characters WHERE id = 'character-1'"
        ).fetchone()
        scene = self.connection.execute(
            "SELECT * FROM story_workspace_scenes WHERE id = 'scene-1'"
        ).fetchone()

        self.assertEqual(workspace["settings"], "{}")
        self.assertIsNotNone(workspace["created_at"])
        self.assertEqual(
            (story["status"], story["review_status"], story["type"]),
            ("draft", "pending", "short"),
        )
        self.assertEqual(
            (story["character_count"], story["scene_count"], story["agent_generated"]),
            (0, 0, 1),
        )
        self.assertEqual(
            (character["tags"], character["story_count"], character["review_status"],
             character["agent_generated"]),
            ("[]", 0, "pending", 1),
        )
        self.assertEqual(
            (scene["character_count"], scene["order_index"], scene["review_status"],
             scene["agent_generated"]),
            (0, 0, "pending", 1),
        )

        invalid_story_values = (
            ("status", "deleted"),
            ("review_status", "approved"),
            ("type", "video"),
            ("agent_generated", 2),
        )
        for offset, (column, value) in enumerate(invalid_story_values, start=2):
            with self.subTest(column=column, value=value):
                with self.assertRaises(sqlite3.IntegrityError):
                    self.connection.execute(
                        f"""
                        INSERT INTO story_workspace_stories
                            (id, identifier, title, author_id, workspace_id, {column})
                        VALUES (?, ?, ?, ?, ?, ?)
                        """,
                        (f"story-{offset}", f"story-{offset:03}", "Invalid Story",
                         user_id, "workspace-1", value),
                    )

        with self.assertRaises(sqlite3.IntegrityError):
            self.connection.execute(
                """
                INSERT INTO story_workspace_workspaces (id, name, owner_id)
                VALUES ('orphan-workspace', 'Orphan', -1)
                """
            )

    def test_story_workspace_migration_idempotent(self):
        legacy_main_sqlite.create_tables(self.connection)
        legacy_main_sqlite.create_tables(self.connection)

        table_count = self.connection.execute(
            """
            SELECT COUNT(*)
            FROM sqlite_master
            WHERE type = 'table' AND name LIKE 'story_workspace_%'
            """
        ).fetchone()[0]
        self.assertEqual(table_count, 6)

    def test_drop_story_workspace_tables(self):
        legacy_main_sqlite.drop_story_workspace_tables(self.connection)
        remaining = self.connection.execute(
            """
            SELECT name
            FROM sqlite_master
            WHERE type = 'table' AND name LIKE 'story_workspace_%'
            """
        ).fetchall()
        self.assertEqual(remaining, [])

        legacy_main_sqlite.create_tables(self.connection)
        recreated = self.connection.execute(
            """
            SELECT name
            FROM sqlite_master
            WHERE type = 'table' AND name LIKE 'story_workspace_%'
            """
        ).fetchall()
        self.assertEqual(len(recreated), 6)

if __name__ == "__main__":
    test_crud()
