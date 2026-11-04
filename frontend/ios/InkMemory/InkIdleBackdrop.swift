// [Input] An idle overlay's native view and the existing system appearance.
// [Output] A local material blur over the retained business view.
// [Pos] Narrow RN presentation adapter; no screenshot, task or lifecycle side effects.
import React
import UIKit

@objc(InkIdleBackdrop)
final class InkIdleBackdropManager: RCTViewManager {
    override static func requiresMainQueueSetup() -> Bool { true }
    override func view() -> UIView! {
        let view = UIVisualEffectView(effect: UIBlurEffect(style: .systemMaterial))
        view.isUserInteractionEnabled = false
        return view
    }
}
