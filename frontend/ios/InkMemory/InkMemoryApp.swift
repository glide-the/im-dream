// [Input] SwiftUI lifecycle, UIKit host and the existing page's background/theme projection.
// [Sync] 2026-10-29: observe the original ink-theme preference for matching native insets and explicit/system appearance.
// [Output] One iOS scene containing the bundled React Native composition root.
// [Pos] iOS application entry.
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
        let root = RCTRootView(bundleURL: bundle, moduleName: "InkMemory", initialProperties: nil, launchOptions: nil)
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

