// [Input] Explicit ordinary Simulator bundle, existing authenticated account and original pages.
// [Output] Idle overlay, retained draft, unified graphics and an explicit bounded ordinary-account task cycle.
// [Pos] XCUITest uses visible production UI; no reset, account injection or historical deletion. Real model method is selected explicitly.
import XCTest

@MainActor
final class IdleScreenSaverUITests: XCTestCase {
    private func target() throws -> XCUIApplication {
        continueAfterFailure = false
        let bundle = try XCTUnwrap(ProcessInfo.processInfo.environment["INK_IOS_UI_TARGET_BUNDLE_ID"])
        let app = XCUIApplication(bundleIdentifier: bundle)
        app.activate()
        let saver = app.buttons["idle-screen-saver-close"]
        let navigation = app.descendants(matching: .any)["main-tab-more"]
        let ready = XCTNSPredicateExpectation(predicate: NSPredicate { _, _ in navigation.exists || saver.exists }, object: nil)
        XCTAssertEqual(XCTWaiter.wait(for: [ready], timeout: 90), .completed)
        if saver.exists { saver.tap() }
        let warning = app.descendants(matching: .any).matching(NSPredicate(format: "label CONTAINS %@", "Open debugger to view warnings.")).firstMatch
        if warning.exists { warning.coordinate(withNormalizedOffset: CGVector(dx: 0.96, dy: 0.5)).tap() }
        XCTAssertTrue(navigation.waitForExistence(timeout: 10))
        return app
    }
    private func shot(_ app: XCUIApplication, _ name: String) {
        let item = XCTAttachment(screenshot: app.screenshot())
        item.name = name; item.lifetime = .keepAlways; add(item)
    }
    private func pause(_ seconds: TimeInterval) { RunLoop.current.run(until: Date(timeIntervalSinceNow: seconds)) }
    private func tab(_ app: XCUIApplication, _ name: String) -> XCUIElement {
        app.descendants(matching: .any)["main-tab-" + name].firstMatch
    }

    func testIdleDismissalRetainsPageAndDoesNotTapThrough() throws {
        let app = try target()
        tab(app, "more").tap()
        let saver = app.buttons["idle-screen-saver-close"]
        pause(18)
        XCTAssertFalse(saver.exists, "The 25-second idle interval must elapse")
        XCTAssertTrue(saver.waitForExistence(timeout: 14))
        let value = saver.value as? String ?? ""
        XCTAssertTrue(value.contains("活跃 Thread"), "The ordinary authenticated Factory observation must be known")
        XCTAssertTrue(value.contains("无") || value.contains("有"))
        shot(app, "idle-more-shared-presence")
        // This coordinate is the underlying Chat tab. Closing must consume the touch.
        app.coordinate(withNormalizedOffset: CGVector(dx: 0.17, dy: 0.94)).tap()
        XCTAssertFalse(saver.exists)
        XCTAssertTrue(tab(app, "more").isSelected)
        XCTAssertFalse(tab(app, "chat").isSelected)
        shot(app, "idle-dismiss-retained-more")
        // Genuine touch resets the deadline, including navigation.
        pause(15)
        tab(app, "chat").tap()
        pause(15)
        XCTAssertFalse(saver.exists)
        XCTAssertTrue(saver.waitForExistence(timeout: 16))
        shot(app, "idle-chat-after-reset")
        saver.tap()
        XCUIDevice.shared.press(.home)
        pause(2)
        app.activate()
        pause(16)
        XCTAssertFalse(saver.exists, "Foreground return starts a fresh idle interval")
        XCTAssertTrue(saver.waitForExistence(timeout: 16))
        shot(app, "idle-after-foreground")
        saver.tap()
    }

