# [Sync] 2026-10-25: import protocol modules independently; resolve executable public exports on access.
# [Input] None.
# [Output] Re-export ClaudeAgentRunner, create_agent_runner, SimpleClaudeAgentSDKClient,
#          session-file helpers, workspace lifecycle API, and MCP server factories to
#          application layers.
# [Pos] subpackage root in libs/claude_agent_kit/server
# [Sync] 2026-05-09: export necklace MCP server factory.
# [Sync] 2026-05-09: export memory MCP server factory.
# [Sync] 2026-09-01: export connector-selected builtin Skill workspace refresh.

"""Server subpackage for ClaudeAgentKit."""
from importlib import import_module

_EXPORT_MODULES = {
    "ClaudeAgentRunner": ".agent_runner", "create_agent_runner": ".agent_runner",
    "SimpleClaudeAgentSDKClient": ".simple_cas_client",
    **dict.fromkeys(("SESSION_FILE_EXTENSION", "get_projects_root", "locate_session_file",
                    "normalize_session_id", "parse_session_messages_from_jsonl", "read_session_messages"), ".session_files"),
    **dict.fromkeys(("get_workspace_root", "init_workspace", "get_or_create_workspace",
                    "sync_builtin_workspace_skills", "resolve_safe_path", "is_archive", "extract_archive_in_skills"), ".workspace"),
    "sync_skills_symlinks": ".workspace_file_sync",
}
_OPTIONAL_MCP_EXPORTS = {"create_memory_mcp_server", "create_user_mcp_server", "create_necklace_mcp_server"}


def __getattr__(name):
    if name in _OPTIONAL_MCP_EXPORTS:
        # Retain the existing all-or-none optional MCP export behavior.
        try:
            memory = import_module(".memory_mcp_server", __name__).create_memory_mcp_server
            user = import_module(".mcp_server", __name__).create_user_mcp_server
            necklace = import_module(".necklace_mcp_server", __name__).create_necklace_mcp_server
        except Exception:
            memory = user = necklace = None
        globals().update(create_memory_mcp_server=memory, create_user_mcp_server=user,
                         create_necklace_mcp_server=necklace)
        return globals()[name]
    module = _EXPORT_MODULES.get(name)
    if module is None:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
    value = getattr(import_module(module, __name__), name)
    globals()[name] = value
    return value


__all__ = [
    "ClaudeAgentRunner",
    "create_agent_runner",
    "SimpleClaudeAgentSDKClient",
    # MCP server factory
    "create_user_mcp_server",
    "create_memory_mcp_server",
    "create_necklace_mcp_server",
    "SESSION_FILE_EXTENSION",
    "get_projects_root",
    "locate_session_file",
    "normalize_session_id",
    "parse_session_messages_from_jsonl",
    "read_session_messages",
    # Workspace lifecycle (WSK-01)
    "get_workspace_root",
    "init_workspace",
    "get_or_create_workspace",
    "sync_builtin_workspace_skills",
    "resolve_safe_path",
    # Archive extraction (WSK-04)
    "is_archive",
    "extract_archive_in_skills",
    # Symlink sync (WSK-02)
    "sync_skills_symlinks",
]
