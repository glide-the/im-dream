// [Input] iOS app metadata and currently qualified runtime artifacts.
// [Output] Credential-free public app information and conservative capability states.
// [Pos] iOS application integration qualification; authenticated business and the full toolset remain pending.
// [Sync] 2026-10-25: report technical runtime facts without defining a native account capability.
// [Sync] 2026-10-25: distinguish the executing public Python slice from full business qualification.
// [Sync] 2026-10-24: retain startup facts without an unused platform availability dispatcher.

import Foundation

struct RuntimeCapabilities {
    func appInfo() -> [String: Any] {
        let info = Bundle.main.infoDictionary ?? [:]
        return [
            "platform": "ios",
            "appVersion": info["CFBundleShortVersionString"] as? String ?? "unknown",
            "buildNumber": info["CFBundleVersion"] as? String ?? "unknown",
            "bridgeVersion": MobileBridgeContract.version,
        ]
    }

    func snapshot() -> [String: Any] {
        [
            "revision": "ios-host-v1",
            "capabilities": [
                "python": state("unavailable", reason: "DREAM_AUTHENTICATED_COMPOSITION_UNQUALIFIED"),
                "claudeRuntime": state("unavailable", reason: "CLAUDE_RUNTIME_TOOLSET_UNQUALIFIED"),
                "localTransport": state("unavailable", reason: "LOCAL_WEB_ASGI_INTEGRATION_UNQUALIFIED"),
                "files": state("unavailable", reason: "NATIVE_FILES_CONTRACT_UNQUALIFIED"),
            ],
        ]
    }

    private func state(_ value: String, reason: String?) -> [String: Any] {
        var result: [String: Any] = ["state": value]
        if let reason { result["reasonCode"] = reason }
        return result
    }
}
