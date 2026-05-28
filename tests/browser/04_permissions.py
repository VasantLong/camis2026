from pathlib import Path
"""Permission boundaries: no-role user, 403 page, role-based sidebar."""
from playwright.sync_api import sync_playwright
from utils import CDP, BASE, create_page, setup_logging, start_recording

OUT = Path(__file__).parent / 'screenshots'
failed = 0

def check(cond, msg):
    global failed
    if cond:
        print(f"  OK: {msg}")
    else:
        failed += 1
        print(f"  FAIL: {msg}")

def login_as(page, email, password):
    page.context.clear_cookies()
    page.goto(f"{BASE}/login")
    page.wait_for_load_state("networkidle")
    page.fill('input[placeholder="邮箱"]', email)
    page.fill('input[type="password"]', password)
    page.click('button[type="submit"]')
    page.wait_for_timeout(3000)
    page.wait_for_load_state("networkidle")

with sync_playwright() as p:
    browser = p.chromium.connect_over_cdp(CDP)
    page = create_page(browser)
    setup_logging("04_permissions")
    recorder = start_recording(page, "04_permissions")

    errors = []
    page.on("console", lambda m: errors.append(f"[{m.type}] {m.text}"))
    page.on("pageerror", lambda e: errors.append(f"PAGE_ERROR: {e}"))

    # 1. No-role user → /activities → 403 (authenticated but no permissions)
    print("1. testuser (no role) → /activities")
    login_as(page, "testuser@test.com", "test123")
    check("/403" in page.url, f"testuser blocked at /403 (got {page.url})")

    # 2. Already on /403 from step 1 — verify 403 page content
    print("2. Verify 403 page")
    check("403" in page.content() or "权限" in page.content() or "Access" in page.content(),
          "403 page has access denied content")

    # 3. tester1 → sidebar has both sections
    print("3. tester1 login")
    page.context.clear_cookies()
    login_as(page, "tester1@test.com", "pass123")
    # After login, should be on /activities (has permissions)
    on_activities = "/activities" in page.url
    on_dashboard = "/dashboard" in page.url
    check(on_activities or on_dashboard, f"tester1 on protected page (got {page.url})")
    sidebar_text = page.locator('.ant-layout-sider').inner_text()
    check("活动管理" in sidebar_text, "sidebar has 活动管理")
    check("活动面板" in sidebar_text, "sidebar has 活动面板")

    # 4. Create activity submenu item visible
    print("4. Create activity menu item")
    submenu = page.locator('.ant-menu-submenu-title:has-text("活动管理")')
    if submenu.count() > 0:
        submenu.first.click()
        page.wait_for_timeout(500)
    create_item = page.locator('.ant-menu-item:has-text("创建新活动")')
    check(create_item.count() > 0, "create activity menu item visible")

    page.screenshot(path=f'{OUT / '04_permissions_final.png'}', full_page=True)
    if recorder:
        recorder.stop()
    page.close()

    print(f"\n=== Console errors ===")
    error_msgs = [e for e in errors if "[error]" in e or "PAGE_ERROR" in e]
    for e in error_msgs:
        print(f"  {e}")
    if not error_msgs:
        print("  (none)")

    print(f"\nFailed: {failed}")
    if failed > 0:
        raise SystemExit(1)
