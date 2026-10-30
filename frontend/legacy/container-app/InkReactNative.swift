// [Input] Historical RN container adapter; retained outside all active bundles.
// [Output] Promise-based runtime readiness and one persistent business surface per RN view.
// [Pos] iOS RN adapter; authentication and business execution retain original owners.
import React
import UIKit

@objc(InkRuntime)
final class InkRuntime: NSObject {
    @objc static func requiresMainQueueSetup() -> Bool { true }

    @objc(ensureStarted:rejecter:)
    func ensureStarted(_ resolve: @escaping RCTPromiseResolveBlock, rejecter reject: @escaping RCTPromiseRejectBlock) {
        EmbeddedDreamBackend.shared.start { result in
            switch result {
            case .success(let facts):
                guard let origin = facts["localWebOrigin"] as? String,
                      let url = URL(string: origin),
                      ["localhost", "127.0.0.1", "::1", "[::1]"].contains(url.host ?? "") else {
                    reject("RUNTIME_ORIGIN_INVALID", "本机服务地址无效。", nil)
                    return
                }
                resolve(["state": "ready", "localWebOrigin": origin])
            case .failure(let error):
                reject("RUNTIME_START_FAILED", "本机服务启动失败，请重试。", error)
            }
        }
    }
}

@objc(InkBusinessSurface)
final class InkBusinessSurface: UIView {
    private let controller = MobileHostViewController()
    @objc var onHostState: RCTDirectEventBlock? {
        didSet { if let state = lastState { onHostState?(state) } }
    }
    private var lastState: [String: Any]?
    @objc var logoutRequest: NSNumber = 0 {
        didSet { if logoutRequest.intValue > 0 { controller.logoutFromHost() } }
    }
    @objc var navigationRequest: NSDictionary? {
        didSet {
            guard let path = navigationRequest?["path"] as? String else { return }
            controller.navigateFromHost(path)
        }
    }

    override init(frame: CGRect) {
        super.init(frame: frame)
        controller.reactNativeHost = true
        controller.hostStateDidChange = { [weak self] state in
            self?.lastState = state
            self?.onHostState?(state)
        }
        controller.loadViewIfNeeded()
        addSubview(controller.view)
    }
    required init?(coder: NSCoder) { fatalError("init(coder:) is unavailable") }
    override func layoutSubviews() {
        super.layoutSubviews()
        controller.view.frame = bounds
    }
    override func didMoveToWindow() {
        super.didMoveToWindow()
        guard window != nil, controller.parent == nil else { return }
        var responder: UIResponder? = self
        while let current = responder {
            if let parent = current as? UIViewController {
                parent.addChild(controller)
                controller.didMove(toParent: parent)
                break
            }
            responder = current.next
        }
    }
    deinit {
        controller.willMove(toParent: nil)
        controller.view.removeFromSuperview()
        controller.removeFromParent()
    }
}
