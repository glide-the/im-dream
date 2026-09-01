# [Input] Story Workspace preview build and mocked authenticated API reads.
# [Output] Provider-free browser layout verification and named screenshots.
# [Pos] Frontend verification script.
# [Sync] 2026-08-31: stop mocking the removed /polycli runtime surface.

from pathlib import Path
from urllib.parse import urlparse

from playwright.sync_api import Route, sync_playwright


BASE_URL = "http://127.0.0.1:4173"
SCREENSHOT = Path(__file__).resolve().parents[2] / "artifacts" / "story-workspace-settings-e2e.png"
WRITING_SCREENSHOT = Path(__file__).resolve().parents[2] / "artifacts" / "story-workspace-writing-e2e.png"
SUBSCRIPTION_SCREENSHOT = Path(__file__).resolve().parents[2] / "artifacts" / "story-workspace-subscription-e2e.png"


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
    if path == "/api/sessions/aggregate" and method == "GET":
        json_response(route, '{"stats":{"total_days":0,"total_entries":0,"total_words":0},"sessions":[],"timezone":"Asia/Shanghai"}')
        return
    if path == "/api/reports" and method == "GET":
        json_response(route, '{"reports":[]}')
        return
    if path == "/api/reflections/latest" and method == "GET":
        json_response(route, '{"task":null,"results":[]}')
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
    if path.startswith("/api/"):
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
    assert workspace_main.is_visible(), "right-side Story Workspace main region should be visible"
    assert workspace_sidebar.count() == 0, "StoryWorkspaceSidebar should be hidden on Settings"
    page.get_by_role("button", name="返回应用").click()
    page.wait_for_url("**/story-workspace/dream")
    workspace_sidebar = page.locator('[data-story-workspace-region="sidebar"]')
    workspace_main = page.locator('[data-story-workspace-region="main"]')
    assert workspace_sidebar.is_visible(), "StoryWorkspaceSidebar should return after Settings"
    assert workspace_sidebar.bounding_box()["x"] < workspace_main.bounding_box()["x"]

    main_nav_labels = workspace_sidebar.locator(
        ".story-workspace-sidebar__nav > .story-workspace-sidebar__nav-button"
    ).all_inner_texts()
    assert main_nav_labels == ["写作", "时间线", "回顾", "卡组", "Dream", "对话"], main_nav_labels

    workspace_sidebar.get_by_role("button", name="折叠侧边栏").click()
    collapsed_nav = workspace_sidebar.locator(
        ".story-workspace-sidebar__nav > .story-workspace-sidebar__nav-button"
    )
    assert collapsed_nav.count() == 6
    assert collapsed_nav.locator(".story-workspace-sidebar__icon").count() == 6
    for index in range(collapsed_nav.count()):
        assert collapsed_nav.nth(index).locator(".story-workspace-sidebar__icon").is_visible()
    workspace_sidebar.get_by_role("button", name="展开侧边栏").click()

    footer_labels = workspace_sidebar.locator(
        ".story-workspace-sidebar__footer > button:not([hidden])"
    ).all_inner_texts()
    assert footer_labels[-1:] == ["设置"], footer_labels

    settings_button = workspace_sidebar.get_by_role("button", name="设置", exact=True)

    # Subscription replaces only the right-hand content and keeps the
    # StoryWorkspaceSidebar mounted in the same position.
    sidebar_before = workspace_sidebar.bounding_box()

    for label, path in (
        ("写作", "/story-workspace/writing"),
        ("时间线", "/story-workspace/timeline"),
        ("回顾", "/story-workspace/analysis"),
        ("卡组", "/story-workspace/decks"),
        ("Dream", "/story-workspace/dream"),
        ("对话", "/story-workspace/chat"),
    ):
        workspace_sidebar.get_by_role("button", name=label, exact=True).click()
        page.wait_for_url(f"**{path}")
        assert workspace_sidebar.is_visible()
        assert workspace_main.is_visible()
        assert workspace_sidebar.bounding_box()["x"] < workspace_main.bounding_box()["x"]
        if path.endswith("/writing"):
            writing_editor = page.get_by_placeholder("Start writing...")
            writing_editor.wait_for()
            assert writing_editor.bounding_box()["x"] > workspace_sidebar.bounding_box()["x"] + workspace_sidebar.bounding_box()["width"]
            page.screenshot(path=str(WRITING_SCREENSHOT), full_page=True)

    settings_button.click()
    page.wait_for_url("**/story-workspace/settings")
    page.get_by_role("navigation", name="设置分类导航").wait_for()
    assert page.locator('[data-story-workspace-region="sidebar"]').count() == 0
    assert page.get_by_role("button", name="返回应用").is_visible()
    assert page.locator("section#settings-general").is_visible()

    page.get_by_role("button", name="返回应用").click()
    page.wait_for_url("**/story-workspace/dream")
    workspace_sidebar = page.locator('[data-story-workspace-region="sidebar"]')

    workspace_sidebar.get_by_role("button", name="设置", exact=True).click()
    page.wait_for_url("**/story-workspace/settings")
    page.get_by_role("button", name="订阅", exact=True).click()
    page.wait_for_url("**/story-workspace/subscription")
    page.locator("#story-workspace-subscription-title").wait_for()
    page.get_by_role("heading", name="选择适合现在创作节奏的方式").wait_for()
    assert page.locator('[data-story-workspace-region="sidebar"]').count() == 0
    page.screenshot(path=str(SUBSCRIPTION_SCREENSHOT), full_page=True)
    page.get_by_role("button", name="返回应用").click()
    page.wait_for_url("**/story-workspace/dream")
    workspace_sidebar = page.locator('[data-story-workspace-region="sidebar"]')

    user_trigger = workspace_sidebar.get_by_role("button", name="打开用户菜单")
    user_trigger.click()
    user_menu = page.get_by_role("menu", name="用户菜单")
    assert user_menu.is_visible()
    assert user_menu.get_by_role("menuitem", name="Logout").is_visible()
    page.keyboard.press("Escape")
    assert not user_menu.is_visible()

    workspace_sidebar.get_by_role("button", name="设置", exact=True).click()
    page.wait_for_url("**/story-workspace/settings")
    page.get_by_role("button", name="资源连接", exact=True).click()
    page.wait_for_url("**/story-workspace/settings/resources")
    connector_surface = page.locator('section[aria-label="资源链接设置"]')
    connector_surface.wait_for()
    connector_styles = connector_surface.evaluate(
        """(element) => {
          const styles = getComputedStyle(element);
          return {
            borderWidth: styles.borderWidth,
            borderRadius: styles.borderRadius,
            background: styles.backgroundColor,
            boxShadow: styles.boxShadow,
          };
        }"""
    )
    assert connector_styles["borderWidth"] == "0px", connector_styles
    assert connector_styles["borderRadius"] == "0px", connector_styles
    assert connector_styles["boxShadow"] == "none", connector_styles

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
    assert page.locator('[data-story-workspace-region="sidebar"]').count() == 0
    page.get_by_role("button", name="返回应用").wait_for()
    page.locator("section#settings-general").wait_for()

    page.get_by_role("button", name="关于", exact=True).click()
    page.wait_for_url("**/story-workspace/settings/about")
    page.locator("section#settings-about").wait_for()

    SCREENSHOT.parent.mkdir(parents=True, exist_ok=True)
    page.screenshot(path=str(SCREENSHOT), full_page=True)

    # Verify the migrated floating menu still completes the real auth logout.
    page.get_by_role("button", name="返回应用").click()
    page.wait_for_url("**/story-workspace/dream")
    workspace_sidebar = page.locator('[data-story-workspace-region="sidebar"]')
    workspace_sidebar.get_by_role("button", name="打开用户菜单").click()
    page.get_by_role("menuitem", name="Logout").click()
    page.get_by_role("heading", name="Welcome Back").wait_for()
    assert page.evaluate("localStorage.getItem('auth_token')") is None
    browser.close()

print(f"PASS: Story Workspace settings layout verified; screenshot={SCREENSHOT}")
