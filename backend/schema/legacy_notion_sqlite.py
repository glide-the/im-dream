"""Migration-only builder for the historical Notion Connector schema.

This module exists solely so the data-free 43 + 5 schema catalog can reproduce
the legacy source contract.  Runtime code must never import it.
"""

from __future__ import annotations

import sqlite3


def create_legacy_notion_tables(db: sqlite3.Connection) -> None:
    """Create the historical five-table source schema in an isolated fixture."""

    db.execute(
        """
        CREATE TABLE IF NOT EXISTS resource_connectors (
          id TEXT PRIMARY KEY,
          user_id INTEGER NOT NULL,
          name TEXT NOT NULL,
          platform TEXT NOT NULL,
          auth_status TEXT NOT NULL DEFAULT 'pending',
          config_json TEXT NOT NULL DEFAULT '{}',
          current_snapshot_version TEXT,
          current_source_revision TEXT,
          current_sync_cursor TEXT,
          last_synced_at TEXT,
          created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
          updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        )
        """
    )
    db.execute(
        "CREATE INDEX IF NOT EXISTS idx_resource_connectors_user_updated "
        "ON resource_connectors(user_id, updated_at DESC)"
    )
    db.execute(
        """
        CREATE TABLE IF NOT EXISTS connector_resources (
          id TEXT PRIMARY KEY,
          connector_id TEXT NOT NULL,
          resource_type TEXT NOT NULL,
          external_id TEXT,
          title TEXT NOT NULL,
          metadata_json TEXT NOT NULL DEFAULT '{}',
          sync_status TEXT NOT NULL DEFAULT 'synced',
          created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
          updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
          FOREIGN KEY (connector_id) REFERENCES resource_connectors(id) ON DELETE CASCADE,
          UNIQUE(connector_id, resource_type, external_id)
        )
        """
    )
    db.execute(
        "CREATE INDEX IF NOT EXISTS idx_connector_resources_connector "
        "ON connector_resources(connector_id, resource_type, updated_at DESC)"
    )
    db.execute(
        """
        CREATE TABLE IF NOT EXISTS connector_resource_pages (
          id TEXT PRIMARY KEY,
          resource_id TEXT NOT NULL,
          page_id TEXT NOT NULL,
          title TEXT NOT NULL,
          last_edited TEXT,
          properties_json TEXT,
          page_json TEXT,
          created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
          updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
          FOREIGN KEY (resource_id) REFERENCES connector_resources(id) ON DELETE CASCADE,
          UNIQUE(resource_id, page_id)
        )
        """
    )
    db.execute(
        "CREATE INDEX IF NOT EXISTS idx_connector_resource_pages_resource "
        "ON connector_resource_pages(resource_id, last_edited DESC)"
    )
    db.execute(
        """
        CREATE TABLE IF NOT EXISTS connector_snapshots (
          id TEXT PRIMARY KEY,
          connector_id TEXT NOT NULL,
          snapshot_version TEXT NOT NULL,
          source_revision TEXT NOT NULL,
          sync_cursor TEXT NOT NULL,
          fetched_at TEXT NOT NULL,
          state TEXT NOT NULL DEFAULT 'snapshot_ready',
          snapshot_json TEXT NOT NULL,
          created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
          updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
          FOREIGN KEY (connector_id) REFERENCES resource_connectors(id) ON DELETE CASCADE,
          UNIQUE(connector_id, snapshot_version)
        )
        """
    )
    db.execute(
        "CREATE INDEX IF NOT EXISTS idx_connector_snapshots_connector "
        "ON connector_snapshots(connector_id, created_at DESC)"
    )
    db.execute(
        """
        CREATE TABLE IF NOT EXISTS connector_chat_threads (
          id TEXT PRIMARY KEY,
          connector_id TEXT NOT NULL,
          thread_id TEXT NOT NULL,
          created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
          updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
          FOREIGN KEY (connector_id) REFERENCES resource_connectors(id) ON DELETE CASCADE,
          UNIQUE(connector_id, thread_id)
        )
        """
    )
    db.execute(
        "CREATE INDEX IF NOT EXISTS idx_connector_chat_threads_connector "
        "ON connector_chat_threads(connector_id, updated_at DESC)"
    )
    db.commit()


__all__ = ["create_legacy_notion_tables"]
