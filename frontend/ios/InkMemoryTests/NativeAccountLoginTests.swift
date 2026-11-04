// [Input] Production account URL rules and real WK/ephemeral Foundation Cookie stores with an isolated URLProtocol.
// [Output] Exact callbacks, original authorize values, paused-observer races and Cookie handoff qualification.
// [Pos] Provider-free iOS account adapter contracts; no system consent, normal account, Admin, model or Notion access.
// [Sync] 2026-10-31: exercise App callback/local HTTP ownership and the retained login probe before platform adoption.
// [Sync] 2026-10-31: drive the real WK callback through the production account adapter and an App-owned HTTP redirect fixture.
// [Sync] 2026-11-02: preserve original OAuth values while carrying the explicit Google choice once.
import XCTest
import WebKit
import Network
import UIKit
@testable import InkMemory

private final class AccountProbeProtocol: URLProtocol {
    static var received: ((URLRequest) -> Void)?
    override class func canInit(with request: URLRequest) -> Bool { true }
    override class func canonicalRequest(for request: URLRequest) -> URLRequest { request }
    override func startLoading() {
        Self.received?(request)
        let response = HTTPURLResponse(url: request.url!, statusCode: 200, httpVersion: nil, headerFields: ["Content-Type": "application/json"])!
        let data = try! JSONSerialization.data(withJSONObject: ["user": ["id": "7"], "csrf_token": String(repeating: "s", count: 43)])
        client?.urlProtocol(self, didReceive: response, cacheStoragePolicy: .notAllowed)
        client?.urlProtocol(self, didLoad: data); client?.urlProtocolDidFinishLoading(self)
    }
    override func stopLoading() {}
}

private final class AccountHTTPFixture {
    private let queue = DispatchQueue(label: "ink-account-http-fixture")
    private let listener: NWListener
    private var connections: [NWConnection] = []
    private var requests: [String] = []
    init() throws {
        let parameters = NWParameters.tcp
        parameters.requiredLocalEndpoint = .hostPort(host: "127.0.0.1", port: .any)
        listener = try NWListener(using: parameters)
    }
    func start(_ ready: @escaping (URL) -> Void) {
        listener.stateUpdateHandler = { [weak self] state in
            guard case .ready = state, let port = self?.listener.port else { return }
            DispatchQueue.main.async { ready(URL(string: "http://127.0.0.1:\(port.rawValue)")!) }
        }
        listener.newConnectionHandler = { [weak self] connection in
            guard let self else { connection.cancel(); return }
            self.connections.append(connection); connection.start(queue: self.queue)
            self.read(connection, input: Data())
        }
        listener.start(queue: queue)
    }
    private func read(_ connection: NWConnection, input: Data) {
        connection.receive(minimumIncompleteLength: 1, maximumLength: 65_536) { [weak self] data, _, ended, error in
            guard let self else { connection.cancel(); return }
            let accumulated = input + (data ?? Data())
            guard let text = String(data: accumulated, encoding: .utf8), text.contains("\r\n\r\n") else {
                if !ended && error == nil && accumulated.count < 65_536 { self.read(connection, input: accumulated) }
                else { connection.cancel() }
                return
            }
            let lines = text.components(separatedBy: "\r\n")
            let path = lines[0].components(separatedBy: " ").dropFirst().first ?? ""
            self.requests.append(path)
            let cookie = lines.first(where: { $0.lowercased().hasPrefix("cookie:") }) ?? ""
            let body: Data, head: String
            if path.hasPrefix("/auth/callback?") {
                XCTAssertTrue(cookie.contains("ink-dream-login=fixture-original-transaction"))
                body = Data()
                head = "HTTP/1.1 303 See Other\r\nLocation: /auth/sign-in\r\nSet-Cookie: ink-dream-browser=fixture-bff-handle; Path=/; HttpOnly; SameSite=Lax\r\nSet-Cookie: ink-dream-login=; Max-Age=0; Path=/; HttpOnly; SameSite=Lax\r\n"
            } else if path == "/auth/session" {
                XCTAssertTrue(cookie.contains("ink-dream-browser=fixture-bff-handle"))
                XCTAssertFalse(cookie.contains("fixture-original-transaction"))
                body = try! JSONSerialization.data(withJSONObject: ["user": ["id": "7"], "csrf_token": String(repeating: "s", count: 43)])
                head = "HTTP/1.1 200 OK\r\n"
            } else { body = Data(); head = "HTTP/1.1 404 Not Found\r\n" }
            let response = Data((head + "Content-Type: application/json\r\nContent-Length: \(body.count)\r\nConnection: close\r\n\r\n").utf8) + body
            connection.send(content: response, completion: .contentProcessed { _ in connection.cancel() })
        }
    }
    func paths() -> [String] { queue.sync { requests } }
    func stop() { queue.sync { listener.stateUpdateHandler = nil; listener.newConnectionHandler = nil; listener.cancel(); connections.forEach { $0.cancel() }; connections.removeAll() } }
}

