from pathlib import Path
"""Auth flow: login, logout, register, redirect."""
from playwright.sync_api import sync_playwright

CDP = "http://127.0.0.1:9222"
BASE = "http://localhost:5173"
OUT = Path(__file__).parent / 'screenshots'
failed = 0

def check(cond, msg):
    global failed
    if cond:
        print(f"  OK: {msg}")
    else:
        failed += 1
        print(f"  FAIL: {msg}")

with sync_playwright() as p:
    browser = p.chromium.connect_over_cdp(CDP)
    page = browser.new_page()
    page.set_viewport_size({"width": 1920, "height": 1080})
    page.context.clear_cookies()

    errors = []
    page.on("console", lambda m: errors.append(f"[{m.type}] {m.text}"))
    page.on("pageerror", lambda e: errors.append(f"PAGE_ERROR: {e}"))

    # 1. Visit / → redirect to /login
    print("1. Redirect / -> /login")
    page.goto(f"{BASE}/")
    page.wait_for_load_state("networkidle")
    check("/login" in page.url, f"URL contains /login (got {page.url})")

    # 2. Wrong password
    print("2. Wrong password login")
    page.goto(f"{BASE}/login")
    page.wait_for_load_state("networkidle")
    page.fill('input[placeholder="用户名"]', "tester1")
    page.fill('input[type="password"]', "wrongpassword")
    page.click('button[type="submit"]')
    page.wait_for_timeout(2000)
    # Should stay on /login (login failed)
    still_login = "/login" in page.url
    # Also check for toast or alert
    toast = page.locator('.ant-message-notice-content, .ant-notification-notice').first
    has_toast = toast.count() > 0 and "Invalid" in (toast.inner_text() or "")
    check(still_login, f"stayed on /login after wrong password (got {page.url})")

    # 3. Correct login
    print("3. Correct login")
    page.context.clear_cookies()
    page.goto(f"{BASE}/login")
    page.wait_for_load_state("networkidle")
    page.fill('input[placeholder="用户名"]', "tester1")
    page.fill('input[type="password"]', "pass123")
    page.click('button[type="submit"]')
    page.wait_for_timeout(3000)
    page.wait_for_load_state("networkidle")
    check("/activities" in page.url, f"redirected to /activities (got {page.url})")
    sidebar = page.locator('.ant-layout-sider')
    check(sidebar.count() > 0, "sidebar visible after login")

    # 4. Logout
    print("4. Logout")
    user_btn = page.locator('button:has-text("tester1")')
    if user_btn.count() > 0:
        user_btn.first.click()
        page.wait_for_timeout(500)
        logout_item = page.locator('.ant-dropdown-menu-item:has-text("退出登录")')
        if logout_item.count() > 0:
            logout_item.first.click()
            page.wait_for_timeout(2000)
            page.wait_for_load_state("networkidle")
            check("/login" in page.url, f"redirected to /login after logout (got {page.url})")
        else:
            check(False, "logout menu item not found")
    else:
        # fallback: navigate to login, try clicking user in header
        check(False, "user button not found")

    # 5. Register new user (no roles → gets 403 on protected routes)
    print("5. Register new user")
    import uuid
    uname = f"test_{uuid.uuid4().hex[:8]}"
    page.goto(f"{BASE}/register")
    page.wait_for_load_state("networkidle")
    page.fill('input[placeholder="用户名"]', uname)
    page.fill('input[placeholder="邮箱"]', f"{uname}@test.com")
    page.fill('input[type="password"]', "pass123")
    page.click('button[type="submit"]')
    page.wait_for_timeout(3000)
    page.wait_for_load_state("networkidle")
    # New users have no role → redirect to /activities → no permission → 403
    check("/403" in page.url or "403" in page.content(),
          f"new user (no role) blocked with 403 (got {page.url})")

    page.screenshot(path=f'{OUT / '01_auth_final.png'}', full_page=True)
    page.close()

    # Report
    print(f"\n=== Console errors ===")
    error_msgs = [e for e in errors if "[error]" in e or "PAGE_ERROR" in e]
    if error_msgs:
        for e in error_msgs:
            print(f"  {e}")
    else:
        print("  (none)")

    print(f"\nFailed: {failed}")
    if failed > 0:
        raise SystemExit(1)
