# [Input] Platform-qualified embedded-Python build receipts and dependency import results.
# [Output] Credential-free mobile runtime capability snapshot and revision.
# [Pos] Side-effect-free qualification gate; it does not import the production service graph.
# [Sync] 2026-10-24: derive Python facts from explicit target-artifact receipts and leave native facts to the host.

"""Mobile runtime qualification without importing the production service graph."""

from __future__ import annotations

from dataclasses import asdict, dataclass
import hashlib
import importlib.util
import json
from typing import Callable, Literal

CapabilityState = Literal["available", "starting", "unavailable", "failed"]
MOBILE_REQUIRED_MODULES = (
    "fastapi",
    "httpx",
    "pydantic",
    "cryptography",
    "PIL",
    "mcp",
    "claude_agent_sdk",
)


@dataclass(frozen=True, slots=True)
class Capability:
    state: CapabilityState
    reasonCode: str | None = None


@dataclass(frozen=True, slots=True)
class PythonRuntimeFacts:
    revision: str
    capabilities: dict[str, Capability]

    def to_public_dict(self) -> dict[str, object]:
        return {
            "revision": self.revision,
            "capabilities": {name: asdict(value) for name, value in self.capabilities.items()},
        }


def _revision(capabilities: dict[str, Capability]) -> str:
    body = json.dumps(
        {name: asdict(capabilities[name]) for name in sorted(capabilities)},
        ensure_ascii=True,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")
    return hashlib.sha256(body).hexdigest()[:16]


def probe_mobile_runtime(
    *,
    platform: Literal["ios", "android"],
    local_transport_ready: bool = False,
    target_python_version: tuple[int, int, int] | None = None,
    embedded_build_qualified: bool = False,
    native_extensions_qualified: bool = False,
    import_smoke_qualified: bool = False,
    module_finder: Callable[[str], object | None] = importlib.util.find_spec,
) -> PythonRuntimeFacts:
    """Return current facts; callers inject platform-owned readiness after validation."""

    missing_modules = tuple(name for name in MOBILE_REQUIRED_MODULES if module_finder(name) is None)
    minimum_python = (3, 13, 0) if platform == "ios" else (3, 12, 0)
    python_ready = (
        target_python_version is not None
        and target_python_version >= minimum_python
        and embedded_build_qualified
        and native_extensions_qualified
        and import_smoke_qualified
        and not missing_modules
    )
    python_reason = None
    if target_python_version is None:
        python_reason = "PYTHON_VERSION_UNQUALIFIED"
    elif target_python_version < minimum_python:
        python_reason = "PYTHON_VERSION_UNSUPPORTED"
    elif not embedded_build_qualified:
        python_reason = "PYTHON_EMBEDDED_BUILD_UNQUALIFIED"
    elif not native_extensions_qualified:
        python_reason = "PYTHON_NATIVE_EXTENSIONS_UNQUALIFIED"
    elif not import_smoke_qualified:
        python_reason = "PYTHON_IMPORT_SMOKE_UNQUALIFIED"
    elif missing_modules:
        python_reason = "PYTHON_MODULES_UNQUALIFIED"

    capabilities = {
        "python": Capability("available" if python_ready else "unavailable", python_reason),
        "claudeRuntime": Capability("unavailable", f"CLAUDE_CLI_UNSUPPORTED_{platform.upper()}"),
        "localTransport": Capability(
            "available" if python_ready and local_transport_ready else "unavailable",
            None if python_ready and local_transport_ready else "LOCAL_ASGI_TRANSPORT_UNQUALIFIED",
        ),
    }
    return PythonRuntimeFacts(revision=_revision(capabilities), capabilities=capabilities)
