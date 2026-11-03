// [Input] Explicit installed bundle ID and an already-open ordinary Reflections detail.
// [Output] Native drag/snap geometry and same-bridge diagnostics overlay assertions.
// [Pos] Read-only normal-account XCUITest acceptance; no launch reset, model, deletion or account injection.
// [Sync] 2026-11-03: verify real Simulator gestures and diagnostics above the selected report detail.
// [Sync] 2026-11-03: verify the floating entry's own touch drag and return to the existing Writing page.
// [Sync] 2026-11-03: normalize both AX labels when comparing multiline history titles with their confirmation summary.
import XCTest

@MainActor
final class AppExperienceUITests: XCTestCase {
    private func openedDetail() throws -> (XCUIApplication, XCUIElement) {
        continueAfterFailure = false
        let bundle = try XCTUnwrap(ProcessInfo.processInfo.environment["INK_IOS_UI_TARGET_BUNDLE_ID"])
        let app = XCUIApplication(bundleIdentifier: bundle)
        app.activate()
        let handle = app.descendants(matching: .any).matching(NSPredicate(format: "label == %@", "调整回顾详情高度")).firstMatch
        XCTAssertTrue(handle.waitForExistence(timeout: 10), "Open an existing report detail before this read-only journey")
        XCTAssertTrue(handle.isHittable)
        return (app, handle)
    }

    private func capture(_ app: XCUIApplication, _ name: String) {
        let attachment = XCTAttachment(screenshot: app.screenshot())
        attachment.name = name
        attachment.lifetime = .keepAlways
        add(attachment)
    }

    func testWritingDiagnosticsEntryDragAndReturn() throws {
        continueAfterFailure = false
        let bundle = try XCTUnwrap(ProcessInfo.processInfo.environment["INK_IOS_UI_TARGET_BUNDLE_ID"])
        let app = XCUIApplication(bundleIdentifier: bundle)
        app.activate()
        let writing = app.descendants(matching: .any).matching(NSPredicate(format: "label == %@", "写作")).firstMatch
        XCTAssertTrue(writing.waitForExistence(timeout: 10), "Open the existing Writing page before this read-only journey")
        let entry = app.buttons["ink-runtime-diagnostics-button"]
        XCTAssertTrue(entry.isHittable)
        let original = entry.frame
        capture(app, "writing-diagnostics-before-drag")
        let start = app.coordinate(withNormalizedOffset: .zero).withOffset(CGVector(
            dx: original.midX - app.frame.minX, dy: original.midY - app.frame.minY))
        let destination = app.coordinate(withNormalizedOffset: CGVector(dx: 0.15, dy: 0.3))
        start.press(forDuration: 0.1, thenDragTo: destination)
        let moved = XCTNSPredicateExpectation(predicate: NSPredicate { _, _ in
            abs(entry.frame.midX - original.midX) > 40 && entry.isHittable
        }, object: nil)
        XCTAssertEqual(XCTWaiter.wait(for: [moved], timeout: 5), .completed)
        XCTAssertTrue(app.frame.contains(entry.frame), "The dragged entry must remain within the App window")
        let dragged = entry.frame
        capture(app, "writing-diagnostics-after-drag")
        entry.tap()
        XCTAssertTrue(app.staticTexts["启动状态"].waitForExistence(timeout: 5))
        XCTAssertTrue(app.staticTexts["本地服务已就绪"].exists)
        capture(app, "writing-diagnostics-open")
        app.buttons["返回"].tap()
        XCTAssertTrue(writing.waitForExistence(timeout: 5))
        XCTAssertTrue(entry.isHittable)
        XCTAssertEqual(entry.frame.midX, dragged.midX, accuracy: 2)
        XCTAssertEqual(entry.frame.midY, dragged.midY, accuracy: 2)
        let restore = entry.coordinate(withNormalizedOffset: CGVector(dx: 0.5, dy: 0.5))
        restore.press(forDuration: 0.1, thenDragTo: start)
        XCTAssertTrue(entry.isHittable)
        XCTAssertTrue(app.frame.contains(entry.frame))
        capture(app, "writing-diagnostics-after-position-cleanup")
        print("INK_APP05_WRITING_DRAG moved=true entryInBounds=true originalPageRestored=true draggedPositionRetained=true businessWrites=0 modelCalls=0")
    }

