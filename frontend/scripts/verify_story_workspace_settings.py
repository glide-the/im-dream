from pathlib import Path
from urllib.parse import urlparse

from playwright.sync_api import Route, sync_playwright


BASE_URL = "http://127.0.0.1:4173"
SCREENSHOT = Path(__file__).resolve().parents[2] / "artifacts" / "story-workspace-settings-e2e.png"


def json_response(route: Route, body: str) -> None:
    route.fulfill(status=200, content_type="application/json", body=body)


def mock_api(route: Route) -> None:
    path = urlparse(route.request.url).path
    method = route.request.method

    if path == "/api/me":
        json_response(route, '{"id":1,"email":"tester@example.com","display_name":"Tester"}')
        return
    if path in {"/api/sessions", "/api/sessions/range"} and method == "GET":
        json_response(route, '{"sessions":[]}')
        return
    if path in {"/api/pictures", "/api/pictures/range"} and method == "GET":
        json_response(route, '{"pictures":[]}')
        return
    if path == "/api/preferences":
        json_response(route, '{"timezone":"Asia/Shanghai"}')
        return
    if path == "/api/system-config":
        # Deliberately differs from the browser's dark preference. Merely
        # mounting the model section must not apply this value.
        json_response(route, '{"success":true,"data":{"theme":"light","workspace_enabled":true}}')
        return
    if path == "/api/decks":
        json_response(route, '{"decks":[]}')
        return
    if path in {"/api/default-voices", "/api/voices"}:
        json_response(route, "[]")
        return
    if path.startswith("/api/") or path.startswith("/polycli/"):
        json_response(route, "{}")
        return
    route.continue_()


with sync_playwright() as playwright:
    browser = playwright.chromium.launch(headless=True)
    page = browser.new_page(viewport={"width": 1600, "height": 900})
    page.on("console", lambda message: print(f"console[{message.type}]: {message.text}"))
    page.on("pageerror", lambda error: print(f"pageerror: {error}"))
    page.route("**/*", mock_api)
    page.add_init_script(
        """
        localStorage.setItem('auth_token', 'e2e-token');
        localStorage.setItem('ink-theme', 'dark');
        localStorage.setItem('ink-language', 'zh');
        """
    )

    page.goto(f"{BASE_URL}/story-workspace/settings")
    page.wait_for_load_state("networkidle")
    try:
        page.locator(".story-workspace-settings").wait_for(timeout=10_000)
    except Exception:
        print("Rendered body:", page.locator("body").inner_text()[:3000])
        raise

    workspace_sidebar = page.locator('[data-story-workspace-region="sidebar"]')
    workspace_main = page.locator('[data-story-workspace-region="main"]')
    assert workspace_sidebar.is_visible(), "StoryWorkspaceSidebar should stay visible"
    assert workspace_main.is_visible(), "right-side Story Workspace main region should be visible"
    assert workspace_sidebar.bounding_box()["x"] < workspace_main.bounding_box()["x"]

    main_nav_labels = workspace_sidebar.locator(
        ".story-workspace-sidebar__nav > .story-workspace-sidebar__nav-button"
    ).all_inner_texts()
    assert main_nav_labels == ["写作", "时间线", "回顾", "卡组", "Dream", "对话"], main_nav_labels

    footer_labels = workspace_sidebar.locator(".story-workspace-sidebar__footer button:not([hidden])").all_inner_texts()
    assert footer_labels[-2:] == ["订阅", "设置"], footer_labels

    settings_button = workspace_sidebar.get_by_role("button", name="设置", exact=True)
    subscription_button = workspace_sidebar.get_by_role("button", name="订阅", exact=True)

    # Subscription and Settings replace only the right-hand content. The
    # StoryWorkspaceSidebar remains mounted and in the same position.
    sidebar_before = workspace_sidebar.bounding_box()
    subscription_button.click()
    page.wait_for_url("**/story-workspace/subscription")
    page.get_by_role("heading", name="选择适合现在创作节奏的方式").wait_for()
    assert workspace_sidebar.is_visible()
    assert workspace_sidebar.bounding_box() == sidebar_before

    settings_button.click()
    page.wait_for_url("**/story-workspace/settings")
    page.get_by_role("navigation", name="设置分类导航").wait_for()
    assert workspace_sidebar.is_visible()
    assert workspace_sidebar.bounding_box() == sidebar_before
    assert page.locator("section#settings-general").is_visible()

    theme_before = page.locator("html").get_attribute("data-theme")
    assert theme_before == "dark", theme_before
    page.get_by_role("button", name="AI 模型", exact=True).click()
    page.wait_for_url("**/story-workspace/settings/model")
    page.locator("section#settings-model").wait_for()
    page.wait_for_timeout(250)
    theme_after = page.locator("html").get_attribute("data-theme")
    assert theme_after == theme_before, (theme_before, theme_after)

    page.get_by_role("button", name="关于", exact=True).click()
    page.wait_for_url("**/story-workspace/settings/about")
    page.locator("section#settings-about").wait_for()
    assert page.locator("html").get_attribute("data-theme") == "dark"

    # The former top-level LeftSidebar Settings entry must now enter the same
    # embedded Story Workspace layout instead of mounting App's standalone
    # settings viewport.
    page.goto(BASE_URL)
    page.wait_for_load_state("networkidle")
    legacy_settings_button = page.locator('button[title="设置"]')
    legacy_settings_button.focus()
    page.keyboard.press("Enter")
    page.wait_for_url("**/story-workspace/settings")
    page.locator('[data-story-workspace-region="sidebar"]').wait_for()
    page.locator("section#settings-general").wait_for()

    page.get_by_role("button", name="关于", exact=True).click()
    page.wait_for_url("**/story-workspace/settings/about")
    page.locator("section#settings-about").wait_for()

    SCREENSHOT.parent.mkdir(parents=True, exist_ok=True)
    page.screenshot(path=str(SCREENSHOT), full_page=True)
    browser.close()

print(f"PASS: Story Workspace settings layout verified; screenshot={SCREENSHOT}")
