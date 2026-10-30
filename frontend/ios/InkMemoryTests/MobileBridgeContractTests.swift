// [Input] iOS generation-aware bridge inventory, capability projection, and packaged resource policy.
// [Output] Provider-free proof of protocol, Web document/resource isolation, and fail-closed runtime gates.
// [Pos] iOS native unit tests; no Python, Claude, service, or model process is started.
// [Sync] 2026-10-29: MCP system authorization accepts the exact registered resource callback independently from normal Web login.
// [Sync] 2026-10-25: cover localhost relay navigation, web auth, and rejection of native account methods.
// [Sync] 2026-10-24: cover generation pinning, event order, reset, and stale-page rejection.
// [Sync] 2026-10-24: retain tests for the current host and remove unused platform/file fixtures.

import XCTest
@testable import InkMemory

final class MobileBridgeContractTests: XCTestCase {
    func testContractParsesAllowlistedRequest() throws {
        let request = try MobileBridgeContract.parse([
            "version": "1.0", "id": "request_1", "pageGeneration": "page_1", "method": "runtime.getCapabilities", "params": [:],
        ])
        XCTAssertEqual(request.method, "runtime.getCapabilities")
    }

    func testContractRejectsGenericShell() {
        XCTAssertThrowsError(try MobileBridgeContract.parse([
            "version": "1.0", "id": "request_2", "pageGeneration": "page_1", "method": "shell.execute", "params": [:],
        ]))
    }

    func testHostKeepsWebAuthenticationOutsideTheNativeBridge() {
        for method in ["auth.start", "auth.getSession", "auth.logout"] {
            XCTAssertThrowsError(try MobileBridgeContract.parse([
                "version": "1.0", "id": "request_auth", "pageGeneration": "page_1", "method": method, "params": [:],
            ]))
        }
        XCTAssertTrue(AppNavigationPolicy.allows(URL(string: "https://accounts.example/auth/dream/password"), mainFrame: true))
        XCTAssertTrue(AppNavigationPolicy.allows(URL(string: "http://localhost:3000/auth/dream/password"), mainFrame: true))
        XCTAssertTrue(AppNavigationPolicy.allows(URL(string: "http://127.0.0.1:5173/auth/callback"), mainFrame: true))
        XCTAssertFalse(AppNavigationPolicy.allows(URL(string: "https://accounts.example/auth/dream/password"), mainFrame: false))
        XCTAssertFalse(AppNavigationPolicy.allows(URL(string: "https://user:password@accounts.example/auth"), mainFrame: true))
        XCTAssertFalse(AppNavigationPolicy.allows(URL(string: "http://accounts.example/auth"), mainFrame: true))
        XCTAssertFalse(AppNavigationPolicy.allows(URL(string: "http://192.168.0.10:3000/auth"), mainFrame: true))
        XCTAssertFalse(AppNavigationPolicy.allows(URL(string: "javascript:alert(1)"), mainFrame: true))
    }

    func testRuntimeCapabilitiesFailClosed() {
        let snapshot = RuntimeCapabilities().snapshot()
        let capabilities = snapshot["capabilities"] as? [String: [String: Any]]
        XCTAssertEqual(capabilities?["python"]?["state"] as? String, "unavailable")
        XCTAssertEqual(capabilities?["claudeRuntime"]?["reasonCode"] as? String, "CLAUDE_RUNTIME_TOOLSET_UNQUALIFIED")
        XCTAssertEqual(capabilities?["files"]?["state"] as? String, "unavailable")
    }

    func testPageGenerationPinsFirstDocumentAndRejectsStaleRequests() {
        var gate = MobilePageGenerationGate()
        XCTAssertTrue(gate.accept("page_current"))
        XCTAssertTrue(gate.accept("page_current"))
        XCTAssertFalse(gate.accept("page_stale"))
        XCTAssertTrue(gate.isCurrent("page_current"))
    }

    func testPageGenerationSequencesEventsAndResetsForNewDocument() {
        var gate = MobilePageGenerationGate()
        XCTAssertNil(gate.nextEvent())
        XCTAssertTrue(gate.accept("page_one"))
        XCTAssertEqual(gate.nextEvent()?.sequence, 1)
        XCTAssertEqual(gate.nextEvent()?.sequence, 2)

        gate.reset()

        XCTAssertNil(gate.activeGeneration)
        XCTAssertEqual(gate.eventSequence, 0)
        XCTAssertTrue(gate.accept("page_two"))
        let firstEvent = gate.nextEvent()
        XCTAssertEqual(firstEvent?.generation, "page_two")
        XCTAssertEqual(firstEvent?.sequence, 1)
    }

