# [Input] None — module-level side-effecting stub setup.
# [Output] Inject claude_code_sdk stub into sys.modules so libs/claude_agent_kit
#          can be imported in environments where claude-code-sdk is not installed.
# [Pos] test-helper node in backend/tests
# [Sync] 2026-05-22: required because libs/claude_agent_kit/server/agent_runner.py
#                    has a top-level hard import of claude_code_sdk.types.
#                    Import this module BEFORE any libs.claude_agent_kit import.

"""Pre-import stubs for claude_code_sdk.

Usage (at top of every test file that imports libs.claude_agent_kit):

    import tests._sdk_stubs  # noqa: F401 — must be first

or equivalently:

    from tests import _sdk_stubs  # noqa: F401
"""
import sys
import types as _t


def _stub_module(name: str, **attrs) -> _t.ModuleType:
    if name in sys.modules:
        return sys.modules[name]
    mod = _t.ModuleType(name)
    mod.__dict__.update(attrs)
    sys.modules[name] = mod
    return mod


# claude_code_sdk — the Claude Code Python SDK.
# Stubbed with every symbol that agent_runner.py and types.py import at module level.
# Each class accepts **kwargs so agent_runner.py can instantiate them freely in tests.

class _KwargsBase:
    def __init__(self, *args, **kwargs):
        for k, v in kwargs.items():
            setattr(self, k, v)


class _HookMatcher(_KwargsBase):
    def __init__(self, matcher=None, hooks=None, **kwargs):
        self.matcher = matcher
        self.hooks = hooks or []
        super().__init__(**kwargs)


class _AssistantMessage:
    def __init__(self, content=None, **kwargs):
        self.content = content or []


class _ResultMessage:
    def __init__(self, subtype="success", session_id=None, usage=None, **kwargs):
        self.subtype = subtype
        self.session_id = session_id
        self.usage = usage


class _UserMessage:
    def __init__(self, content=None, **kwargs):
        self.content = content or []


class _StreamEvent(_KwargsBase):
    pass


_stub_module("claude_code_sdk",
    query=None,
    ClaudeSDKClient=_KwargsBase,
)
_stub_module("claude_code_sdk.types",
    AssistantMessage=_AssistantMessage,
    ClaudeCodeOptions=_KwargsBase,
    HookContext=_KwargsBase,
    HookJSONOutput=_KwargsBase,
    HookMatcher=_HookMatcher,
    McpServerConfig=_KwargsBase,
    McpStdioServerConfig=_KwargsBase,
    ResultMessage=_ResultMessage,
    StreamEvent=_StreamEvent,
    SystemMessage=_KwargsBase,
    UserMessage=_UserMessage,
)
