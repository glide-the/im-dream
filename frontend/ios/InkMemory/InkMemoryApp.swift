// [Input] SwiftUI lifecycle, UIKit host and the existing page's background/theme projection.
// [Sync] 2026-11-03: expose diagnostics occupation to the idle overlay eligibility check.
// [Sync] 2026-11-03: reuse the launch screen's StartupArtwork vector asset for the diagnostics entry, preserving its appearance variants and original colors.
// [Sync] 2026-11-02: host scene-local diagnostics above app-owned sheets with a non-key, button-only hit region and the original JS bridge.
// [Sync] 2026-11-02: inherit the original window's applied appearance before mounting the diagnostics root.
// [Sync] 2026-11-03: follow same-scene React Native alert windows above their actual level; preserve the alert's key window and actions.
// [Sync] 2026-10-29: observe the original ink-theme preference for matching native insets and explicit/system appearance.
// [Output] One iOS scene containing the bundled React Native composition root.
// [Pos] iOS application entry.
// [Sync] 2026-11-02: reuse the static launch storyboard while the RN root loads its first content.
// [Sync] 2026-11-03: size the transparent RN loading surface to its host bounds instead of retaining the storyboard canvas.
// [Sync] 2026-10-24: extend through container insets while retaining the keyboard safe area.
// [Sync] 2026-10-24: create the first native iOS container entry.
// [Sync] 2026-10-25: keep the original Web header and composer inside the iPhone system safe area.
// [Sync] 2026-10-25: fill native insets with the page theme and use its explicit/system status-bar appearance.
// [Sync] 2026-10-27: RN owns the main interface; WebKit is retained for existing authentication and DOM integrations.
// [Sync] 2026-10-28: SwiftUI owns keyboard geometry; RN pages use the resulting viewport without a second inset.
// [Sync] 2026-10-28: extend only the project background through container insets; keep RN content below system status/navigation areas.
// [Sync] 2026-10-28: use SwiftUI's current proposed viewport instead of RCTRootView's cached intrinsic size when the keyboard changes the scene.

import SwiftUI
import UIKit
import React

@main
struct InkMemoryApp: App {
    @AppStorage("ink-theme") private var themeMode = "system"
    private var preferredScheme: ColorScheme? {
        themeMode == "dark" ? .dark : themeMode == "light" ? .light : nil
    }
    private var background: UIColor {
        if themeMode == "dark" { return UIColor(red: 29.0 / 255, green: 25.0 / 255, blue: 22.0 / 255, alpha: 1) }
        if themeMode == "light" { return UIColor(red: 246.0 / 255, green: 239.0 / 255, blue: 229.0 / 255, alpha: 1) }
        return MobileHostViewController.initialBackground
    }
    var body: some Scene {
        WindowGroup {
            ZStack {
                Color(uiColor: background)
                    .ignoresSafeArea(.container)
                ReactNativeAppView(background: background)
            }
            .preferredColorScheme(preferredScheme)
        }
    }
}

struct ReactNativeAppView: UIViewRepresentable {
    let background: UIColor
    func makeUIView(context: Context) -> UIView {
        guard let bundle = Bundle.main.url(forResource: "main", withExtension: "jsbundle") else {
            preconditionFailure("The packaged React Native bundle is missing.")
        }
        let root = StartupReactRootView(bundleURL: bundle, moduleName: "InkMemory", initialProperties: nil, launchOptions: nil)
        root.loadingView = UIStoryboard(name: "LaunchScreen", bundle: nil).instantiateInitialViewController()?.view
        root.loadingView?.backgroundColor = .clear
        root.loadingView?.isOpaque = false
        root.loadingViewFadeDelay = 0
        root.loadingViewFadeDuration = 0.15
        root.backgroundColor = background
        return root
    }
    func updateUIView(_ uiView: UIView, context: Context) { uiView.backgroundColor = background }