    func testKeyboardAndUnsentDraftRemain() throws {
        let app = try target()
        tab(app, "chat").tap()
        let editor = app.webViews.textViews.firstMatch
        XCTAssertTrue(editor.waitForExistence(timeout: 30))
        if !editor.isEnabled {
            let retry = app.buttons["重试读取"]
            if retry.exists && retry.isEnabled { retry.tap() }
            let ready = XCTNSPredicateExpectation(predicate: NSPredicate { _, _ in editor.isEnabled }, object: nil)
            guard XCTWaiter.wait(for: [ready], timeout: 30) == .completed else {
                throw XCTSkip("Normal account configuration is unavailable; the original editor remains read-only")
            }
        }
        let before = editor.value as? String ?? ""
        let marker = " idle-preservation-check"
        let hasDraft = !before.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty && !before.contains("Ask ")
        editor.tap()
        if !hasDraft { editor.typeText(marker) }
        let expected = editor.value as? String ?? ""
        if !hasDraft { XCTAssertTrue(expected.contains(marker.trimmingCharacters(in: .whitespaces))) }
        pause(28)
        XCTAssertFalse(app.buttons["idle-screen-saver-close"].exists, "An editing owner blocks the idle overlay")
        XCTAssertEqual(editor.value as? String ?? "", expected)
        shot(app, "idle-keyboard-keeps-draft")
        tab(app, "more").tap()
        XCTAssertTrue(app.buttons["idle-screen-saver-close"].waitForExistence(timeout: 35))
        shot(app, "idle-after-keyboard-release")
        app.buttons["idle-screen-saver-close"].tap()
        tab(app, "chat").tap()
        XCTAssertEqual(editor.value as? String ?? "", expected, "The retained input instance keeps its unsent draft through navigation and idle overlay")
        if !hasDraft {
            editor.tap()
            // An empty contenteditable exposes a paragraph newline through AX.
            // Delete the test text; typing that newline would invoke the original Enter action.
            editor.typeKey("a", modifierFlags: .command)
            editor.typeText(XCUIKeyboardKey.delete.rawValue)
            XCTAssertTrue((editor.value as? String ?? "").trimmingCharacters(in: .whitespacesAndNewlines).isEmpty)
        } else { XCTAssertEqual(editor.value as? String ?? "", before) }
        tab(app, "more").tap()
    }
    func testUnifiedClockNativeFrames() throws {
        let app = try target()
        tab(app, "more").tap()
        XCTAssertTrue(app.buttons["idle-screen-saver-close"].waitForExistence(timeout: 35))
        func at(_ fraction: Double, _ name: String) {
            let now = Date().timeIntervalSince1970
            var next = floor(now) + fraction
            if next <= now { next += 1 }
            pause(next - now)
            shot(app, name)
        }
        at(0.80, "unified-clock-hair-base-a")
        at(0.25, "unified-clock-hair-moving")
        at(0.80, "unified-clock-hair-base-b")
        app.buttons["idle-screen-saver-close"].tap()
    }

    func testPresenceDuringOneRealTask() throws {
        let app = try target()
        tab(app, "chat").tap()
        let editor = app.webViews.textViews.firstMatch
        XCTAssertTrue(editor.waitForExistence(timeout: 30))
        guard editor.isEnabled else { throw XCTSkip("Ordinary model configuration must be ready before a real turn") }
        let prior = (editor.value as? String ?? "").trimmingCharacters(in: .whitespacesAndNewlines)
        guard prior.isEmpty else { throw XCTSkip("Preserve the existing unsent draft") }
        // One ordinary user turn using the model confirmed in Settings; no replay or retry.
        editor.tap()
        editor.typeText("Run exactly one Bash command: sleep 75; printf IDLE_PRESENCE_OK. Do not read or write files. After it completes, reply only IDLE_PRESENCE_OK.")
        let send = app.buttons["发送消息"]
        XCTAssertTrue(send.isEnabled); send.tap()
        let stop = app.buttons["停止生成"]
        XCTAssertTrue(stop.waitForExistence(timeout: 30))
        tab(app, "more").tap()
        let saver = app.buttons["idle-screen-saver-close"]
        XCTAssertTrue(saver.waitForExistence(timeout: 35))
        XCTAssertTrue((saver.value as? String ?? "").contains("活跃 Thread：有"))
        shot(app, "presence-real-task-saver-active")
        saver.tap()
        XCUIDevice.shared.press(.home)
        pause(3)
        let springboard = XCUIApplication(bundleIdentifier: "com.apple.springboard")
        shot(springboard, "presence-real-task-system-active")
        app.activate()
        let original = XCTNSPredicateExpectation(predicate: NSPredicate { _, _ in self.tab(app,"more").exists || saver.exists }, object: nil)
        XCTAssertEqual(XCTWaiter.wait(for:[original],timeout:30),.completed)
        if saver.exists { saver.tap() }
        tab(app, "chat").tap()
        let reply = app.staticTexts.matching(NSPredicate(format:"label == %@", "IDLE_PRESENCE_OK")).firstMatch
        // The idle overlay hides the underlying accessibility tree. Consume its
        // closing touch while awaiting completion; retain the same single turn.
        let completed = XCTNSPredicateExpectation(predicate: NSPredicate { _, _ in
            if saver.exists { saver.tap() }
            return reply.exists && !stop.exists
        }, object: nil)
        XCTAssertEqual(XCTWaiter.wait(for: [completed], timeout: 180), .completed,
                       "Wait for the ordinary turn's final state after its text arrives")
        shot(app, "presence-real-task-completed")
        tab(app, "more").tap()
        XCTAssertTrue(saver.waitForExistence(timeout: 35))
        XCTAssertTrue((saver.value as? String ?? "").contains("活跃 Thread：无"))
        shot(app, "presence-real-task-saver-idle")
        saver.tap()
    }

