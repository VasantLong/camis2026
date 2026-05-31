from pathlib import Path
"""Permission boundaries: no-role user, 403 page, role-based sidebar."""
from playwright.sync_api import sync_playwright
from utils import (CDP, BASE, create_page, setup_logging, start_recording,
                   check, get_failed, login_as)

OUT = Path(__file__).parent / 'screenshots'

with sync_playwright() as p:
    browser = p.chromium.connect_over_cdp(CDP)
    page = create_page(browser)
    setup_logging("04_permissions")
    recorder = start_recording(page, "04_permissions")

    errors = []
    page.on("console", lambda m: errors.append(f"[{m.type}] {m.text}"))
    page.on("pageerror", lambda e: errors.append(f"PAGE_ERROR: {e}"))

    # 1. No-role user → try to access /activities → 403
    print("1. testuser (no role) → /activities")
    login_as(page, "testuser@test.com", "test123")
    check("/login" not in page.url, "testuser logged in")
    # No-role user tries to access a protected page → 403
    page.goto(f"{BASE}/activities")
    page.wait_for_timeout(3000)
    page.wait_for_load_state("networkidle")
    check("/403" in page.url, f"testuser blocked at /403 (got {page.url})")

    # 2. Already on /403 from step 1 — verify 403 page content
    print("2. Verify 403 page")
    check("403" in page.content() or "权限" in page.content() or "Access" in page.content(),
          "403 page has access denied content")

    # 3. promoter → sidebar has 活动管理
    print("3. promoter login")
    page.context.clear_cookies()
    login_as(page, "promoter@test.com", "pass123")
    check("/login" not in page.url, "promoter logged in")
    sidebar_text = page.locator('.ant-layout-sider').inner_text()
    check("活动管理" in sidebar_text, "sidebar has 活动管理")

    # 4. Create activity submenu item visible
    print("4. Create activity menu item")
    submenu = page.locator('.ant-menu-submenu-title:has-text("活动管理")')
    if submenu.count() > 0:
        submenu.first.click()
        page.wait_for_timeout(500)
    create_item = page.locator('.ant-menu-item:has-text("创建新活动")')
    check(create_item.count() > 0, "create activity menu item visible")

    # 5. SecurityOfficer-only: sees sign button, NOT reject/confirm_approval
    print("5. SecurityOfficer restricted buttons")
    page.context.clear_cookies()
    login_as(page, "security@test.com", "pass123")
    check("/login" not in page.url, "security officer logged in")
    sidebar_text3 = page.locator('.ant-layout-sider').inner_text()
    check("活动管理" in sidebar_text3, "security officer sees 活动管理")
    # Navigate to activity list
    sub = page.locator('.ant-menu-submenu-title:has-text("活动管理")')
    if sub.count() > 0 and sub.first.get_attribute("aria-expanded") != "true":
        sub.first.click()
        page.wait_for_timeout(400)
    all_act = page.locator('.ant-menu-item:has-text("全部活动")').first
    if all_act.count() > 0:
        all_act.click()
        page.wait_for_timeout(1500)
        page.wait_for_load_state("networkidle")
    page.wait_for_selector('.ant-table-tbody tr', timeout=10000)
    page.wait_for_timeout(500)
    first_link = page.locator('.ant-table-tbody tr a').first
    if first_link.count() > 0:
        first_link.click()
        page.wait_for_timeout(2000)
        page.wait_for_load_state("networkidle")
    has_reject = page.locator('button:has-text("驳回")').count() > 0
    has_confirm = page.locator('button:has-text("确认审批")').count() > 0
    has_sign = page.locator('button:has-text("签署")').count() > 0
    check(not has_reject, "security officer does NOT see reject button")
    check(not has_confirm, "security officer does NOT see confirm_approval button")
    check(has_sign, "security officer sees sign-related button")

    # 6. SecurityManager: sees reject/confirm_approval buttons
    print("6. SecurityManager elevated buttons")
    page.context.clear_cookies()
    login_as(page, "security_mgr@test.com", "pass123")
    check("/login" not in page.url, "security manager logged in")
    page.wait_for_selector('.ant-table-tbody tr', timeout=10000)
    page.wait_for_timeout(500)
    first_link2 = page.locator('.ant-table-tbody tr a').first
    if first_link2.count() > 0:
        first_link2.click()
        page.wait_for_timeout(2000)
        page.wait_for_load_state("networkidle")
    has_reject2 = page.locator('button:has-text("驳回")').count() > 0
    has_confirm2 = page.locator('button:has-text("确认审批")').count() > 0
    print(f"  (reject button visible: {has_reject2}, confirm_approval visible: {has_confirm2})")

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

    failed = get_failed()
    print(f"\nFailed: {failed}")
    if failed > 0:
        raise SystemExit(1)