    func sizeThatFits(_ proposal: ProposedViewSize, uiView: UIView, context: Context) -> CGSize? {
        guard let width = proposal.width, let height = proposal.height,
              width.isFinite, height.isFinite else { return nil }
        return CGSize(width: width, height: height)
    }
}

private final class StartupReactRootView: RCTRootView {
    override func layoutSubviews() {
        super.layoutSubviews()
        loadingView?.frame = bounds
    }
}

// The floating window never becomes the keyboard/authentication presentation owner.
// Its full hit region is enabled only while the existing diagnostics leaf is open.
private final class DiagnosticsOverlayWindow: UIWindow {
    weak var diagnosticsController: DiagnosticsOverlayController?
    override var canBecomeKey: Bool { false }
    override func point(inside point: CGPoint, with event: UIEvent?) -> Bool {
        guard let controller = diagnosticsController else { return false }
        if controller.expanded { return super.point(inside: point, with: event) }
        return controller.button.frame.contains(controller.view.convert(point, from: self))
    }
}

private final class DiagnosticsOverlayController: UIViewController {
    let button = UIButton(type: .system)
    var expanded = false
    private var position = CGPoint(x: 1, y: 0.25)
    private var dragOrigin = CGPoint.zero
    private var keyboardFrame: CGRect?
    private var keyboardObserver: NSObjectProtocol?

