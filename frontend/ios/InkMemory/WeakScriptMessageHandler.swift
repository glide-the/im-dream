// [Input] WKWebView script messages and a weak application-owned delegate.
// [Output] Forwarded messages without retaining the host view controller.
// [Pos] WebKit lifecycle adapter that breaks the user-content-controller retain cycle.
// [Sync] 2026-10-24: add weak message forwarding for deterministic host cleanup.

import WebKit

final class WeakScriptMessageHandler: NSObject, WKScriptMessageHandler {
    weak var delegate: WKScriptMessageHandler?

    init(delegate: WKScriptMessageHandler) {
        self.delegate = delegate
    }

    func userContentController(_ userContentController: WKUserContentController, didReceive message: WKScriptMessage) {
        delegate?.userContentController(userContentController, didReceive: message)
    }
}
