# [Input] The canonical production business-router module inventory.
# [Output] Existing APIRouter instances in the same registration order for server and embedded hosts.
# [Pos] Router assembly inventory; imports remain lazy until the composition root loads them.
from importlib import import_module

BUSINESS_ROUTER_NAMES = (
    "auth", "oauth", "device_oauth", "sessions", "pictures", "preferences", "notion", "product", "reports",
    "voices", "friends", "claude_agent", "storage", "deck_plugins", "claude_plugins", "claude_mcp",
    "deck_plugin_binding", "deck_versions", "story_workspace", "system_config", "gateway_models", "workspace",
    "reflections", "memory",
)


def load_business_routers():
    return tuple(import_module("routers." + name) for name in BUSINESS_ROUTER_NAMES)
