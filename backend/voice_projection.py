# [Input] Original public Voice dict and nullable/raw stored Memory JSON text.
# [Output] Original Memory value, preserving empty text, JSON scalar/array and numeric types.
# [Pos] Shared pure Voice response projection; no database or policy dependency.
# [Sync] 2026-09-15: extract the existing database helper unchanged for Admin consumers.
import json


def _parse_voice_row(row: dict) -> dict:
    """Parse a raw voices DB row, deserialising JSON columns."""
    raw_config = row.get("memory_workspace_config")
    if raw_config and isinstance(raw_config, str):
        try:
            row["memory_workspace_config"] = json.loads(raw_config)
        except (json.JSONDecodeError, ValueError):
            row["memory_workspace_config"] = None
    return row