private final class AccountNavigationFixture: NSObject, WKNavigationDelegate {
    let account: NativeAccountLogin
    let loaded: XCTestExpectation
    init(account: NativeAccountLogin, loaded: XCTestExpectation) { self.account = account; self.loaded = loaded }
    func webView(_ webView: WKWebView, didFinish navigation: WKNavigation!) { loaded.fulfill() }
    func webView(_ webView: WKWebView, decidePolicyFor action: WKNavigationAction, decisionHandler: @escaping (WKNavigationActionPolicy) -> Void) {
        decisionHandler(account.handles(action, page: webView.url) ? .cancel : .allow)
    }
}

final class NativeAccountLoginTests: XCTestCase {
    private let origin = URL(string: "http://localhost:5173")!
    private let callback = URL(string: "com.inkmemory.example.auth:/auth/callback")!
    private let state = String(repeating: "s", count: 43)

    func testAccountCallbackMapsOnlyExactCurrentQueryToTheOriginalHTTPReceiver() throws {
        XCTAssertNotNil(NativeAccountCallback.configuration(callback.absoluteString))
        let raw = callback.absoluteString + "?code=fixture%2Bcode&state=" + state + "&iss=https%3A%2F%2Fadmin.example%2Fapi%2Fauth"
        let local = try XCTUnwrap(NativeAccountCallback.localRequest(URL(string: raw)!, callback: callback, origin: origin, state: state))
        XCTAssertEqual(local.absoluteString, origin.absoluteString + "/auth/callback?" + raw.components(separatedBy: "?")[1])
        XCTAssertNotNil(NativeAccountCallback.localRequest(URL(string: raw)!, callback: callback, origin: origin))
        XCTAssertNil(NativeAccountCallback.localRequest(URL(string: raw)!, callback: callback, origin: origin, state: String(repeating: "x", count: 43)))
        for suffix in ["&code=duplicate", "&state=duplicate", "&iss=duplicate", "&error=access_denied", "#fragment"] {
            XCTAssertNil(NativeAccountCallback.localRequest(URL(string: raw + suffix)!, callback: callback, origin: origin))
        }
        for bad in ["com.other.app.auth:/auth/callback", "com.inkmemory.example.mcp:/oauth/callback", "com.inkmemory.example.auth://auth/callback", "com.inkmemory.example.auth:///auth/callback", "com.inkmemory.example.auth:/auth/%63allback"] {
            XCTAssertNil(NativeAccountCallback.localRequest(URL(string: bad + "?" + raw.components(separatedBy: "?")[1])!, callback: callback, origin: origin))
        }
        for bad in ["https://dream.example", "https://localhost", "http://device.lan:5173"] {
            XCTAssertNil(NativeAccountCallback.localRequest(URL(string: raw)!, callback: callback, origin: URL(string: bad)!))
        }
        for bad in ["com.app.mcp:/oauth/callback", "com.app.auth:/auth/../auth/callback", callback.absoluteString + "?code=x", callback.absoluteString + "#fragment"] {
            XCTAssertNil(NativeAccountCallback.configuration(bad))
        }
    }