    func testReadCompletedPresenceTask() throws {
        let app = try target()
        tab(app,"chat").tap()
        let reply = app.staticTexts.matching(NSPredicate(format:"label == %@", "IDLE_PRESENCE_OK")).firstMatch
        XCTAssertTrue(reply.waitForExistence(timeout:30))
        let stop = app.buttons["停止生成"]
        let finished = XCTNSPredicateExpectation(predicate: NSPredicate { _,_ in !stop.exists }, object:nil)
        XCTAssertEqual(XCTWaiter.wait(for:[finished],timeout:30),.completed)
        shot(app,"presence-same-task-final-read")
        tab(app,"more").tap()
        let saver = app.buttons["idle-screen-saver-close"]
        XCTAssertTrue(saver.waitForExistence(timeout:35))
        XCTAssertTrue((saver.value as? String ?? "").contains("活跃 Thread：无"))
        shot(app,"presence-same-task-idle-final-read")
        saver.tap()
    }

    func testYReadCurrentConfiguredModel() throws {
        let app = try target()
        tab(app, "more").tap()
        let settings = app.buttons["设置"]
        XCTAssertTrue(settings.waitForExistence(timeout: 10)); settings.tap()
        let model = app.buttons["AI 模型"]
        XCTAssertTrue(model.waitForExistence(timeout: 10)); model.tap()
        // RN radio has no UIKit button trait; actual device AX exposes checked/unchecked.
        let radios = app.descendants(matching: .any).matching(NSPredicate(format: "value == %@ OR value == %@", "checked", "unchecked"))
        for _ in 0..<4 {
            if radios.firstMatch.waitForExistence(timeout: 10) { break }
            if app.buttons["idle-screen-saver-close"].exists { app.buttons["idle-screen-saver-close"].tap() }
        }
        let chosen = radios.allElementsBoundByIndex.first { element in
            let value = element.value as? String ?? ""
            return (value == "checked" || value.contains("已选中")) && element.label.range(of:"image|图像|图片",options:[.regularExpression,.caseInsensitive]) == nil && element.isEnabled
        }
        guard let chosen else { throw XCTSkip("A callable saved model could not be confirmed through normal settings") }
        let item = XCTAttachment(screenshot: chosen.screenshot())
        item.name = "presence-current-model-read-only"; item.lifetime = .keepAlways; add(item)
        print("IDLE_CONFIGURED_MODEL " + chosen.label)
        tab(app, "more").tap()
    }

    func testZCleanupOnlyOwnedMarker() throws {
        let app = try target()
        tab(app, "chat").tap()
        let editor = app.webViews.textViews.firstMatch
        XCTAssertTrue(editor.waitForExistence(timeout: 30))
        let value = (editor.value as? String ?? "").trimmingCharacters(in: .whitespacesAndNewlines)
        if value == "idle-preservation-check" {
            let newChat = app.buttons.matching(NSPredicate(format: "label == %@ OR label == %@", "新建对话", "New chat")).firstMatch
            XCTAssertTrue(newChat.isHittable)
            newChat.tap()
            XCTAssertTrue(editor.waitForExistence(timeout: 20))
            XCTAssertTrue((editor.value as? String ?? "").trimmingCharacters(in: .whitespacesAndNewlines).isEmpty)
        }
        tab(app, "more").tap()
        shot(app, "idle-test-cleanup-preserves-more")
    }

}
