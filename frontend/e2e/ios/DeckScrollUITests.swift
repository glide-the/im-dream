// [Input] Explicit installed application bundle ID and the existing normal Deck preview.
// [Output] Actual native drag, information visibility and navigation geometry evidence.
// [Pos] Read-only XCTest UI acceptance; no login, message, model, file or business mutation.
// [Sync] 2026-10-29: verify the installed native maintenance form and version/plugin navigation without edits.
// [Sync] 2026-10-29: observe original model settings, prompt focus and return without selecting or saving configuration.
// Impact: Project/Episode/artifact/Hook/DB are out of scope; existing Thread/data remain unchanged.
import XCTest

@MainActor
final class DeckScrollUITests: XCTestCase {
    func testModelSettingsReadOnlyNavigation() throws {
        continueAfterFailure = false
        let bundleID = try XCTUnwrap(ProcessInfo.processInfo.environment["INK_IOS_UI_TARGET_BUNDLE_ID"])
        let app = XCUIApplication(bundleIdentifier: bundleID)
        app.activate()
        XCTAssertTrue(app.wait(for: .runningForeground, timeout: 10))
        let heading = app.descendants(matching: .any).matching(NSPredicate(format: "label == %@", "AI 模型 / Model")).firstMatch
        XCTAssertTrue(heading.waitForExistence(timeout: 15), "Open the original model settings before this read-only test")
        let back = app.buttons.matching(NSPredicate(format: "label IN %@", ["Back to app", "返回应用"])).firstMatch
        XCTAssertTrue(back.isHittable)
        let prompt = app.descendants(matching: .any).matching(NSPredicate(format: "label == %@", "系统提示词")).firstMatch
        let start = app.coordinate(withNormalizedOffset: CGVector(dx: 0.9, dy: 0.78))
        let end = app.coordinate(withNormalizedOffset: CGVector(dx: 0.9, dy: 0.35))
        for _ in 0..<10 {
            if prompt.isHittable { break }
            start.press(forDuration: 0.1, thenDragTo: end)
        }
        XCTAssertTrue(prompt.isHittable, "The original prompt must be reachable by scrolling")
        prompt.tap()
        XCTAssertTrue(prompt.isHittable)
        XCTAssertTrue(back.isHittable)
        let image = XCTAttachment(screenshot: app.screenshot())
        image.name = "native-model-settings-readonly-prompt"
        image.lifetime = .keepAlways
        add(image)
        back.tap()
        let model = app.buttons.matching(NSPredicate(format: "label IN %@", ["AI models", "AI 模型"])).firstMatch
        XCTAssertTrue(model.waitForExistence(timeout: 10))
        model.tap()
        XCTAssertTrue(prompt.waitForExistence(timeout: 10))
        XCTAssertTrue(back.isHittable)
        print("INK_NATIVE_MODEL_SETTINGS_PROOF modelRead=true promptVisible=true promptTappedWithoutTyping=true backAndReopen=true messageSubmissions=0 modelCalls=0 businessMutations=0")
    }