    override func viewDidLoad() {
        super.viewDidLoad()
        view.backgroundColor = .clear
        button.setImage(UIImage(named: "StartupArtwork")?.withRenderingMode(.alwaysOriginal), for: .normal)
        button.imageView?.contentMode = .scaleAspectFit
        button.contentHorizontalAlignment = .fill
        button.contentVerticalAlignment = .fill
        button.accessibilityLabel = "开发者控制页"
        button.accessibilityHint = "打开运行状态。可拖动按钮调整位置。"
        button.accessibilityIdentifier = "ink-runtime-diagnostics-button"
        button.bounds.size = CGSize(width: 44, height: 44)
        button.layer.cornerRadius = 22
        button.layer.borderWidth = 1
        button.addGestureRecognizer(UIPanGestureRecognizer(target: self, action: #selector(drag(_:))))
        button.accessibilityCustomActions = [
            UIAccessibilityCustomAction(name: "移到左侧", target: self, selector: #selector(moveLeft)),
            UIAccessibilityCustomAction(name: "移到右侧", target: self, selector: #selector(moveRight)),
            UIAccessibilityCustomAction(name: "移到上方", target: self, selector: #selector(moveUp)),
            UIAccessibilityCustomAction(name: "移到下方", target: self, selector: #selector(moveDown))
        ]
        view.addSubview(button)
        keyboardObserver = NotificationCenter.default.addObserver(forName: UIResponder.keyboardWillChangeFrameNotification, object: nil, queue: .main) { [weak self] notification in
            guard let self, let frame = notification.userInfo?[UIResponder.keyboardFrameEndUserInfoKey] as? CGRect else { return }
            self.keyboardFrame = frame
            self.view.setNeedsLayout()
            let duration = notification.userInfo?[UIResponder.keyboardAnimationDurationUserInfoKey] as? Double ?? 0
            UIView.animate(withDuration: duration) { self.view.layoutIfNeeded() }
        }
    }

    deinit { if let keyboardObserver { NotificationCenter.default.removeObserver(keyboardObserver) } }

    private var availableCenters: CGRect {
        var area = view.safeAreaLayoutGuide.layoutFrame.insetBy(dx: 12, dy: 12)
        if let frame = keyboardFrame, let window = view.window {
            let keyboard = view.convert(window.convert(frame, from: nil), from: window)
            if keyboard.intersects(view.bounds) { area.size.height = max(0, min(area.maxY, keyboard.minY - 12) - area.minY) }
        }
        let half = button.bounds.width / 2
        return CGRect(x: area.minX + half, y: area.minY + half,
                      width: max(0, area.width - half * 2), height: max(0, area.height - half * 2))
    }

    override func viewDidLayoutSubviews() {
        super.viewDidLayoutSubviews()
        let area = availableCenters
        button.center = CGPoint(x: area.minX + area.width * position.x, y: area.minY + area.height * position.y)
    }

    @objc private func drag(_ gesture: UIPanGestureRecognizer) {
        if gesture.state == .began { dragOrigin = button.center }
        let area = availableCenters, translation = gesture.translation(in: view)
        let x = min(area.maxX, max(area.minX, dragOrigin.x + translation.x))
        let y = min(area.maxY, max(area.minY, dragOrigin.y + translation.y))
        position = CGPoint(x: area.width > 0 ? (x - area.minX) / area.width : 0,
                           y: area.height > 0 ? (y - area.minY) / area.height : 0)
        view.setNeedsLayout()
    }

    @objc private func moveLeft() -> Bool { position.x = 0; view.setNeedsLayout(); return true }
    @objc private func moveRight() -> Bool { position.x = 1; view.setNeedsLayout(); return true }
    @objc private func moveUp() -> Bool { position.y = 0; view.setNeedsLayout(); return true }
    @objc private func moveDown() -> Bool { position.y = 1; view.setNeedsLayout(); return true }
}

final class NativeDiagnosticsOverlay {
    var isOpen: Bool { root != nil }
    weak var scene: UIWindowScene?
    private weak var bridge: RCTBridge?
    private let window: DiagnosticsOverlayWindow
    private let controller = DiagnosticsOverlayController()
    private var root: RCTRootView?
    private var enabled = false
    private var background = MobileHostViewController.initialBackground
    private weak var coveredWindow: UIWindow?
    private var coveredAccessibilityHidden = false
    private var sceneObserver: NSObjectProtocol?
    private var windowObservers: [NSObjectProtocol] = []

    init(scene: UIWindowScene, bridge: RCTBridge) {
        self.scene = scene; self.bridge = bridge
        window = DiagnosticsOverlayWindow(windowScene: scene)
        window.frame = scene.coordinateSpace.bounds
        window.overrideUserInterfaceStyle = scene.windows.first(where: { $0.isKeyWindow })?.overrideUserInterfaceStyle ?? .unspecified
        window.windowLevel = UIWindow.Level(rawValue: UIWindow.Level.normal.rawValue + 1)
        window.backgroundColor = .clear
        window.rootViewController = controller
        window.diagnosticsController = controller
        window.accessibilityIdentifier = "ink-runtime-diagnostics-window"
        controller.loadViewIfNeeded()
        controller.button.addAction(UIAction { [weak self] _ in self?.open() }, for: .touchUpInside)
        sceneObserver = NotificationCenter.default.addObserver(forName: UIScene.didDisconnectNotification, object: scene, queue: .main) { [weak self] _ in self?.dispose() }
        for name in [UIWindow.didBecomeVisibleNotification, UIWindow.didBecomeHiddenNotification, UIWindow.didBecomeKeyNotification, UIWindow.didResignKeyNotification] {
            windowObservers.append(NotificationCenter.default.addObserver(forName: name, object: nil, queue: .main) { [weak self] notification in
                guard let self, let changed = notification.object as? UIWindow,
                      changed !== self.window, changed.windowScene === self.scene else { return }
                // RCTAlertController makes its window visible/key before presenting itself.
                DispatchQueue.main.async { [weak self] in self?.updateWindowLevel() }
            })
        }
    }

    deinit {
        if let sceneObserver { NotificationCenter.default.removeObserver(sceneObserver) }
        windowObservers.forEach { NotificationCenter.default.removeObserver($0) }
    }

    private func updateWindowLevel() {
        guard enabled, let scene else { return }
        let alertClass = NSClassFromString("RCTAlertController")
        let alertLevels = scene.windows.compactMap { candidate -> CGFloat? in
            guard candidate !== window, !candidate.isHidden, candidate.alpha > 0, let alertClass else { return nil }
            var presented = candidate.rootViewController
            while let current = presented {
                if current.isKind(of: alertClass) { return candidate.windowLevel.rawValue }
                presented = current.presentedViewController
            }
            return nil
        }
        // Only the installed RN alert class can raise this app-owned overlay.
        // Permission prompts and system authentication retain the system's ordering.
        let level = UIWindow.Level(rawValue: max(UIWindow.Level.normal.rawValue, alertLevels.max() ?? UIWindow.Level.normal.rawValue) + 1)
        if window.windowLevel != level {
            window.windowLevel = level
            UIAccessibility.post(notification: .layoutChanged, argument: nil)
        }
    }

    func configure(_ options: NSDictionary) {
        func color(_ key: String) -> UIColor? {
            guard let value = options[key] as? String, value.count == 7, value.hasPrefix("#"),
                  let rgb = UInt32(value.dropFirst(), radix: 16) else { return nil }
            return UIColor(red: CGFloat((rgb >> 16) & 255) / 255,
                           green: CGFloat((rgb >> 8) & 255) / 255, blue: CGFloat(rgb & 255) / 255, alpha: 1)
        }
        background = color("background") ?? background
        controller.button.backgroundColor = color("surface") ?? background
        controller.button.tintColor = color("foreground") ?? .label
        controller.button.layer.borderColor = (color("border") ?? .separator).cgColor
        if root != nil { controller.view.backgroundColor = background; root?.backgroundColor = background }
    }

    func setEnabled(_ value: Bool) {
        enabled = value
        if !value { close() }
        updateWindowLevel()
        window.isHidden = !value
    }

    private func open() {
        guard enabled, root == nil, let bridge, let scene, scene.activationState == .foregroundActive else { return }
        guard let original = scene.windows.first(where: { $0.isKeyWindow }) else { return }
        updateWindowLevel()
        original.endEditing(true)
        coveredWindow = original
        coveredAccessibilityHidden = original.accessibilityElementsHidden
        original.accessibilityElementsHidden = true
        let diagnostics = RCTRootView(bridge: bridge, moduleName: "InkRuntimeDiagnostics", initialProperties: nil)
        diagnostics.backgroundColor = background
        diagnostics.accessibilityIdentifier = "ink-runtime-diagnostics-content"
        diagnostics.translatesAutoresizingMaskIntoConstraints = false
        controller.expanded = true
        controller.view.backgroundColor = background
        controller.view.accessibilityViewIsModal = true
        controller.button.isHidden = true
        controller.view.addSubview(diagnostics)
        let safe = controller.view.safeAreaLayoutGuide
        NSLayoutConstraint.activate([
            diagnostics.leadingAnchor.constraint(equalTo: safe.leadingAnchor),
            diagnostics.trailingAnchor.constraint(equalTo: safe.trailingAnchor),
            diagnostics.topAnchor.constraint(equalTo: safe.topAnchor),
            diagnostics.bottomAnchor.constraint(equalTo: safe.bottomAnchor)
        ])
        root = diagnostics
        UIAccessibility.post(notification: .screenChanged, argument: nil)
    }

    func close() {
        let wasOpen = root != nil
        root?.removeFromSuperview(); root = nil
        coveredWindow?.accessibilityElementsHidden = coveredAccessibilityHidden
        coveredWindow = nil
        controller.expanded = false
        controller.view.backgroundColor = .clear
        controller.view.accessibilityViewIsModal = false
        controller.button.isHidden = false
        if wasOpen { UIAccessibility.post(notification: .screenChanged, argument: enabled ? controller.button : nil) }
    }

    func dispose() {
        setEnabled(false)
        if let sceneObserver { NotificationCenter.default.removeObserver(sceneObserver); self.sceneObserver = nil }
        windowObservers.forEach { NotificationCenter.default.removeObserver($0) }
        windowObservers.removeAll()
        window.rootViewController = nil
        scene = nil
    }
}

