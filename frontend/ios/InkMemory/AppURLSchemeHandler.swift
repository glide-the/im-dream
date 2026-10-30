// [Input] Requests for the fixed ink-memory://app origin and generated Web resources in the app bundle.
// [Output] Method-limited, root-contained local asset responses, route fallback, and explicit unavailable API responses.
// [Pos] iOS WebView local-origin owner.
// [Sync] 2026-10-25: allow the normal localhost Web/BFF flow through the native LAN relay.
// [Sync] 2026-10-25: separate normal HTTPS main-frame navigation from local bridge/resource authority.
// [Sync] 2026-10-24: restrict local resource requests to GET/HEAD and contain decoded paths under the packaged Web root.
// [Sync] 2026-10-24: serve shared React resources without file URL access or a listening TCP port.

import Foundation
import UniformTypeIdentifiers
import WebKit

enum AppNavigationPolicy {
    static func allows(_ url: URL?, mainFrame: Bool) -> Bool {
        guard mainFrame, let url, url.user == nil, url.password == nil else { return false }
        if url.scheme == "ink-memory" { return url.host == "app" }
        if LocalDevelopmentTopology.isLoopbackWebURL(url) { return true }
        // Existing AuthEntry uses top-level HTTPS form navigation. Remote pages receive no bridge.
        return url.scheme == "https" && !(url.host ?? "").isEmpty
    }
}

final class AppURLSchemeHandler: NSObject, WKURLSchemeHandler {
    func webView(_ webView: WKWebView, start urlSchemeTask: WKURLSchemeTask) {
        guard let url = urlSchemeTask.request.url,
              let relative = AppResourceRequestPolicy.relativePath(for: url, method: urlSchemeTask.request.httpMethod) else {
            fail(urlSchemeTask, code: 403, message: "Invalid application origin.")
            return
        }
        if relative.hasPrefix("api/") || relative.hasPrefix("auth/") {
            fail(urlSchemeTask, code: 503, message: "The qualified local Dream transport is unavailable.")
            return
        }
        let resource = resourceURL(for: relative) ?? (relative.contains(".") ? nil : resourceURL(for: "index.html"))
        guard let resource, let data = try? Data(contentsOf: resource) else {
            fail(urlSchemeTask, code: 404, message: "Resource not found.")
            return
        }
        let mime = UTType(filenameExtension: resource.pathExtension)?.preferredMIMEType ?? "application/octet-stream"
        let response = URLResponse(url: url, mimeType: mime, expectedContentLength: data.count, textEncodingName: mime.hasPrefix("text/") || mime.contains("javascript") ? "utf-8" : nil)
        urlSchemeTask.didReceive(response)
        if urlSchemeTask.request.httpMethod?.uppercased() != "HEAD" { urlSchemeTask.didReceive(data) }
        urlSchemeTask.didFinish()
    }

    func webView(_ webView: WKWebView, stop urlSchemeTask: WKURLSchemeTask) {}

    private func resourceURL(for relativePath: String) -> URL? {
        guard let root = Bundle.main.resourceURL?.appendingPathComponent("web", isDirectory: true) else { return nil }
        return AppResourceRequestPolicy.resourceURL(for: relativePath, under: root)
    }

    private func fail(_ task: WKURLSchemeTask, code: Int, message: String) {
        let payload = try? JSONSerialization.data(withJSONObject: ["error": ["code": "CAPABILITY_UNAVAILABLE", "message": message]])
        let url = task.request.url ?? URL(string: "ink-memory://app/")!
        let response = HTTPURLResponse(url: url, statusCode: code, httpVersion: "HTTP/1.1", headerFields: ["Content-Type": "application/json; charset=utf-8"])
        if let response { task.didReceive(response) }
        if let payload { task.didReceive(payload) }
        task.didFinish()
    }
}

enum AppResourceRequestPolicy {
    static func relativePath(for url: URL, method: String?) -> String? {
        guard ["GET", "HEAD"].contains(method?.uppercased() ?? ""),
              url.scheme?.lowercased() == "ink-memory", url.host?.lowercased() == "app",
              url.user == nil, url.password == nil, url.port == nil,
              let encodedPath = URLComponents(url: url, resolvingAgainstBaseURL: false)?.percentEncodedPath,
              let decoded = encodedPath.removingPercentEncoding,
              !decoded.contains("%"), !decoded.contains("\\"),
              decoded.unicodeScalars.allSatisfy({ !CharacterSet.controlCharacters.contains($0) }) else { return nil }
        let components = decoded.split(separator: "/", omittingEmptySubsequences: true)
        guard components.allSatisfy({ $0 != "." && $0 != ".." }) else { return nil }
        return components.isEmpty ? "index.html" : components.joined(separator: "/")
    }

    static func resourceURL(for relativePath: String, under root: URL) -> URL? {
        let qualifiedRoot = root.standardizedFileURL.resolvingSymlinksInPath()
        let candidate = qualifiedRoot.appendingPathComponent(relativePath, isDirectory: false)
            .standardizedFileURL.resolvingSymlinksInPath()
        guard candidate.path.hasPrefix(qualifiedRoot.path + "/") else { return nil }
        return candidate
    }
}