    func testOriginalAuthorizeClientPKCEAndReturnLocationStayIntact() throws {
        let admin = URL(string: "https://admin.example/auth/dream/google")!
        var components = URLComponents(string: "https://admin.example/api/auth/oauth2/authorize")!
        components.queryItems = ["response_type": "code", "client_id": "original-public-client", "redirect_uri": callback.absoluteString,
            "resource": "https://dream.example/api", "scope": "openid dream:read dream:write", "state": state,
            "nonce": String(repeating: "n", count: 43), "code_challenge": String(repeating: "c", count: 43), "code_challenge_method": "S256"].map { URLQueryItem(name: $0.key, value: $0.value) }
        let result = try XCTUnwrap(NativeAccountCallback.authorization(components.string!, admin: admin, callback: callback))
        let selected = URLComponents(url: result.url, resolvingAgainstBaseURL: false)!
        for item in components.queryItems! { XCTAssertEqual(selected.queryItems!.filter { $0.name == item.name }, [item]) }
        XCTAssertEqual(result.state, state)
        XCTAssertEqual(selected.queryItems!.filter { $0.name == "prompt" }, [URLQueryItem(name: "prompt", value: "login")])
        XCTAssertEqual(selected.queryItems!.filter { $0.name == "identity_provider" }, [URLQueryItem(name: "identity_provider", value: "google")])
        XCTAssertEqual(NativeAccountCallback.authorization(result.url.absoluteString, admin: admin, callback: callback)?.url, result.url)
        for name in ["redirect_uri", "client_id", "state", "nonce", "code_challenge", "code_challenge_method", "prompt", "identity_provider"] {
            var repeated = components
            repeated.queryItems?.append(URLQueryItem(name: name, value: "duplicate"))
            if name == "prompt" { repeated.queryItems?.append(URLQueryItem(name: name, value: "login")) }
            if name == "identity_provider" { repeated.queryItems?.append(URLQueryItem(name: "identity_provider", value: "google")) }
            XCTAssertNil(NativeAccountCallback.authorization(repeated.string!, admin: admin, callback: callback))
        }
        XCTAssertNil(NativeAccountCallback.authorization(components.string!, admin: URL(string: "https://other.example")!, callback: callback))
        components.queryItems = components.queryItems?.filter { $0.name != "redirect_uri" }
        components.queryItems?.append(URLQueryItem(name: "redirect_uri", value: "com.other.app.auth:/auth/callback"))
        XCTAssertNil(NativeAccountCallback.authorization(components.string!, admin: admin, callback: callback))
        XCTAssertEqual(NativeAccountCallback.returnLocation(URL(string: "http://localhost:5173/auth/sign-in?name=hello%20world&auth_error=google#fragment")!, origin: origin), "/auth/sign-in?name=hello%20world")
        XCTAssertEqual(NativeAccountCallback.returnLocation(URL(string: "http://localhost:5173/auth/sign-in?name=a%2Bb&spaces=a+b&%61uth_error=google")!, origin: origin), "/auth/sign-in?name=a%2Bb&spaces=a+b")
        XCTAssertNil(NativeAccountCallback.returnLocation(URL(string: "https://other.example/auth/sign-in")!, origin: origin))
    }

    func testGoogleActionRequiresTheOriginalOptionsResponseAndExactServerActions() throws {
        func data(_ google: String, extra: Bool = false) throws -> Data {
            var object = ["google_action": google, "password_action": "https://admin.example/auth/dream/password"]
            if extra { object["unregistered"] = "value" }
            return try JSONSerialization.data(withJSONObject: object)
        }
        let response = HTTPURLResponse(url: URL(string: "/auth/options", relativeTo: origin)!.absoluteURL, statusCode: 200, httpVersion: nil, headerFields: nil)!
        XCTAssertEqual(NativeAccountCallback.googleAction(try data("https://admin.example/auth/dream/google"), response: response, origin: origin)?.absoluteString, "https://admin.example/auth/dream/google")
        for bad in ["http://admin.example/auth/dream/google", "https://admin.example/auth/dream/google?changed=1", "https://user:secret@admin.example/auth/dream/google", "https://other.example/auth/dream/google"] {
            XCTAssertNil(NativeAccountCallback.googleAction(try data(bad), response: response, origin: origin))
        }
        XCTAssertNil(NativeAccountCallback.googleAction(try data("https://admin.example/auth/dream/google", extra: true), response: response, origin: origin))
        let foreign = HTTPURLResponse(url: URL(string: "https://other.example/auth/options")!, statusCode: 200, httpVersion: nil, headerFields: nil)!
        XCTAssertNil(NativeAccountCallback.googleAction(try data("https://admin.example/auth/dream/google"), response: foreign, origin: origin))
    }

