// [Input] Original account form navigation, BFF start/callback/session and target account URI.
// [Output] Operation-bound system authorization and original Cookie handoff to the retained login document.
// [Pos] iOS account login adapter; Admin, Client ID, PKCE, credentials and permissions retain their original owners.
// [Sync] 2026-11-02: report the failing account stage to the existing native diagnostics without replacing login completion.
// [Sync] 2026-11-02: carry the explicit Google selection through Admin's signed OAuth continuation.
// [Sync] 2026-10-31: use AuthenticationServices for Google and the original BFF for both system and password callbacks.
import AuthenticationServices
import UIKit
import WebKit

enum NativeAccountCallback {
    static func localOrigin(_ origin: URL) -> Bool {
        origin.scheme == "http" && ["localhost", "127.0.0.1", "::1", "[::1]"].contains(origin.host ?? "")
            && origin.user == nil && origin.password == nil && ["", "/"].contains(origin.path) && origin.query == nil && origin.fragment == nil
    }
    static func configuration(_ value: String) -> URL? {
        guard value.range(of: "^[a-z][a-z0-9-]*(\\.[a-z0-9][a-z0-9-]*)+\\.auth:/auth/callback$", options: .regularExpression) != nil,
              let url = URL(string: value), url.absoluteString == value else { return nil }
        return url
    }
    static func sameOrigin(_ url: URL, _ origin: URL) -> Bool {
        url.scheme == origin.scheme && url.host == origin.host && url.port == origin.port && url.user == nil && url.password == nil
    }
    static func targetMatches(_ url: URL, callback: URL) -> Bool {
        guard let value = URLComponents(url: url, resolvingAgainstBaseURL: false) else { return false }
        return configuration(callback.absoluteString) != nil && value.scheme == callback.scheme && value.host == nil
            && value.port == nil && value.user == nil && value.password == nil && value.fragment == nil
            && value.percentEncodedPath == "/auth/callback"
    }
    static func localRequest(_ url: URL, callback: URL, origin: URL, state: String? = nil) -> URL? {
        guard localOrigin(origin), targetMatches(url, callback: callback), let components = URLComponents(url: url, resolvingAgainstBaseURL: false) else { return nil }
        let items = components.queryItems ?? []
        for name in ["code", "state", "iss"] {
            let values = items.filter { $0.name == name }
            guard values.count == 1, let value = values.first?.value, !value.isEmpty else { return nil }
        }
        guard !items.contains(where: { $0.name == "error" }),
              let actualState = items.first(where: { $0.name == "state" })?.value,
              actualState.range(of: "^[A-Za-z0-9_-]{43}$", options: .regularExpression) != nil,
              state == nil || state == actualState,
              var destination = URLComponents(url: origin, resolvingAgainstBaseURL: false) else { return nil }
        destination.percentEncodedPath = "/auth/callback"; destination.percentEncodedQuery = components.percentEncodedQuery
        destination.fragment = nil
        return destination.url
    }
    static func googleAction(_ data: Data?, response: HTTPURLResponse?, origin: URL) -> URL? {
        guard response?.statusCode == 200, let received = response?.url, sameOrigin(received, origin), received.path == "/auth/options",
              let data, let object = (try? JSONSerialization.jsonObject(with: data)) as? [String: String],
              Set(object.keys) == Set(["google_action", "password_action"]),
              let raw = object["google_action"], let google = URL(string: raw), let password = object["password_action"].flatMap(URL.init(string:)),
              google.path == "/auth/dream/google", password.path == "/auth/dream/password", sameOrigin(password, google),
              google.user == nil, google.password == nil, google.query == nil, google.fragment == nil,
              password.query == nil, password.fragment == nil,
              google.scheme == "https" || (google.scheme == "http" && ["localhost", "127.0.0.1", "::1", "[::1]"].contains(google.host ?? "")) else { return nil }
        return google
    }
    static func authorization(_ location: String, admin: URL, callback: URL) -> (url: URL, state: String)? {
        guard configuration(callback.absoluteString) != nil, var value = URLComponents(string: location), let url = value.url,
              sameOrigin(url, admin), value.percentEncodedPath == "/api/auth/oauth2/authorize", value.fragment == nil else { return nil }
        let items = value.queryItems ?? []
        func one(_ name: String) -> String? {
            let values = items.filter { $0.name == name }
            return values.count == 1 ? values.first?.value : nil
        }
        guard one("response_type") == "code", one("redirect_uri") == callback.absoluteString,
              one("code_challenge_method") == "S256", let client = one("client_id"), !client.isEmpty,
              let scope = one("scope"), !scope.isEmpty, let resource = one("resource"), !resource.isEmpty,
              let state = one("state"), let nonce = one("nonce"), let challenge = one("code_challenge"),
              [state, nonce, challenge].allSatisfy({ $0.range(of: "^[A-Za-z0-9_-]{43}$", options: .regularExpression) != nil }),
              items.filter({ $0.name == "prompt" }).isEmpty || one("prompt") == "login",
              items.filter({ $0.name == "identity_provider" }).isEmpty || one("identity_provider") == "google" else { return nil }
        value.queryItems = items
            + (one("prompt") == nil ? [URLQueryItem(name: "prompt", value: "login")] : [])
            + (one("identity_provider") == nil ? [URLQueryItem(name: "identity_provider", value: "google")] : [])
        guard let selected = value.url else { return nil }
        return (selected, state)
    }
    static func returnLocation(_ page: URL, origin: URL) -> String? {
        guard sameOrigin(page, origin), let value = URLComponents(url: page, resolvingAgainstBaseURL: false) else { return nil }
        let query = value.percentEncodedQuery.map { raw in
            raw.components(separatedBy: "&").filter { part in
                let key = part.components(separatedBy: "=").first ?? ""
                return key.removingPercentEncoding != "auth_error"
            }.joined(separator: "&")
        }
        let path = value.percentEncodedPath.isEmpty ? "/" : value.percentEncodedPath
        return path + (query.flatMap { $0.isEmpty ? nil : "?" + $0 } ?? "")
    }
}

