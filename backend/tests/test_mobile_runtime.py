# [Input] Provider-free protocol envelopes and injected mobile qualification receipts.
# [Output] Regression evidence for fail-closed Python and Claude runtime capability gates.
# [Pos] Mobile runtime unit tests; no native runtime, service, or model process is started.
# [Sync] 2026-10-25: reject removed native authentication operations without changing web auth.
# [Sync] 2026-10-24: inject target Python receipts and verify native capability ownership.

"""Provider-free checks for the side-effect-free mobile Python seam."""

from __future__ import annotations

import pytest

from mobile_runtime.capabilities import MOBILE_REQUIRED_MODULES, probe_mobile_runtime
from mobile_runtime.contract import BridgeRequest, MobileBridgeProtocolError
from mobile_runtime.runtime import MobileRuntime


@pytest.mark.parametrize("method", ["shell.execute", "auth.start", "auth.getSession", "auth.logout"])
def test_bridge_request_rejects_unknown_method_before_dispatch(method: str) -> None:
    with pytest.raises(MobileBridgeProtocolError, match="allowlisted") as error:
        BridgeRequest.parse({"version": "1.0", "id": "request_1", "pageGeneration": "page_1", "method": method, "params": {}})
    assert error.value.code == "FORBIDDEN"


@pytest.mark.parametrize("platform", ["ios", "android"])
def test_mobile_probe_keeps_claude_cli_unavailable(platform: str) -> None:
    snapshot = probe_mobile_runtime(
        platform=platform,  # type: ignore[arg-type]
        local_transport_ready=True,
        target_python_version=(3, 13, 0) if platform == "ios" else (3, 12, 0),
        embedded_build_qualified=True,
        native_extensions_qualified=True,
        import_smoke_qualified=True,
        module_finder=lambda name: object() if name in MOBILE_REQUIRED_MODULES else None,
    )
    assert snapshot.capabilities["python"].state == "available"
    assert snapshot.capabilities["claudeRuntime"].state == "unavailable"
    assert snapshot.capabilities["claudeRuntime"].reasonCode == f"CLAUDE_CLI_UNSUPPORTED_{platform.upper()}"


def test_local_transport_requires_qualified_python_modules() -> None:
    snapshot = probe_mobile_runtime(
        platform="android",
        local_transport_ready=True,
        target_python_version=(3, 12, 0),
        embedded_build_qualified=True,
        native_extensions_qualified=True,
        import_smoke_qualified=True,
        module_finder=lambda _name: None,
    )
    assert snapshot.capabilities["python"].reasonCode == "PYTHON_MODULES_UNQUALIFIED"
    assert snapshot.capabilities["localTransport"].state == "unavailable"


def test_native_capability_method_is_rejected_by_python_owner() -> None:
    runtime = MobileRuntime(platform="android")
    response = runtime.handle({"version": "1.0", "id": "request_2", "pageGeneration": "page_2", "method": "runtime.getCapabilities", "params": {}})
    assert response["ok"] is False
    assert response["error"] == {"code": "FORBIDDEN", "message": "The method is owned by the native host."}
    assert "token" not in repr(response).lower()
    assert "secret" not in repr(response).lower()


def test_python_version_requires_an_explicit_target_artifact_receipt() -> None:
    snapshot = probe_mobile_runtime(
        platform="android",
        embedded_build_qualified=True,
        native_extensions_qualified=True,
        import_smoke_qualified=True,
        module_finder=lambda name: object() if name in MOBILE_REQUIRED_MODULES else None,
    )
    assert snapshot.capabilities["python"].reasonCode == "PYTHON_VERSION_UNQUALIFIED"


def test_unqualified_runtime_request_fails_closed() -> None:
    runtime = MobileRuntime(platform="ios")
    response = runtime.handle({
        "version": "1.0",
        "id": "request_3",
        "pageGeneration": "page_3",
        "method": "runtime.request",
        "params": {"method": "GET", "path": "/api/health"},
    })
    assert response["ok"] is False
    assert response["error"] == {
        "code": "CAPABILITY_UNAVAILABLE",
        "message": "The qualified local Dream transport is unavailable for this mobile target.",
    }


def test_unqualified_pull_read_fails_closed() -> None:
    runtime = MobileRuntime(platform="android")
    response = runtime.handle({
        "version": "1.0",
        "id": "request_4",
        "pageGeneration": "page_4",
        "method": "runtime.response.read",
        "params": {"streamId": "stream_1", "maximumBytes": 65536},
    })
    assert response["ok"] is False
    assert response["pageGeneration"] == "page_4"
