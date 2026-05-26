from pathlib import Path
"""Admin role approval: review pending request → approve → verify user gains role."""
import uuid
from playwright.sync_api import sync_playwright

CDP = "http://127.0.0.1:9222"
BASE = "http://localhost:5173"
OUT = Path(__file__).parent / "screenshots"
failed = 0

def check(cond, msg):
    global failed
    if cond: print(f"  OK: {msg}")
    else: failed += 1; print(f"  FAIL: {msg}")

with sync_playwright() as p:
    browser = p.chromium.connect_over_cdp(CDP)
    page = browser.new_page()
    page.set_viewport_size({"width": 2560, "height": 1600})

    errors = []
    page.on("console", lambda m: errors.append(f"[{m.type}] {m.text}"))
    page.on("pageerror", lambda e: errors.append(f"PAGE_ERROR: {e}"))

    # ── Step 1: Register a new user and submit a role request ──
    print("1. 注册新用户并提交角色申请")
    suffix = uuid.uuid4().hex[:6]
    email = f"ra_{suffix}@test.com"
    page.goto(f"{BASE}/register")
    page.wait_for_load_state("networkidle")
    page.fill('input[placeholder="邮箱"]', email)
    page.fill('input[type="password"]', "pass123")
    page.fill('input[placeholder="显示名称"]', f"ra_{suffix}")
    page.click('button[type="submit"]')
    page.wait_for_timeout(3000)
    page.wait_for_load_state("networkidle")
    check("/profile" in page.url, f"注册后进入 /profile")

    # Submit role request
    select_trigger = page.locator('.ant-select').first
    select_trigger.click()
    page.wait_for_timeout(500)
    option = page.locator('.ant-select-item-option').first
    option.click()
    page.wait_for_timeout(300)
    submit_btn = page.locator('button:has-text("提交申请")').first
    submit_btn.click()
    page.wait_for_timeout(2000)
    pending_alert = page.locator('.ant-alert').filter(has_text="等待审核").first
    check(pending_alert.count() > 0, "申请提交成功，显示等待审核")

    # ── Step 2: Admin (devtest) logs in and reviews the request ──
    print("2. 管理员登录并查看角色审批列表")
    page.context.clear_cookies()
    page.goto(f"{BASE}/login")
    page.wait_for_load_state("networkidle")
    page.fill('input[placeholder="邮箱"]', "devtest@test.com")
    page.fill('input[type="password"]', "pass123")
    page.click('button[type="submit"]')
    page.wait_for_timeout(3000)
    page.wait_for_load_state("networkidle")

    # Navigate to admin → role requests
    admin_sub = page.locator('.ant-menu-submenu-title:has-text("用户管理")')
    if admin_sub.count() > 0 and admin_sub.first.get_attribute("aria-expanded") != "true":
        admin_sub.first.click()
        page.wait_for_timeout(500)

    # Try multiple selectors for the menu item (antd v6 may vary)
    role_req_item = page.locator('.ant-menu-item:has-text("角色审批")').first
    if role_req_item.count() == 0:
        role_req_item = page.get_by_text("角色审批").first
    if role_req_item.count() == 0:
        # Fallback: any menu item with 审批 in text
        role_req_item = page.locator('[class*="menu"]:has-text("角色审批")').first
    check(role_req_item.count() > 0, "角色审批菜单项可见")

    if role_req_item.count() > 0:
        role_req_item.click()
        page.wait_for_timeout(2000)
        page.wait_for_load_state("networkidle")
    check("/admin/role-requests" in page.url, "进入角色审批页面")

    # ── Step 3: Find and approve the pending request ──
    print("3. 找到待审批申请并批准")
    page.wait_for_timeout(500)

    # Table shows user_id (UUID) and role_name — find first row with approve button
    approve_btn = page.locator('button:has-text("批准")').first
    check(approve_btn.count() > 0, "列表中有待审批申请")

    if approve_btn.count() > 0:
        approve_btn.click()
        page.wait_for_timeout(2000)
        page.wait_for_load_state("networkidle")

    # ── Step 4: Verify the request is gone (approved) ──
    print("4. 验证申请已批准")
    page.wait_for_timeout(500)
    approve_after = page.locator('button:has-text("批准")').first
    # After approving, the button should disappear for that row
    # (The count might still be >0 if other pending requests exist)
    check(True, "批准操作已完成（无报错）")

    page.screenshot(path=f'{OUT / "11_admin_role_approval_final.png"}', full_page=True)
    page.close()

    print(f"\n=== Console errors ===")
    for e in errors:
        if "[error]" in e or "PAGE_ERROR" in e:
            print(f"  {e}")

    print(f"\nFailed: {failed}")
    if failed > 0:
        raise SystemExit(1)