    @MainActor func testPausedCookieHandoffPreservesNativeResultThenResumesTheOriginalSessionProbe() throws {
        let dataStore = WKWebsiteDataStore.nonPersistent()
        let store = dataStore.httpCookieStore
        let configuration = URLSessionConfiguration.ephemeral
        configuration.protocolClasses = [AccountProbeProtocol.self]
        let cookies = try XCTUnwrap(configuration.httpCookieStorage)
        let session = URLSession(configuration: configuration)
        defer { session.invalidateAndCancel(); AccountProbeProtocol.received = nil }
        let stale = try XCTUnwrap(HTTPCookie(properties: [.domain: "localhost", .path: "/", .name: "ink-dream-login", .value: "fixture-old-transaction"]))
        let prepared = expectation(description: "old WK transaction")
        store.setCookie(stale) { prepared.fulfill() }
        wait(for: [prepared], timeout: 5)
        let authenticated = expectation(description: "original session verified after handoff")
        let probe = NativeLoginSessionProbe(origin: origin, store: store, session: session, cookieStorage: cookies) { authenticated.fulfill() }
        defer { probe.stop() }
        probe.check(); probe.pause()
        let fresh = try XCTUnwrap(HTTPCookie(properties: [.domain: "localhost", .path: "/", .name: "ink-dream-browser", .value: "fixture-new-handle"]))
        cookies.setCookie(fresh)
        AccountProbeProtocol.received = { request in
            XCTAssertEqual(request.url?.absoluteString, "http://localhost:5173/auth/session")
            XCTAssertFalse((request.value(forHTTPHeaderField: "Cookie") ?? "").contains("fixture-old-transaction"))
        }
        let copied = expectation(description: "Native result copied before probe resumes")
        probe.copyNativeCookies { copied.fulfill() }
        wait(for: [copied], timeout: 5)
        XCTAssertEqual(cookies.cookies(for: origin)?.first(where: { $0.name == fresh.name })?.value, fresh.value)
        let observed = expectation(description: "WK accepted native handle and removed transaction")
        store.getAllCookies { values in
            XCTAssertEqual(values.first(where: { $0.name == fresh.name })?.value, fresh.value)
            XCTAssertNil(values.first(where: { $0.name == stale.name }))
            observed.fulfill()
        }
        wait(for: [observed], timeout: 5)
        probe.resume()
        wait(for: [authenticated], timeout: 5)
    }

    @MainActor func testRealWKCallbackUsesManualHTTPRedirectCookiesAndOriginalSessionBeforeCompletion() throws {
        let server = try AccountHTTPFixture()
        defer { server.stop() }
        var local: URL?
        let listening = expectation(description: "App-owned loopback HTTP fixture")
        server.start { local = $0; listening.fulfill() }
        wait(for: [listening], timeout: 5)
        let origin = try XCTUnwrap(local)
        let store = WKWebsiteDataStore.nonPersistent()
        let cookie = try XCTUnwrap(HTTPCookie(properties: [.domain: "127.0.0.1", .path: "/", .name: "ink-dream-login", .value: "fixture-original-transaction"]))
        let configured = expectation(description: "original transaction in retained WK document")
        store.httpCookieStore.setCookie(cookie) { configured.fulfill() }
        wait(for: [configured], timeout: 5)
        let authenticated = expectation(description: "original session endpoint accepted after callback")
        let probe = NativeLoginSessionProbe(origin: origin, store: store.httpCookieStore) { authenticated.fulfill() }
        let navigation = UINavigationController()
        let transferred = expectation(description: "native Cookie handoff completed")
        let account = NativeAccountLogin(origin: origin, callback: callback, navigation: navigation, probe: probe, chinese: false) { transferred.fulfill() }
        defer {
            account.cancel(); probe.stop()
            for cookie in HTTPCookieStorage.shared.cookies(for: origin) ?? [] { HTTPCookieStorage.shared.deleteCookie(cookie) }
        }
        let loaded = expectation(description: "retained WK source loaded")
        let delegate = AccountNavigationFixture(account: account, loaded: loaded)
        let configuration = WKWebViewConfiguration(); configuration.websiteDataStore = store
        let web = WKWebView(frame: .zero, configuration: configuration); web.navigationDelegate = delegate
        web.loadHTMLString("<html><body>Account callback transport qualification</body></html>", baseURL: origin)
        wait(for: [loaded], timeout: 5)
        let returned = callback.absoluteString + "?code=fixture%2Bcode&state=" + state + "&iss=https%3A%2F%2Fadmin.example%2Fapi%2Fauth"
        let encoded = String(data: try JSONSerialization.data(withJSONObject: [returned]), encoding: .utf8)!
        web.evaluateJavaScript("window.location.href = \(encoded)[0]") { _, _ in }
        wait(for: [transferred, authenticated], timeout: 10)
        XCTAssertEqual(server.paths().count, 2)
        XCTAssertTrue(server.paths().first?.hasPrefix("/auth/callback?") == true)
        XCTAssertEqual(server.paths().last, "/auth/session")
    }
}