final class NativeAccountLogin: NSObject, URLSessionTaskDelegate, ASWebAuthenticationPresentationContextProviding {
    private let origin: URL
    private let callback: URL?
    private weak var navigation: UINavigationController?
    private let probe: NativeLoginSessionProbe
    private let webReady: () -> Void
    private let chinese: Bool
    private var operation: UUID?
    private var task: URLSessionDataTask?
    private var authorization: ASWebAuthenticationSession?
    private var stopped = false
    private var transport: URLSession?
    private let diagnostic: ([String: Any]) -> Void
    private var stage = "preparing"
    private var lastReportedStage: String?

    init(origin: URL, callback: URL?, navigation: UINavigationController, probe: NativeLoginSessionProbe, chinese: Bool, diagnostic: @escaping ([String: Any]) -> Void = { _ in }, webReady: @escaping () -> Void) {
        self.origin = origin; self.callback = NativeAccountCallback.localOrigin(origin) ? callback : nil
        self.navigation = navigation; self.probe = probe; self.chinese = chinese; self.webReady = webReady
        self.diagnostic = diagnostic
    }
    func handles(_ action: WKNavigationAction, page: URL?) -> Bool {
        guard !stopped, action.targetFrame?.isMainFrame == true, let destination = action.request.url else { return false }
        if let callback, NativeAccountCallback.targetMatches(destination, callback: callback) {
            guard operation == nil else { return true }
            let id = UUID(); operation = id; probe.pause()
            probe.copyWebCookies { [weak self] in
                guard let self, self.operation == id else { return }
                self.complete(destination, id: id, state: nil)
            }
            return true
        }
        guard action.sourceFrame.isMainFrame, action.navigationType == .formSubmitted, action.request.httpMethod == "POST", destination.path == "/auth/dream/google",
              let page, let returnTo = NativeAccountCallback.returnLocation(page, origin: origin) else { return false }
        guard operation == nil else { return true }
        let id = UUID(); operation = id; probe.pause()
        stage = "configuration"
        lastReportedStage = nil
        guard let callback else { failure(id: id); return true }
        probe.copyWebCookies { [weak self] in
            guard let self, self.operation == id else { return }
            self.fetch(URL(string: "/auth/options", relativeTo: self.origin)!.absoluteURL, id: id) { data, response, error in
                guard error == nil, let google = NativeAccountCallback.googleAction(data, response: response, origin: self.origin), google == destination else { self.failure(id: id); return }
                var start = URLComponents(url: URL(string: "/auth/start", relativeTo: self.origin)!.absoluteURL, resolvingAgainstBaseURL: false)!
                start.queryItems = [URLQueryItem(name: "return_to", value: returnTo)]
                self.stage = "authorization-configuration"
                self.fetch(start.url!, id: id) { _, response, error in
                    guard error == nil, response?.statusCode == 303, let received = response?.url,
                          NativeAccountCallback.sameOrigin(received, self.origin), received.path == "/auth/start",
                          let location = response?.value(forHTTPHeaderField: "Location"),
                          let prepared = NativeAccountCallback.authorization(location, admin: google, callback: callback) else {
                        if error == nil, let location = response?.value(forHTTPHeaderField: "Location"),
                           let components = URLComponents(string: location),
                           let received = components.queryItems?.first(where: { $0.name == "redirect_uri" })?.value,
                           received != callback.absoluteString {
                            self.report(NSError(domain: "InkAccountLogin", code: 1, userInfo: [NSLocalizedDescriptionKey: "OAuth callback mismatch: BFF uses \(received); app expects \(callback.absoluteString)."]), stage: self.stage)
                            self.failure(id: id, report: false)
                        } else { self.failure(id: id, error: error) }
                        return
                    }
                    self.authorize(prepared.url, state: prepared.state, callback: callback, id: id)
                }
            }
        }
        return true
    }
    private func authorize(_ url: URL, state: String, callback: URL, id: UUID) {
        stage = "system-authorization"
        guard navigation?.viewIfLoaded?.window != nil else { failure(id: id); return }
        let completed: ASWebAuthenticationSession.CompletionHandler = { [weak self] url, error in
            DispatchQueue.main.async {
                guard let self, self.operation == id, !self.stopped else { return }
                self.authorization = nil
                if (error as? ASWebAuthenticationSessionError)?.code == .canceledLogin { self.restore(); return }
                guard error == nil, let url else { self.failure(id: id, error: error); return }
                self.complete(url, id: id, state: state)
            }
        }
        let session: ASWebAuthenticationSession
        if #available(iOS 17.4, *) { session = ASWebAuthenticationSession(url: url, callback: .customScheme(callback.scheme!), completionHandler: completed) }
        else { session = ASWebAuthenticationSession(url: url, callbackURLScheme: callback.scheme!, completionHandler: completed) }
        authorization = session; session.presentationContextProvider = self
        if !session.start() { authorization = nil; failure(id: id) }
    }
    private func complete(_ returned: URL, id: UUID, state: String?) {
        stage = "callback"
        guard let callback, let url = NativeAccountCallback.localRequest(returned, callback: callback, origin: origin, state: state) else { failure(id: id); return }
        fetch(url, id: id) { _, response, error in
            guard error == nil, response?.statusCode == 303, let received = response?.url,
                  NativeAccountCallback.sameOrigin(received, self.origin), received.path == "/auth/callback" else {
                self.failure(id: id, error: error, retry: error != nil || (response?.statusCode ?? 503) >= 500 ? { [weak self] in self?.complete(returned, id: id, state: state) } : nil)
                return
            }
            self.probe.copyNativeCookies {
                guard self.operation == id, !self.stopped else { return }
                self.operation = nil; self.probe.resume(); self.webReady()
            }
        }
    }
    private func fetch(_ url: URL, id: UUID, completed: @escaping (Data?, HTTPURLResponse?, Error?) -> Void) {
        guard !stopped, operation == id else { return }
        var request = URLRequest(url: url); request.cachePolicy = .reloadIgnoringLocalCacheData
        let session = transport ?? URLSession(configuration: .default, delegate: self, delegateQueue: .main)
        transport = session
        task = session.dataTask(with: request) { [weak self] data, response, error in
            DispatchQueue.main.async {
                guard let self, !self.stopped, self.operation == id else { return }
                self.task = nil
                if let error { self.report(error, stage: self.stage) }
                else if let response = response as? HTTPURLResponse, response.statusCode >= 400 {
                    self.report(NSError(domain: "InkAccountHTTP", code: response.statusCode, userInfo: [NSLocalizedDescriptionKey: "HTTP \(response.statusCode) at \(self.stage)"]), stage: self.stage)
                }
                completed(data, response as? HTTPURLResponse, error)
            }
        }
        task?.resume()
    }
    func urlSession(_ session: URLSession, task: URLSessionTask, willPerformHTTPRedirection response: HTTPURLResponse, newRequest request: URLRequest, completionHandler: @escaping (URLRequest?) -> Void) { completionHandler(nil) }
    func presentationAnchor(for session: ASWebAuthenticationSession) -> ASPresentationAnchor { navigation?.view.window ?? ASPresentationAnchor() }
    private func report(_ error: Error, stage: String) {
        lastReportedStage = stage
        let value = error as NSError
        diagnostic(["source": "google", "error": ["phase": stage, "domain": value.domain, "code": value.code, "message": value.localizedDescription]])
    }
    private func failure(id: UUID, error: Error? = nil, report shouldReport: Bool = true, retry: (() -> Void)? = nil) {
        guard !stopped, operation == id else { return }
        if shouldReport && (error != nil || lastReportedStage != stage) { report(error ?? NSError(domain: "InkAccountLogin", code: 2, userInfo: [NSLocalizedDescriptionKey: "Google login could not complete at \(stage)."]), stage: stage) }
        guard let navigation, navigation.presentedViewController == nil else { restore(); return }
        let alert = UIAlertController(title: chinese ? "登录未完成" : "Login incomplete", message: chinese ? "登录未完成，请重试。" : "Login could not be completed. Please try again.", preferredStyle: .alert)
        if let retry { alert.addAction(UIAlertAction(title: chinese ? "重试" : "Retry", style: .default) { [weak self] _ in guard self?.operation == id else { return }; retry() }) }
        alert.addAction(UIAlertAction(title: chinese ? "关闭" : "Close", style: .cancel) { [weak self] _ in guard self?.operation == id else { return }; self?.restore() })
        navigation.present(alert, animated: true)
    }
    private func restore() { operation = nil; task?.cancel(); task = nil; authorization?.cancel(); authorization = nil; probe.resume() }
    func cancel() { guard !stopped else { return }; stopped = true; operation = nil; task?.cancel(); task = nil; authorization?.cancel(); authorization = nil; transport?.invalidateAndCancel(); transport = nil }
}