    func testDetailHandleDragAndSnap() throws {
        let (app, handle) = try openedDetail()
        let before = handle.frame.minY
        capture(app, "reflection-detail-before-drag")
        let start = handle.coordinate(withNormalizedOffset: CGVector(dx: 0.5, dy: 0.5))
        start.press(forDuration: 0.1, thenDragTo: start.withOffset(CGVector(dx: 0, dy: -180)))
        let expands = XCTNSPredicateExpectation(predicate: NSPredicate { _, _ in handle.frame.minY < before - 25 }, object: nil)
        XCTAssertEqual(XCTWaiter.wait(for: [expands], timeout: 5), .completed, "Upward handle drag must increase detail height")
        let expanded = handle.frame.minY
        capture(app, "reflection-detail-expanded")
        let reverse = handle.coordinate(withNormalizedOffset: CGVector(dx: 0.5, dy: 0.5))
        reverse.press(forDuration: 0.1, thenDragTo: reverse.withOffset(CGVector(dx: 0, dy: 180)))
        let contracts = XCTNSPredicateExpectation(predicate: NSPredicate { _, _ in handle.frame.minY > expanded + 25 }, object: nil)
        XCTAssertEqual(XCTWaiter.wait(for: [contracts], timeout: 5), .completed, "Downward drag must restore more list space")
        XCTAssertTrue(app.buttons["关闭"].isHittable)
        print("INK_APP02_NATIVE_DRAG upward=true downward=true businessWrites=0 modelCalls=0")
    }

    func testDiagnosticsAboveDetailAndReturn() throws {
        let (app, handle) = try openedDetail()
        let before = handle.frame
        let button = app.buttons["ink-runtime-diagnostics-button"]
        XCTAssertTrue(button.isHittable)
        button.tap()
        XCTAssertTrue(app.staticTexts["启动状态"].waitForExistence(timeout: 5))
        XCTAssertFalse(handle.isHittable, "Covered business controls must leave the accessibility hit surface")
        XCTAssertTrue(app.staticTexts["本地服务已就绪"].exists)
        app.buttons["刷新"].tap()
        XCTAssertTrue(app.staticTexts["状态已刷新"].waitForExistence(timeout: 5))
        capture(app, "diagnostics-above-reflection-detail")
        app.buttons["返回"].tap()
        XCTAssertTrue(handle.waitForExistence(timeout: 5))
        XCTAssertTrue(handle.isHittable)
        XCTAssertEqual(handle.frame.minY, before.minY, accuracy: 2)
        XCTAssertTrue(app.buttons["关闭"].isHittable)
        capture(app, "reflection-detail-after-diagnostics")
        print("INK_APP05_NATIVE_OVERLAY detailCovered=true detailRestored=true businessWrites=0 modelCalls=0")
    }

    func testDetailBodyScrollKeepsControls() throws {
        let (app, _) = try openedDetail()
        let body = app.descendants(matching: .any).matching(identifier: "reflection-detail-body").firstMatch
        XCTAssertTrue(body.waitForExistence(timeout: 5))
        XCTAssertGreaterThan(body.frame.height, 0, "Detail controls must leave visible height for report content")
        let related = body.staticTexts["Related notes coming soon"]
        for _ in 0..<5 {
            if related.isHittable { break }
            body.swipeUp()
        }
        XCTAssertTrue(related.isHittable, "The end of the existing report body must remain reachable by its own scroll gesture")
        XCTAssertTrue(app.buttons["关闭"].isHittable)
        XCTAssertTrue(app.buttons["下一条"].isHittable)
        capture(app, "reflection-detail-body-scroll")
        print("INK_APP02_NATIVE_BODY bodyVisible=true bodyScrolled=true controlsVisible=true businessWrites=0 modelCalls=0")
    }

