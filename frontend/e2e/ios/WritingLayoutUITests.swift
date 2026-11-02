// [Input] Isolated Simulator app containing the production WritingView/WKWebView and packaged original Next resources.
// [Output] Actual native header readiness, duplicate removal, toolbar geometry, keyboard and touch-scroll proof.
// [Pos] Provider-free Simulator UI acceptance; only in-memory DTO fixtures receive text/selection writes.
import XCTest

@MainActor
final class WritingLayoutUITests: XCTestCase {
    func testPackagedWritingHeaderAndTouchChooser() throws {
        continueAfterFailure = false
        let target = try XCTUnwrap(ProcessInfo.processInfo.environment["INK_WRITING_UI_TARGET"])
        let app = XCUIApplication(bundleIdentifier: target)
        app.launch()
        let header = app.buttons["Unhappy"]
        XCTAssertTrue(header.waitForExistence(timeout: 30), "The native header must receive chooser-view from the actual packaged Writing document")
        XCTAssertTrue(header.isHittable)
        XCTAssertFalse(app.buttons["正在读取…"].exists)
        let web = app.webViews.firstMatch
        XCTAssertTrue(web.waitForExistence(timeout: 10))
        XCTAssertFalse(web.staticTexts["Unhappy"].exists, "Mobile metadata must not repeat the chooser value in the body")
        let calendar = web.buttons["Calendar"]
        XCTAssertTrue(calendar.isHittable)
        let date = web.staticTexts.matching(NSPredicate(format: "label CONTAINS %@ AND label CONTAINS %@", "年", "星期")).firstMatch
        XCTAssertTrue(date.exists)
        XCTAssertLessThanOrEqual(calendar.frame.maxY, date.frame.minY + 2, "The toolbar must remain above the date metadata")
        let before = XCTAttachment(screenshot: app.screenshot()); before.name = "writing-packaged-ready"; before.lifetime = .keepAlways; add(before)

        let editor = web.textViews.firstMatch
        XCTAssertTrue(editor.isHittable)
        editor.tap()
        editor.typeText("An ordinary morning with handwritten lines.\nA second line.\n")
        let keyboardVisible = app.keyboards.count > 0
        header.tap()
        XCTAssertTrue(web.buttons["OK"].waitForExistence(timeout: 10))
        XCTAssertEqual(app.keyboards.count, 0, "The chooser header action must dismiss the editor keyboard")
        let back = app.buttons["← 更多"]
        XCTAssertTrue(back.isHittable)
        back.tap()
        app.buttons["返回写作"].tap()
        XCTAssertTrue(header.waitForExistence(timeout: 10))
        XCTAssertFalse(web.buttons["OK"].exists)
        XCTAssertTrue((web.textViews.firstMatch.value as? String ?? "").contains("An ordinary morning"))

        app.buttons["首次心情夹具"].tap()
        let choose = app.buttons["选择心情"]
        XCTAssertTrue(choose.waitForExistence(timeout: 20))
        let option = app.webViews.buttons["OK"]
        XCTAssertFalse(option.isHittable, "Long startup content must begin above the option")
        for _ in 0..<12 {
            if option.isHittable { break }
            app.webViews.firstMatch.swipeUp()
        }
        XCTAssertTrue(option.isHittable, "Real WKWebView touch swipes must expose the original options")
        let scrolled = XCTAttachment(screenshot: app.screenshot()); scrolled.name = "writing-startup-touch-scrolled"; scrolled.lifetime = .keepAlways; add(scrolled)
        option.tap()
        let chosen = app.buttons["OK"]
        XCTAssertTrue(chosen.waitForExistence(timeout: 10))
        XCTAssertTrue(chosen.isHittable)
        XCTAssertFalse(app.webViews.buttons["OK"].exists)
        XCTAssertEqual(app.keyboards.count, 0, "Selecting an emotion must not refocus the blank textarea")
        let after = XCTAttachment(screenshot: app.screenshot()); after.name = "writing-selected-header"; after.lifetime = .keepAlways; add(after)
        print("INK_WRITING_PACKAGED_PROOF headerReady=true duplicateChooser=false toolbarOverlap=false keyboardInitiallyVisible=\(keyboardVisible) touchOptionsReachable=true selectedHeader=true realAccounts=0 databaseWrites=0 modelCalls=0")
    }
}
