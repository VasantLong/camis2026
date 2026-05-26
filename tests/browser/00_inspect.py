"""Page reconnaissance: screenshot each route + list interactive elements.
Uses devtest (all-role user) for maximum page coverage."""
from pathlib import Path
from playwright.sync_api import sync_playwright

OUT = Path(__file__).parent / "screenshots"
OUT.mkdir(parents=True, exist_ok=True)

CDP = "http://127.0.0.1:9222"
BASE = "http://localhost:5173"


def inspect(page, name: str):
    page.wait_for_load_state("networkidle")
    page.wait_for_timeout(500)
    path = OUT / f"{name}.png"
    page.screenshot(path=path, full_page=True)
    print(f"[screenshot] {path}")

    buttons = page.locator("button").all()
    inputs = page.locator("input").all()
    links = page.locator("a").all()

    print(f"  buttons: {len(buttons)}, inputs: {len(inputs)}, links: {len(links)}")
    for b in buttons:
        text = b.inner_text()[:80].replace("\n", " ")
        if text:
            print(f"    [button] {text}")
    for i in inputs:
        ph = i.get_attribute("placeholder") or ""
        tp = i.get_attribute("type") or "text"
        if tp != "hidden":
            print(f"    [input] type={tp} placeholder='{ph}'")
    for a in links:
        href = a.get_attribute("href") or ""
        text = a.inner_text()[:40].replace("\n", " ")
        if text and href:
            print(f"    [link] {text} -> {href}")


with sync_playwright() as p:
    browser = p.chromium.connect_over_cdp(CDP)
    page = browser.new_page()
    page.set_viewport_size({"width": 2560, "height": 1600})

    console_errors: list[str] = []
    page.on("console", lambda msg: console_errors.append(f"[{msg.type}] {msg.text}"))
    page.on("pageerror", lambda err: console_errors.append(f"[PAGE_ERROR] {err}"))

    auth_results: list[str] = []
    def log_response(response):
        if "/auth/" in response.url:
            try:
                body = response.text()
                auth_results.append(f"{response.status} {response.url} body={body[:120]}")
            except:
                auth_results.append(f"{response.status} {response.url}")
    page.on("response", log_response)

    # --- PUBLIC ---
    print("=== /login ===")
    page.goto(f"{BASE}/login")
    inspect(page, "01_login")

    print("=== /register ===")
    page.goto(f"{BASE}/register")
    inspect(page, "02_register")

    # --- LOGIN as devtest (all roles, all permissions) ---
    print("=== login as devtest ===")
    page.goto(f"{BASE}/login")
    page.wait_for_load_state("networkidle")
    page.fill('input[placeholder="邮箱"]', "devtest@test.com")
    page.fill('input[type="password"]', "pass123")
    page.click('button[type="submit"]')
    page.wait_for_timeout(3000)
    page.wait_for_load_state("networkidle")
    print(f"  url: {page.url}")

    # --- PROTECTED (via client-side sidebar nav) ---

    # Activities list
    print("=== /activities (via sidebar) ===")
    inspect(page, "03_activities")

    # Expand "活动管理" submenu
    submenu = page.locator('.ant-menu-submenu-title:has-text("活动管理")')
    if submenu.count() > 0:
        submenu.first.click()
        page.wait_for_timeout(500)

    # Create activity
    print("=== /activities/new ===")
    create_item = page.locator('.ant-menu-item:has-text("创建新活动")')
    if create_item.count() > 0:
        create_item.first.click()
        page.wait_for_timeout(2000)
        page.wait_for_load_state("networkidle")
        inspect(page, "04_activities_new")
    else:
        print("  '创建新活动' menu item not found")

    # Dashboard
    print("=== /dashboard ===")
    dash_item = page.locator('.ant-menu-item:has-text("活动面板")')
    if dash_item.count() > 0:
        dash_item.first.click()
        page.wait_for_timeout(2000)
        page.wait_for_load_state("networkidle")
        inspect(page, "05_dashboard")
    else:
        print("  '活动面板' menu item not found")

    # Admin: Role Requests
    print("=== /admin/role-requests ===")
    admin_sub = page.locator('.ant-menu-submenu-title:has-text("用户管理")')
    if admin_sub.count() > 0 and admin_sub.first.get_attribute("aria-expanded") != "true":
        admin_sub.first.click()
        page.wait_for_timeout(500)
    role_req_item = page.locator('.ant-menu-item:has-text("角色审批")')
    if role_req_item.count() > 0:
        role_req_item.first.click()
        page.wait_for_timeout(2000)
        page.wait_for_load_state("networkidle")
        inspect(page, "06_admin_role_requests")
    else:
        print("  '角色审批' menu item not found")

    # Admin: User Management
    print("=== /admin/users ===")
    user_mgmt_item = page.locator('.ant-menu-item:has-text("用户列表")')
    if user_mgmt_item.count() > 0:
        user_mgmt_item.first.click()
        page.wait_for_timeout(2000)
        page.wait_for_load_state("networkidle")
        inspect(page, "07_admin_users")
    else:
        print("  '用户列表' menu item not found")

    # Profile
    print("=== /profile ===")
    profile_item = page.locator('.ant-menu-item:has-text("个人中心")')
    if profile_item.count() > 0:
        profile_item.first.click()
        page.wait_for_timeout(2000)
        page.wait_for_load_state("networkidle")
        inspect(page, "08_profile")
    else:
        print("  '个人中心' menu item not found")

    page.close()
    print(f"\n=== Auth responses ===")
    for r in auth_results:
        print(f"  {r}")
    print(f"\n=== Console ({len(console_errors)}) ===")
    for e in console_errors[-20:]:
        print(f"  {e}")