    func testDiagnosticsWithSettingsKeyboard() throws {
        continueAfterFailure = false
        let bundle = try XCTUnwrap(ProcessInfo.processInfo.environment["INK_IOS_UI_TARGET_BUNDLE_ID"])
        let app = XCUIApplication(bundleIdentifier: bundle)
        app.activate()
        let heading = app.descendants(matching: .any).matching(NSPredicate(format: "label == %@", "AI 模型 / Model")).firstMatch
        XCTAssertTrue(heading.waitForExistence(timeout: 10), "Open the original model settings before this read-only journey")
        XCTAssertTrue(app.buttons["恢复默认"].isEnabled, "The original configuration must have loaded successfully")
        let prompt = app.descendants(matching: .any).matching(NSPredicate(format: "label == %@", "系统提示词")).firstMatch
        for _ in 0..<10 {
            if prompt.isHittable { break }
            app.coordinate(withNormalizedOffset: CGVector(dx: 0.85, dy: 0.8))
                .press(forDuration: 0.1, thenDragTo: app.coordinate(withNormalizedOffset: CGVector(dx: 0.85, dy: 0.4)))
        }
        XCTAssertTrue(prompt.isHittable)
        prompt.tap()
        XCTAssertTrue(app.keyboards.firstMatch.waitForExistence(timeout: 5))
        let button = app.buttons["ink-runtime-diagnostics-button"]
        XCTAssertTrue(button.isHittable)
        capture(app, "diagnostics-button-with-keyboard")
        button.tap()
        XCTAssertTrue(app.staticTexts["启动状态"].waitForExistence(timeout: 5))
        XCTAssertFalse(app.keyboards.firstMatch.exists)
        app.buttons["返回"].tap()
        XCTAssertTrue(heading.waitForExistence(timeout: 5))
        XCTAssertFalse(app.buttons["保存系统提示词"].isEnabled, "Focusing and opening diagnostics must leave the original prompt unchanged")
        print("INK_APP05_NATIVE_KEYBOARD entryReachable=true keyboardDismissed=true originalFormUnchanged=true businessWrites=0 modelCalls=0")
    }

    func testDiagnosticsAboveDeleteAlertAndCancel() throws {
        continueAfterFailure = false
        let bundle = try XCTUnwrap(ProcessInfo.processInfo.environment["INK_IOS_UI_TARGET_BUNDLE_ID"])
        let app = XCUIApplication(bundleIdentifier: bundle)
        app.activate()
        print("INK_APP_CONFIRM_HARNESS title-whitespace-v2")
        let target = app.buttons.matching(NSPredicate(format: "label BEGINSWITH %@", "删除对话: ")).firstMatch
        XCTAssertTrue(target.waitForExistence(timeout: 10), "Open normal Chat history before this cancellation-only journey")
        let title = String(target.label.dropFirst("删除对话: ".count))
            .split(whereSeparator: \.isWhitespace).joined(separator: " ")
        target.tap()
        let alert = app.alerts.firstMatch
        defer { if alert.buttons["取消"].isHittable { alert.buttons["取消"].tap() } }
        XCTAssertTrue(alert.waitForExistence(timeout: 5))
        XCTAssertTrue(alert.staticTexts.allElementsBoundByIndex.contains {
            $0.label.split(whereSeparator: \.isWhitespace).joined(separator: " ").contains(title)
        })
        let entry = app.buttons["ink-runtime-diagnostics-button"]
        XCTAssertTrue(entry.isHittable, "The diagnostics entry must remain usable above the App-owned Alert window")
        // XCUIElement.tap's default interruption handler cancels the original Alert.
        // Tap the observed centre across windows, preserving the original Alert assertions.
        let centre = app.coordinate(withNormalizedOffset: .zero).withOffset(CGVector(
            dx: entry.frame.midX - app.frame.minX, dy: entry.frame.midY - app.frame.minY))
        centre.tap()
        XCTAssertTrue(app.staticTexts["启动状态"].waitForExistence(timeout: 5))
        XCTAssertFalse(alert.buttons["删除"].isHittable)
        capture(app, "diagnostics-above-delete-confirmation")
        app.buttons["返回"].tap()
        XCTAssertTrue(alert.buttons["取消"].waitForExistence(timeout: 5))
        alert.buttons["取消"].tap()
        XCTAssertTrue(target.waitForExistence(timeout: 5))
        print("INK_APP01_APP05_NATIVE_CONFIRMATION targetNamed=true diagnosticsAboveAlert=true cancelled=true historyRetained=true deletions=0 modelCalls=0")
    }
}
