// [Input] Original authenticated session read and Factory observations from the embedded interpreter.
// [Output] One account-scoped binary snapshot for React Native and ActivityKit.
// [Pos] Native display adapter; no task control, background execution grant, polling or second runtime.
import Foundation
import ActivityKit
import UIKit

@MainActor
final class NativeThreadPresence {
    private var owner: String?
    private var expectedOwner: String?
    private var generation = UUID().uuidString
    private var sequence = 0
    private var observation: NSObjectProtocol?
    private var verification: URLSessionDataTask?
    private var session: URLSession?
    private let redirects = PresenceRedirectPolicy()
    private var task: Task<Void, Never>?
    private var revision = 0
    private var known = false
    private var subscribed = false
    private var activityRequested = false
    private var active = false
    private var observedAt: Double?
    var changed: (([String: Any]) -> Void)?

    init() {
        observation = NotificationCenter.default.addObserver(forName: Notification.Name("InkThreadPresenceObservation"), object: nil, queue: .main) { [weak self] event in
            guard let value = event.userInfo as? [String: Any] else { return }
            MainActor.assumeIsolated { self?.receive(value) }
        }
        // Previous process observations belong to that process; opening never replays work.
        Task { for activity in Activity<ThreadActivityAttributes>.activities { await activity.end(nil, dismissalPolicy: .immediate) } }
    }

    var snapshot: [String: Any] {
        var value: [String: Any] = ["known": known]
        if let owner { value["ownerId"] = owner }
        if known { value["hasActiveThread"] = active; value["observedAt"] = observedAt }
        return value
    }

    func configure(expected: String?, origin: URL?, completion: @escaping (Result<[String: Any], Error>) -> Void) {
        if expectedOwner == expected, expected != nil, owner == expected, subscribed { reconcile(); completion(.success(snapshot)); return }
        clear()
        expectedOwner = expected
        guard let expected, let origin else { completion(.success(snapshot)); return }
        let binding = generation
        var request = URLRequest(url: URL(string: "/auth/session", relativeTo: origin)!.absoluteURL)
        request.cachePolicy = .reloadIgnoringLocalCacheData
        let configuration = URLSessionConfiguration.default
        configuration.httpCookieStorage = .shared
        let verifier = URLSession(configuration: configuration, delegate: redirects, delegateQueue: nil)
        session = verifier
        verification = verifier.dataTask(with: request) { [weak self] data, response, error in
            Task { @MainActor in
                guard let self, self.generation == binding else { completion(.failure(CocoaError(.userCancelled))); return }
                guard error == nil, (response as? HTTPURLResponse)?.statusCode == 200,
                      let data, let body = try? JSONSerialization.jsonObject(with: data) as? [String: Any],
                      let user = body["user"] as? [String: Any], let identifier = user["id"],
                      String(describing: identifier) == expected else {
                    completion(.failure(NSError(domain: "InkMemory.ThreadPresence", code: 1, userInfo: [NSLocalizedDescriptionKey: "无法确认活跃状态所属会话。"])))
                    return
                }
                self.owner = expected
                EmbeddedDreamBackend.shared.configureThreadPresence(["actorId": expected, "generation": binding]) { result in
                    guard self.generation == binding else { completion(.failure(CocoaError(.userCancelled))); return }
                    if case .success = result { self.subscribed = true }
                    completion(result.map { _ in self.snapshot })
                }
            }
        }
        verification?.resume()
    }

    func receive(_ value: [String: Any]) {
        guard let owner, value["ownerId"] as? String == owner,
              value["generation"] as? String == generation,
              let incoming = value["sequence"] as? Int, incoming > sequence,
              let active = value["hasActiveThread"] as? Bool,
              let time = value["observedAt"] as? Double, time.isFinite else { return }
        sequence = incoming; known = true; self.active = active; observedAt = time
        if !active { activityRequested = false }
        changed?(snapshot)
        reconcile()
    }

    func clear() {
        let old = generation
        generation = UUID().uuidString; owner = nil; expectedOwner = nil
        known = false; subscribed = false; activityRequested = false; sequence = 0; active = false; observedAt = nil; revision += 1
        verification?.cancel(); verification = nil; session?.invalidateAndCancel(); session = nil
        EmbeddedDreamBackend.shared.configureThreadPresence(["generation": old, "release": true]) { _ in }
        changed?(snapshot)
        reconcile()
    }

    private func reconcile() {
        revision += 1
        guard task == nil else { return }
        task = Task { [weak self] in
            guard let self else { return }
            var applied = -1
            while applied != self.revision {
                applied = self.revision
                let binding = self.generation
                var activities = Activity<ThreadActivityAttributes>.activities
                if !self.known || self.owner == nil {
                    for item in activities { await item.end(nil, dismissalPolicy: .immediate) }
                    continue
                }
                // The widget is a last observation; a suspended app cannot publish live values.
                let content = ActivityContent(state: ThreadActivityAttributes.ContentState(hasActiveThread: self.active), staleDate: Date(timeIntervalSince1970: (self.observedAt ?? 0) / 1000))
                if !self.active {
                    for item in activities { await item.end(content, dismissalPolicy: .default) }
                    continue
                }
                let current = activities.first(where: { $0.activityState == .active || $0.activityState == .stale })
                for item in activities where item.id != current?.id { await item.end(nil, dismissalPolicy: .immediate) }
                guard binding == self.generation else { continue }
                if let current { self.activityRequested = true; await current.update(content) }
                else if !self.activityRequested && UIApplication.shared.applicationState == .active && ActivityAuthorizationInfo().areActivitiesEnabled {
                    do {
                        activities = [try Activity.request(attributes: ThreadActivityAttributes(), content: content, pushType: nil)]
                        self.activityRequested = true
                    }
                    catch { NSLog("Thread presence system display unavailable") }
                }
            }
            self.task = nil
        }
    }

    deinit {
        if let observation { NotificationCenter.default.removeObserver(observation) }
        verification?.cancel(); session?.invalidateAndCancel()
    }
}

private final class PresenceRedirectPolicy: NSObject, URLSessionTaskDelegate {
    func urlSession(_ session: URLSession, task: URLSessionTask, willPerformHTTPRedirection response: HTTPURLResponse, newRequest request: URLRequest, completionHandler: @escaping (URLRequest?) -> Void) {
        completionHandler(nil)
    }
}
