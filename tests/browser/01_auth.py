from pathlib import Path
"""Auth flow: login, logout, register, redirect."""
from playwright.sync_api import sync_playwright
from utils import CDP, BASE, create_page, start_recording

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
    page = create_page(browser)
    recorder = start_recording(page, "01_auth")
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
    page.fill('input[placeholder="邮箱"]', "devtest@test.com")
    page.fill('input[type="password"]', "wrongpassword")
    page.click('button[type="submit"]')
    page.wait_for_timeout(2000)
    still_login = "/login" in page.url
    toast = page.locator('.ant-message').filter(has_text="邮箱或密码错误").first
    has_toast = toast.count() > 0
    check(still_login, f"stayed on /login after wrong password (got {page.url})")
    check(has_toast, "error toast visible after wrong password")

    # 2b. Wrong username (should show same error, no page reload)
    print("2b. Wrong username login")
    page.context.clear_cookies()
    page.goto(f"{BASE}/login")
    page.wait_for_load_state("networkidle")
    page.fill('input[placeholder="邮箱"]', "nonexistent@test.com")
    page.fill('input[type="password"]', "pass123")
    page.click('button[type="submit"]')
    page.wait_for_timeout(2000)
    still_login2 = "/login" in page.url
    toast2 = page.locator('.ant-message').filter(has_text="邮箱或密码错误").first
    has_toast2 = toast2.count() > 0
    check(still_login2, f"stayed on /login after wrong username (got {page.url})")
    check(has_toast2, "error toast visible after wrong username")

    # 3. Correct login → protected page (depends on user's permissions)
    print("3. Correct login")
    page.context.clear_cookies()
    page.goto(f"{BASE}/login")
    page.wait_for_load_state("networkidle")
    page.fill('input[placeholder="邮箱"]', "devtest@test.com")
    page.fill('input[type="password"]', "pass123")
    page.click('button[type="submit"]')
    page.wait_for_timeout(3000)
    page.wait_for_load_state("networkidle")
    is_protected = "/activities" in page.url or "/dashboard" in page.url or "/profile" in page.url
    not_login = "/login" not in page.url
    check(not_login, f"redirected away from /login (got {page.url})")
    check(is_protected, f"landed on protected page (got {page.url})")
    sidebar = page.locator('.ant-layout-sider')
    check(sidebar.count() > 0, "sidebar visible after login")

    # 4. Logout
    print("4. Logout")
    user_btn = page.locator('.ant-layout-header button:has(.anticon-user)')
    if user_btn.count() == 0:
        user_btn = page.locator('header button:has(.anticon-user)')
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
        check(False, "user button not found")

    # 5. Register new user → lands on /profile (no roles, no 403)
    print("5. Register new user")
    import uuid
    uname = f"test_{uuid.uuid4().hex[:8]}"
    page.goto(f"{BASE}/register")
    page.wait_for_load_state("networkidle")
    page.fill('input[placeholder="邮箱"]', f"{uname}@test.com")
    page.fill('input[type="password"]', "pass123")
    page.fill('input[placeholder="显示名称"]', uname)
    page.click('button[type="submit"]')
    page.wait_for_timeout(3000)
    page.wait_for_load_state("networkidle")
    check("/profile" in page.url,
          f"new user (no role) lands on /profile (got {page.url})")

    # 5b. Register with duplicate email → 409
    print("5b. Register duplicate email")
    page.goto(f"{BASE}/register")
    page.wait_for_load_state("networkidle")
    page.fill('input[placeholder="邮箱"]', f"{uname}@test.com")
    page.fill('input[type="password"]', "pass123")
    page.fill('input[placeholder="显示名称"]', uname)
    page.click('button[type="submit"]')
    page.wait_for_timeout(2000)
    toast3 = page.locator('.ant-message').filter(has_text="邮箱已注册").first
    has_toast3 = toast3.count() > 0
    still_register = "/register" in page.url
    check(still_register, f"stayed on /register after duplicate (got {page.url})")
    check(has_toast3, "duplicate error toast visible")

    page.screenshot(path=f'{OUT / '01_auth_final.png'}', full_page=True)
    if recorder:
        recorder.stop()
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