    func testApplicationResourcePolicyAllowsOnlyQualifiedReads() throws {
        let asset = try XCTUnwrap(URL(string: "ink-memory://app/assets/main.js?build=1"))
        XCTAssertEqual(AppResourceRequestPolicy.relativePath(for: asset, method: "GET"), "assets/main.js")
        XCTAssertEqual(AppResourceRequestPolicy.relativePath(for: asset, method: "HEAD"), "assets/main.js")
        XCTAssertNil(AppResourceRequestPolicy.relativePath(for: asset, method: "POST"))
        XCTAssertNil(AppResourceRequestPolicy.relativePath(
            for: try XCTUnwrap(URL(string: "ink-memory://other/assets/main.js")),
            method: "GET"
        ))
        XCTAssertNil(AppResourceRequestPolicy.relativePath(
            for: try XCTUnwrap(URL(string: "ink-memory://app/%252e%252e/secret")),
            method: "GET"
        ))
    }

    func testApplicationResourcePolicyContainsResolvedPath() {
        let root = URL(fileURLWithPath: "/tmp/ink-memory-web", isDirectory: true)
        XCTAssertEqual(
            AppResourceRequestPolicy.resourceURL(for: "assets/main.js", under: root)?.path,
            "/tmp/ink-memory-web/assets/main.js"
        )
        XCTAssertNil(AppResourceRequestPolicy.resourceURL(for: "../secret", under: root))
    }

    func testMcpSystemAuthorizationRequiresExactResourceCallback() throws {
        let callback = try XCTUnwrap(URL(string: "com.inkmemory.mobile.mcp:/oauth/callback"))
        var authorization = URLComponents(string: "https://authorization.example.test/authorize")!
        authorization.queryItems = [URLQueryItem(name: "client_id", value: "fixture"), URLQueryItem(name: "redirect_uri", value: callback.absoluteString)]
        XCTAssertNotNil(NativeMcpOAuthCallback.authorizationURL(authorization.string!, callback: callback))
        authorization.queryItems?.append(URLQueryItem(name: "redirect_uri", value: callback.absoluteString))
        XCTAssertNil(NativeMcpOAuthCallback.authorizationURL(authorization.string!, callback: callback))
        authorization.queryItems = [URLQueryItem(name: "redirect_uri", value: "com.other.app:/oauth/callback")]
        XCTAssertNil(NativeMcpOAuthCallback.authorizationURL(authorization.string!, callback: callback))
        XCTAssertNil(NativeMcpOAuthCallback.authorizationURL("file:///authorize", callback: callback))
    }

    func testMcpReturnedCallbackKeepsAccountLoginAndOtherPathsOutsideItsSession() throws {
        let callback = try XCTUnwrap(URL(string: "com.inkmemory.mobile.mcp:/oauth/callback"))
        XCTAssertTrue(NativeMcpOAuthCallback.matches(try XCTUnwrap(URL(string: "com.inkmemory.mobile.mcp:/oauth/callback?code=fixture&state=fixture")), callback: callback))
        for value in ["com.other.app:/oauth/callback?code=fixture", "com.inkmemory.mobile.mcp:/other?code=fixture", "com.inkmemory.mobile.mcp:/oauth/callback?code=fixture#fragment", "http://localhost:5173/auth/callback?code=fixture"] {
            XCTAssertFalse(NativeMcpOAuthCallback.matches(try XCTUnwrap(URL(string: value)), callback: callback))
        }
    }

    func testLoginProbeRequiresTheOriginalSessionResponse() throws {
        let origin = try XCTUnwrap(URL(string: "http://localhost:5173"))
        let url = try XCTUnwrap(URL(string: "/auth/session", relativeTo: origin)?.absoluteURL)
        let response = try XCTUnwrap(HTTPURLResponse(url: url, statusCode: 200, httpVersion: nil, headerFields: nil))
        let data = try JSONSerialization.data(withJSONObject: ["user": ["id": "7"], "csrf_token": String(repeating: "s", count: 43)])
        XCTAssertTrue(NativeLoginSessionProbe.isAuthenticated(data: data, response: response, origin: origin))
        XCTAssertFalse(NativeLoginSessionProbe.isAuthenticated(data: Data("<html>Login</html>".utf8), response: response, origin: origin))
        XCTAssertFalse(NativeLoginSessionProbe.isAuthenticated(data: Data("{}".utf8), response: response, origin: origin))
        for address in ["http://localhost:5173/auth/start", "https://accounts.example/auth/session", "http://localhost:5174/auth/session"] {
            let redirected = try XCTUnwrap(HTTPURLResponse(url: try XCTUnwrap(URL(string: address)), statusCode: 200, httpVersion: nil, headerFields: nil))
            XCTAssertFalse(NativeLoginSessionProbe.isAuthenticated(data: data, response: redirected, origin: origin))
        }
        XCTAssertFalse(NativeLoginSessionProbe.isAuthenticated(data: data, response: HTTPURLResponse(url: url, statusCode: 401, httpVersion: nil, headerFields: nil), origin: origin))
    }
}
