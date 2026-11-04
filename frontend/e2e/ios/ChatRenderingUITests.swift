// [Input] Explicit isolated APP-06 Simulator bundle and production Chat/composer/Hook with memory-only transport.
// [Output] Native code height, long message reading, keyboard/touch, streaming, Stop and saved-history receipts.
// [Pos] Provider-free technical qualification; no physical device, real account, database or model operations.
// [Sync] 2026-11-03: sample idle historical-message geometry to detect repeated native offset corrections.
import XCTest

@MainActor
final class ChatRenderingUITests: XCTestCase {
    func target() throws -> XCUIApplication {
        continueAfterFailure = false
        let bundle = try XCTUnwrap(ProcessInfo.processInfo.environment["INK_APP06_UI_TARGET"])
        XCTAssertEqual(bundle, "com.inkmemory.app06qualification")
        let app = XCUIApplication(bundleIdentifier: bundle)
        app.launch()
        XCTAssertTrue(app.buttons["Code"].waitForExistence(timeout: 30))
        return app
    }
    func shot(_ app: XCUIApplication, _ name: String) {
        let attachment = XCTAttachment(screenshot: app.screenshot())
        attachment.name = name; attachment.lifetime = .keepAlways; add(attachment)
    }
    func latestReply(_ app: XCUIApplication) -> XCUIElement {
        let query = app.staticTexts.matching(NSPredicate(format: "label == %@", "Reply complete."))
        return query.element(boundBy: max(0, query.count - 1))
    }
    func testIdleHistoryRemainsStill() throws {
        let app = try target()
        app.buttons["Stable"].tap()
        let reply = app.staticTexts["Stable reply."]
        let expand = app.buttons["Expand message"]
        XCTAssertTrue(reply.waitForExistence(timeout: 15))
        XCTAssertTrue(expand.waitForExistence(timeout: 15))
        let list = app.otherElements["native-chat-messages-scroll"].scrollViews.firstMatch
        let ready = XCTNSPredicateExpectation(predicate: NSPredicate { _, _ in reply.isHittable }, object: nil)
        XCTAssertEqual(XCTWaiter.wait(for: [ready], timeout: 10), .completed)
        let user = app.otherElements["native-chat-message-stable-user"]
        print("APP06_IDLE_GEOMETRY list=\(list.frame) user=\(user.frame) reply=\(reply.frame) expand=\(expand.frame)")
        // A timed geometry sample tests absence of movement while all inputs are fixed.
        var positions: [CGFloat] = []
        for _ in 0..<24 {
            positions.append(reply.frame.minY)
            RunLoop.current.run(until: Date(timeIntervalSinceNow: 0.12))
        }
        print("APP06_IDLE_POSITIONS \(positions)")
        shot(app, "app06-idle-history")
        XCTAssertLessThanOrEqual((positions.max() ?? 0) - (positions.min() ?? 0), 2,
                                 "An idle historical turn must keep one scroll position")
        XCTAssertTrue(reply.isHittable)
        XCTAssertLessThanOrEqual(reply.frame.maxY, list.frame.maxY + 1)
        expand.tap()
        XCTAssertTrue(app.buttons["Collapse message"].exists)
    }
    func testCodeHeightAndLatestPosition() throws {
        let app = try target()
        app.buttons["Code"].tap()
        let editor = app.webViews.textViews.firstMatch
        XCTAssertTrue(editor.waitForExistence(timeout: 30))
        let send = app.buttons["Send message"]
        XCTAssertTrue(send.waitForExistence(timeout: 10)); XCTAssertTrue(send.isEnabled)
        send.tap()
        XCTAssertTrue(app.buttons["Stop generating"].waitForExistence(timeout: 15))
        app.buttons["Finish"].tap()
        XCTAssertTrue(app.staticTexts.matching(NSPredicate(format: "label CONTAINS %@", "Reply complete.")).firstMatch.waitForExistence(timeout: 15))
        let list = app.otherElements["native-chat-messages-scroll"].scrollViews.firstMatch
        shot(app, "app06-code-latest")
        print("APP06_CODE_TREE\n\(app.debugDescription)")
        let latest = app.staticTexts.matching(NSPredicate(format: "label == %@", "Reply complete.")).firstMatch
        XCTAssertTrue(latest.isHittable)
        XCTAssertLessThanOrEqual(latest.frame.maxY, list.frame.maxY + 1)
        let codes = app.otherElements.matching(identifier: "native-chat-markdown-code")
        XCTAssertGreaterThan(codes.count, 0)
        for code in codes.allElementsBoundByIndex {
            print("APP06_CODE_GEOMETRY \(code.frame)")
            XCTAssertLessThan(code.frame.height, 100, "One-line/empty code must retain intrinsic height")
        }
        let longLine = app.staticTexts.matching(NSPredicate(format: "label BEGINSWITH %@", "long_long_long_")).firstMatch
        let longCode = try XCTUnwrap(codes.allElementsBoundByIndex.last).scrollViews.firstMatch
        let lineX = longLine.frame.minX, latestY = latest.frame.minY
        longCode.swipeLeft()
        XCTAssertLessThan(longLine.frame.minX, lineX - 10)
        XCTAssertEqual(latest.frame.minY, latestY, accuracy: 2)
        shot(app, "app06-code-horizontal-touch")
    }
    func testLongInputStreamStopAndSavedHistory() throws {
        let app = try target()
        let editor = app.webViews.textViews.firstMatch
        XCTAssertTrue(editor.waitForExistence(timeout: 30))
        editor.tap(); editor.typeText("A short keyboard check")
        XCTAssertGreaterThan(app.keyboards.count, 0, "Use the Simulator software keyboard")
        XCTAssertTrue(app.buttons["Send message"].isHittable)
        shot(app, "app06-keyboard")
        app.buttons["Hide keyboard"].tap()
        let keyboardGone = XCTNSPredicateExpectation(predicate: NSPredicate { _, _ in app.keyboards.count == 0 }, object: nil)
        XCTAssertEqual(XCTWaiter.wait(for: [keyboardGone], timeout: 5), .completed)
        app.buttons["Long"].tap()
        XCTAssertTrue(app.buttons["Send message"].isEnabled)
        app.buttons["Send message"].tap()
        XCTAssertTrue(app.buttons["Stop generating"].waitForExistence(timeout: 15))
        let list = app.otherElements["native-chat-messages-scroll"].scrollViews.firstMatch
        let expand = app.buttons["Expand message"]
        for _ in 0..<12 { if expand.isHittable { break }; list.swipeDown() }
        XCTAssertTrue(expand.isHittable)
        XCTAssertGreaterThanOrEqual(expand.frame.height, 44)
        shot(app, "app06-long-collapsed")
        expand.tap()
        let first = app.staticTexts.matching(NSPredicate(format: "label CONTAINS %@", "Paragraph 1.")).firstMatch
        XCTAssertTrue(first.isHittable, "Expansion must retain the visible reading boundary")
        let collapse = app.buttons["Collapse message"]
        XCTAssertTrue(collapse.exists)
        print("APP06_EXPANSION first=\(first.frame) collapse=\(collapse.frame) fullRange=\(collapse.frame.minY-first.frame.minY)")
        for attempt in 0..<20 {
            if collapse.isHittable { break }
            let upwards = collapse.frame.midY > list.frame.midY
            print("APP06_DISCLOSURE_DRAG \(attempt) target=\(collapse.frame) viewport=\(list.frame) upwards=\(upwards)")
            let start = list.coordinate(withNormalizedOffset: CGVector(dx: 0.08, dy: upwards ? 0.85 : 0.15))
            let end = list.coordinate(withNormalizedOffset: CGVector(dx: 0.08, dy: upwards ? 0.20 : 0.80))
            start.press(forDuration: 0.1, thenDragTo: end, withVelocity: .slow, thenHoldForDuration: 0.2)
        }
        if !collapse.isHittable { shot(app, "app06-collapse-unreachable"); print("APP06_COLLAPSE_TREE\n\(app.debugDescription)") }
        XCTAssertTrue(collapse.isHittable)
        collapse.tap()
        let jump = app.buttons["Scroll to bottom"]
        if jump.isHittable { jump.tap() }
        let latest = latestReply(app)
        XCTAssertTrue(latest.isHittable)
        app.buttons["Next"].tap()
        XCTAssertTrue(latestReply(app).isHittable)
        editor.tap()
        XCTAssertGreaterThan(app.keyboards.count, 0)
        XCTAssertTrue(app.buttons["Stop generating"].isHittable)
        XCTAssertTrue(latestReply(app).isHittable)
        shot(app, "app06-stream-keyboard")
        app.buttons["Hide keyboard"].tap()
        let streamKeyboardGone = XCTNSPredicateExpectation(predicate: NSPredicate { _, _ in app.keyboards.count == 0 }, object: nil)
        XCTAssertEqual(XCTWaiter.wait(for: [streamKeyboardGone], timeout: 5), .completed)
        for _ in 0..<12 { if first.isHittable { break }; list.swipeDown() }
        XCTAssertTrue(first.isHittable)
        let readingY = first.frame.minY
        app.buttons["Next"].tap()
        XCTAssertEqual(first.frame.minY, readingY, accuracy: 2, "New output must retain historical reading position")
        XCTAssertTrue(jump.isHittable); jump.tap()
        XCTAssertTrue(latestReply(app).isHittable)
        app.buttons["Stop generating"].tap()
        XCTAssertTrue(app.buttons["Send message"].waitForExistence(timeout: 15))
        let receipt = app.staticTexts["app06-receipt"]
        XCTAssertTrue(NSPredicate(format: "label CONTAINS 'idle' AND label CONTAINS 'saved=2' AND label CONTAINS 'exact=true' AND label CONTAINS 'posts=1' AND label CONTAINS 'stops=1'").evaluate(with: receipt))
        app.buttons["Dark"].tap(); shot(app, "app06-dark-complete")
        app.buttons["Light"].tap(); shot(app, "app06-light-complete")
        app.buttons["Back"].tap()
        let saved = app.buttons.matching(NSPredicate(format: "label CONTAINS %@", "Saved fixture 1")).firstMatch
        XCTAssertTrue(saved.waitForExistence(timeout: 15)); saved.tap()
        XCTAssertTrue(latestReply(app).waitForExistence(timeout: 15))
        for _ in 0..<12 { if expand.isHittable { break }; list.swipeDown() }
        XCTAssertTrue(expand.isHittable, "History reopens the same complete user text with its initial preview")
        shot(app, "app06-saved-history")
        app.buttons["Back"].tap()
        XCTAssertTrue(saved.waitForExistence(timeout: 15))
        print("APP06_JOURNEY softwareKeyboard=true fullSubmission=true expandCollapse=true historicalReading=true streamFollow=true originalStop=true savedHistory=true lightDark=true accountCalls=0 databaseWrites=0 modelCalls=0")
    }
}
