// [Input] The native host's account-scoped local Thread observation.
// [Output] One binary Live Activity payload shared by the app and widget targets.
// [Pos] Display DTO only; no task identity, credentials, networking or execution.
import ActivityKit

struct ThreadActivityAttributes: ActivityAttributes {
    struct ContentState: Codable, Hashable {
        var hasActiveThread: Bool
    }
}
