// [Input] Bundled Dream Python entry and JSON requests.
// [Output] Actual backend results on the main queue.
// [Pos] Serialized interpreter startup and concurrent calls into the persistent Python event loop.
// [Sync] 2026-10-25: allow response reads and HTTP cancellation to execute concurrently.
// [Sync] 2026-10-25: execute business routes with bounded inline bodies and validated headers.
// [Sync] 2026-10-25: initialize the application-process original Runtime before binding Python startup.
// [Sync] 2026-10-27: coalesce App/RN/WebView startup and retain ready facts for process lifetime.
// [Sync] 2026-11-02: log fixed startup phases and cached/coalesced calls with monotonic durations; retain startup results.
import Foundation

final class EmbeddedDreamBackend {
    static let shared = EmbeddedDreamBackend()
    private let startupQueue = DispatchQueue(label: "com.inkmemory.mobile.python.startup")
    private let queue = DispatchQueue(label: "com.inkmemory.mobile.python", attributes: .concurrent)
    private var readyFacts: [String: Any]?
    private var starting = false
    private var startupWaiters: [(Result<[String: Any], Error>) -> Void] = []
    private var startupAttempt = 0
    private var startupTick: TimeInterval = 0
    private init() {}

    func start(completion: @escaping (Result<[String: Any], Error>) -> Void) {
        let requested = ProcessInfo.processInfo.systemUptime
        startupQueue.async {
            if let facts = self.readyFacts {
                self.observe("cached_ready", since: requested)
                DispatchQueue.main.async { completion(.success(facts)) }
                return
            }
            self.startupWaiters.append(completion)
            guard !self.starting else {
                self.observe("coalesced_waiter", since: requested)
                return
            }
            self.starting = true
            self.startupAttempt += 1
            self.startupTick = ProcessInfo.processInfo.systemUptime
            self.observe("queue_wait", since: requested)
            self.initializeRuntime()
        }
    }

    // Fixed metadata only: request bodies, endpoints, account IDs and errors stay in their original owners.
    private func observe(_ phase: String, since tick: TimeInterval, success: Bool = true) {
        let record: [String: Any] = [
            "layer": "native", "phase": phase, "outcome": success ? "ok" : "failed",
            "elapsedMs": (ProcessInfo.processInfo.systemUptime - tick) * 1000,
            "timestampMs": Date().timeIntervalSince1970 * 1000,
            "pid": ProcessInfo.processInfo.processIdentifier, "attempt": startupAttempt,
        ]
        if let data = try? JSONSerialization.data(withJSONObject: record), let line = String(data: data, encoding: .utf8) {
            fputs("DREAM_STARTUP " + line + "\n", stderr)
        }
    }

    private func finishStartup(_ result: Result<[String: Any], Error>, bindingTick: TimeInterval? = nil) {
        startupQueue.async {
            let succeeded: Bool
            if case .success = result { succeeded = true } else { succeeded = false }
            if let bindingTick { self.observe("python_runtime_bind", since: bindingTick, success: succeeded) }
            self.observe("startup_total", since: self.startupTick, success: succeeded)
            if case .success(let facts) = result { self.readyFacts = facts }
            self.starting = false
            let waiters = self.startupWaiters
            self.startupWaiters.removeAll()
            DispatchQueue.main.async { waiters.forEach { $0(result) } }
        }
    }

    private func initializeRuntime() {
            var phase = "python_public_bootstrap"
            var tick = ProcessInfo.processInfo.systemUptime
            do {
                guard let resources = Bundle.main.resourcePath else { throw CocoaError(.fileNoSuchFile) }
                var failure: NSError?
                // CPython owns initialization of its standard-library extensions.
                // Keep the interpreter-first order qualified by the native SDK test.
                guard IMDreamPythonCall(resources, "start", nil, &failure) != nil else {
                    throw failure ?? CocoaError(.coderInvalidValue) as NSError
                }
                observe(phase, since: tick)
                phase = "node_host_launch"; tick = ProcessInfo.processInfo.systemUptime
                guard let endpoint = IMDreamNodeStart(resources, &failure) else {
                    throw failure ?? CocoaError(.coderInvalidValue) as NSError
                }
                observe(phase, since: tick)
                phase = "node_endpoint_wait"; tick = ProcessInfo.processInfo.systemUptime
                let deadline = Date().addingTimeInterval(15)
                while !FileManager.default.fileExists(atPath: endpoint) && Date() < deadline {
                    Thread.sleep(forTimeInterval: 0.05)
                }
                guard FileManager.default.fileExists(atPath: endpoint) else {
                    throw NSError(domain: "InkMemory.DreamNode", code: 2,
                                  userInfo: [NSLocalizedDescriptionKey: "Embedded Node did not start."])
                }
                observe(phase, since: tick)
                phase = "python_runtime_bind"; tick = ProcessInfo.processInfo.systemUptime
                let data = try JSONSerialization.data(withJSONObject: ["runtimeEndpoint": endpoint])
                let bindingTick = tick
                self.call("start", payload: String(decoding: data, as: UTF8.self)) { result in
                    self.finishStartup(result, bindingTick: bindingTick)
                }
            } catch {
                observe(phase, since: tick, success: false)
                finishStartup(.failure(error))
            }
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
