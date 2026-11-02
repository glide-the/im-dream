// [Input] Bundled Dream Python entry and JSON requests.
// [Output] Actual backend results on the main queue.
// [Pos] Serialized interpreter startup and concurrent calls into the persistent Python event loop.
// [Sync] 2026-10-25: allow response reads and HTTP cancellation to execute concurrently.
// [Sync] 2026-10-25: execute business routes with bounded inline bodies and validated headers.
// [Sync] 2026-10-25: initialize the application-process original Runtime before binding Python startup.
// [Sync] 2026-10-27: coalesce App/RN/WebView startup and retain ready facts for process lifetime.
import Foundation

final class EmbeddedDreamBackend {
    static let shared = EmbeddedDreamBackend()
    private let startupQueue = DispatchQueue(label: "com.inkmemory.mobile.python.startup")
    private let queue = DispatchQueue(label: "com.inkmemory.mobile.python", attributes: .concurrent)
    private var readyFacts: [String: Any]?
    private var starting = false
    private var startupWaiters: [(Result<[String: Any], Error>) -> Void] = []
    private init() {}

    func start(completion: @escaping (Result<[String: Any], Error>) -> Void) {
        startupQueue.async {
            if let facts = self.readyFacts {
                DispatchQueue.main.async { completion(.success(facts)) }
                return
            }
            self.startupWaiters.append(completion)
            guard !self.starting else { return }
            self.starting = true
            self.initializeRuntime()
        }
    }

    private func finishStartup(_ result: Result<[String: Any], Error>) {
        startupQueue.async {
            if case .success(let facts) = result { self.readyFacts = facts }
            self.starting = false
            let waiters = self.startupWaiters
            self.startupWaiters.removeAll()
            DispatchQueue.main.async { waiters.forEach { $0(result) } }
        }
    }

    private func initializeRuntime() {
            do {
                guard let resources = Bundle.main.resourcePath else { throw CocoaError(.fileNoSuchFile) }
                var failure: NSError?
                // CPython owns initialization of its standard-library extensions.
                // Keep the interpreter-first order qualified by the native SDK test.
                guard IMDreamPythonCall(resources, "start", nil, &failure) != nil else {
                    throw failure ?? CocoaError(.coderInvalidValue) as NSError
                }
                guard let endpoint = IMDreamNodeStart(resources, &failure) else {
                    throw failure ?? CocoaError(.coderInvalidValue) as NSError
                }
                let deadline = Date().addingTimeInterval(15)
                while !FileManager.default.fileExists(atPath: endpoint) && Date() < deadline {
                    Thread.sleep(forTimeInterval: 0.05)
                }
                guard FileManager.default.fileExists(atPath: endpoint) else {
                    throw NSError(domain: "InkMemory.DreamNode", code: 2,
                                  userInfo: [NSLocalizedDescriptionKey: "Embedded Node did not start."])
                }
                let data = try JSONSerialization.data(withJSONObject: ["runtimeEndpoint": endpoint])
                self.call("start", payload: String(decoding: data, as: UTF8.self)) { self.finishStartup($0) }
            } catch { finishStartup(.failure(error)) }
    }

    func request(method: String, path: String, headers: [String: String] = [:], body: Data? = nil,
                 completion: @escaping (Result<[String: Any], Error>) -> Void) {
        do {
            let data = try JSONSerialization.data(withJSONObject: [
                "method": method, "path": path, "headers": headers,
                "bodyBase64": body.map { $0.base64EncodedString() as Any } ?? NSNull(),
            ])
            call("request", payload: String(decoding: data, as: UTF8.self), completion: completion)
        } catch { completion(.failure(error)) }
    }

    func bridge(_ request: MobileBridgeRequest, completion: @escaping (Result<[String: Any], Error>) -> Void) {
        do {
            let data = try JSONSerialization.data(withJSONObject: [
                "method": request.method, "pageGeneration": request.pageGeneration, "params": request.params,
            ])
            call("bridge", payload: String(decoding: data, as: UTF8.self), completion: completion)
        } catch { completion(.failure(error)) }
    }

    func closeDocument(_ generation: String) {
        guard let data = try? JSONSerialization.data(withJSONObject: ["pageGeneration": generation]) else { return }
        call("close_document", payload: String(decoding: data, as: UTF8.self)) { _ in }
    }

    private func call(_ function: String, payload: String?, completion: @escaping (Result<[String: Any], Error>) -> Void) {
        queue.async {
            let result = Result<[String: Any], Error> {
                guard let resources = Bundle.main.resourcePath else { throw CocoaError(.fileNoSuchFile) }
                var failure: NSError?
                guard let json = IMDreamPythonCall(resources, function, payload, &failure) else {
                    throw failure ?? CocoaError(.coderInvalidValue) as NSError
                }
                guard let value = try JSONSerialization.jsonObject(with: Data(json.utf8)) as? [String: Any] else {
                    throw CocoaError(.coderInvalidValue)
                }
                return value
            }
            DispatchQueue.main.async { completion(result) }
        }
    }
}