    func testMaintenanceFormReadOnlyNavigation() throws {
        continueAfterFailure = false
        let bundleID = try XCTUnwrap(ProcessInfo.processInfo.environment["INK_IOS_UI_TARGET_BUNDLE_ID"])
        let app = XCUIApplication(bundleIdentifier: bundleID)
        app.activate()
        XCTAssertTrue(app.wait(for: .runningForeground, timeout: 10))
        let name = app.textFields["Deck name"]
        XCTAssertTrue(name.waitForExistence(timeout: 10), "Open an existing Deck maintenance form before this read-only test")
        XCTAssertTrue(name.isHittable)
        XCTAssertFalse((name.value as? String ?? "").isEmpty)
        let history = app.buttons["版本记录"]
        XCTAssertTrue(history.isHittable)
        history.tap()
        let collapse = app.buttons["收起版本记录"]
        XCTAssertTrue(collapse.waitForExistence(timeout: 10))
        let image = XCTAttachment(screenshot: app.screenshot())
        image.name = "native-deck-content-history"
        image.lifetime = .keepAlways
        add(image)
        collapse.tap()
        XCTAssertTrue(name.waitForExistence(timeout: 10))
        let plugins = app.descendants(matching: .any).matching(NSPredicate(format: "label == %@", "Claude 插件")).firstMatch
        XCTAssertTrue(plugins.isHittable)
        plugins.tap()
        XCTAssertTrue(app.staticTexts["Installed plugins"].waitForExistence(timeout: 10))
        let pluginImage = XCTAttachment(screenshot: app.screenshot())
        pluginImage.name = "native-deck-plugin-read"
        pluginImage.lifetime = .keepAlways
        add(pluginImage)
        let overview = app.descendants(matching: .any).matching(NSPredicate(format: "label == %@", "概览")).firstMatch
        XCTAssertTrue(overview.isHittable)
        overview.tap()
        XCTAssertTrue(name.waitForExistence(timeout: 10))
        XCTAssertTrue(app.buttons["Close"].isHittable)
        print("INK_NATIVE_DECK_MAINTENANCE_PROOF nameVisible=true historyOpened=true pluginsOpened=true overviewRestored=true messageSubmissions=0 modelCalls=0 businessMutations=0")
    }

    func testPreviewScrollKeepsNavigationVisible() throws {
        continueAfterFailure = false
        let bundleID = try XCTUnwrap(ProcessInfo.processInfo.environment["INK_IOS_UI_TARGET_BUNDLE_ID"])
        XCTAssertFalse(bundleID.isEmpty)
        let app = XCUIApplication(bundleIdentifier: bundleID)
        app.activate()
        XCTAssertTrue(app.wait(for: .runningForeground, timeout: 10))
        let tryNow = app.buttons["Try now"]
        XCTAssertTrue(tryNow.waitForExistence(timeout: 10), "Open the existing English Deck preview before this read-only test")
        let information = app.staticTexts["Information"]
        let updated = app.staticTexts["Updated"]
        XCTAssertTrue(information.exists)
        XCTAssertTrue(updated.exists)
        let before = information.frame
        let beforeImage = XCTAttachment(screenshot: app.screenshot())
        beforeImage.name = "deck-before-native-drag"
        beforeImage.lifetime = .keepAlways
        add(beforeImage)

        let start = app.coordinate(withNormalizedOffset: CGVector(dx: 0.8, dy: 0.78))
        let end = app.coordinate(withNormalizedOffset: CGVector(dx: 0.8, dy: 0.3))
        start.press(forDuration: 0.1, thenDragTo: end)
        let moved = XCTNSPredicateExpectation(predicate: NSPredicate { _, _ in
            information.frame.minY < before.minY - 20 && updated.isHittable
        }, object: nil)
        let result = XCTWaiter.wait(for: [moved], timeout: 8)
        let afterImage = XCTAttachment(screenshot: app.screenshot())
        afterImage.name = "deck-after-native-drag"
        afterImage.lifetime = .keepAlways
        add(afterImage)
        let nav = app.descendants(matching: .any).matching(NSPredicate(format: "label == %@", "Decks")).firstMatch
        let facts: [String: Any] = [
            "appWidth": app.frame.width, "appHeight": app.frame.height,
            "informationBeforeY": before.minY, "informationAfterY": information.frame.minY,
            "updatedVisible": updated.isHittable, "deckNavigationVisible": nav.isHittable,
            "messageSubmissions": 0, "modelCalls": 0, "businessMutations": 0,
        ]
        let payload = try JSONSerialization.data(withJSONObject: facts, options: [.sortedKeys])
        let proof = XCTAttachment(data: payload, uniformTypeIdentifier: "public.json")
        proof.name = "native-deck-scroll-proof"
        proof.lifetime = .keepAlways
        add(proof)
        print("INK_NATIVE_DECK_SCROLL_PROOF \(String(decoding: payload, as: UTF8.self))")
        XCTAssertEqual(result, .completed, "The original information rows must become visible after a native drag")
        XCTAssertTrue(nav.isHittable, "Bottom Deck navigation must stay visible")
        end.press(forDuration: 0.1, thenDragTo: start)
    }
}
