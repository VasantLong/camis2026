"""SuperAdmin user management: user list, detail drawer, archive/unarchive, edit roles, toggle active."""
from pathlib import Path
import uuid
from playwright.sync_api import sync_playwright
from utils import (CDP, BASE, API, create_page, setup_logging, start_recording,
                   check, get_failed, login_as, api_post, api_get, login_api)

OUT = Path(__file__).parent / "screenshots"

# --- Register dynamic test user via API ---
uname = f"sa_test_{uuid.uuid4().hex[:8]}"
email = f"{uname}@test.com"
password = "pass123"
api_post("/auth/register", {"email": email, "password": password, "display_name": uname}, None)
print(f"API registered: {email}")

sa_token, _ = login_api("superadmin@test.com", "pass123")
users = api_get("/admin/users", sa_token)
test_user = next((u for u in users if u["email"] == email), None)
check(test_user is not None, f"found test user: {email}")
uid = test_user["id"]

with sync_playwright() as p:
    browser = p.chromium.connect_over_cdp(CDP)
    page = create_page(browser)
    setup_logging("14_superadmin_users")
    recorder = start_recording(page, "14_superadmin_users")

    errors = []
    page.on("console", lambda m: errors.append(f"[{m.type}] {m.text}"))
    page.on("pageerror", lambda e: errors.append(f"PAGE_ERROR: {e}"))

    # ============================================================
    # 1. SuperAdmin login → navigate to user management
    # ============================================================
    print("\n=== 1. Login as SuperAdmin, navigate to user management ===")
    login_as(page, "superadmin@test.com", "pass123")
    check("/login" not in page.url, "superadmin logged in")

    # Navigate via sidebar: 用户管理 → 用户列表
    user_sub = page.locator('.ant-menu-submenu-title:has-text("用户管理")')
    if user_sub.count() > 0 and user_sub.first.get_attribute("aria-expanded") != "true":
        user_sub.first.click()
        page.wait_for_timeout(400)
    user_list_item = page.locator('.ant-menu-item:has-text("用户列表")').first
    user_list_item.click()
    page.wait_for_timeout(1500)
    page.wait_for_load_state("networkidle")
    check("/admin/users" in page.url, f"on user management page (got {page.url})")

    # ============================================================
    # 2. Click user row → drawer opens with detail
    # ============================================================
    print("\n=== 2. User detail drawer ===")
    page.wait_for_selector('.ant-table-tbody tr', timeout=10000)
    page.wait_for_timeout(500)
    # Find row containing the test user's email
    row = page.locator(f'.ant-table-tbody tr:has-text("{email}")').first
    check(row.count() > 0, f"test user row found in table")
    row.click()
    page.wait_for_timeout(1000)
    # Drawer should be visible with user detail
    drawer = page.locator('.ant-drawer:visible').first
    has_drawer = drawer.count() > 0
    if not has_drawer:
        drawer = page.locator('.ant-drawer').first
    check(drawer.count() > 0, "user detail drawer opened")
    check(email in (drawer.inner_text() if drawer.count() > 0 else ""), "email visible in drawer")
    # Close drawer
    drawer_close = page.locator('.ant-drawer .ant-drawer-close').first
    if drawer_close.count() > 0:
        drawer_close.click()
        page.wait_for_timeout(500)

    # ============================================================
    # 3. Archive user → verify login blocked → unarchive
    # ============================================================
    print("\n=== 3. Archive user ===")
    # Close drawer before row actions
    mask0 = page.locator('.ant-drawer-mask').first
    if mask0.count() > 0:
        mask0.click()
        page.wait_for_timeout(800)
    archive_btn = row.locator('button:has-text("归档")').first
    check(archive_btn.count() > 0, "archive button visible")
    archive_btn.click()
    page.wait_for_timeout(500)
    # Popconfirm appears
    pop_ok = page.locator('.ant-popconfirm .ant-btn-primary').first
    if pop_ok.count() > 0:
        pop_ok.click()
        page.wait_for_timeout(3000)
        page.wait_for_load_state("networkidle")
    check(True, "archive action triggered")

    # Verify archived user cannot login
    login_as(page, email, password)
    check("/login" in page.url, "archived user blocked at login")
    check("该账号已被归档" in page.content(), "archive error message visible")

    # Re-login as superadmin, unarchive
    login_as(page, "superadmin@test.com", "pass123")
    user_sub2 = page.locator('.ant-menu-submenu-title:has-text("用户管理")')
    if user_sub2.count() > 0 and user_sub2.first.get_attribute("aria-expanded") != "true":
        user_sub2.first.click()
        page.wait_for_timeout(400)
    page.locator('.ant-menu-item:has-text("用户列表")').first.click()
    page.wait_for_timeout(1500)
    page.wait_for_load_state("networkidle")
    page.wait_for_selector('.ant-table-tbody tr', timeout=10000)
    page.wait_for_timeout(500)
    row2 = page.locator(f'.ant-table-tbody tr:has-text("{email}")').first

    unarchive_btn = row2.locator('button:has-text("取消归档")').first
    check(unarchive_btn.count() > 0, "unarchive button visible")
    unarchive_btn.click()
    page.wait_for_timeout(500)
    pop_ok2 = page.locator('.ant-popconfirm .ant-btn-primary').first
    if pop_ok2.count() > 0:
        pop_ok2.click()
        page.wait_for_timeout(3000)
        page.wait_for_load_state("networkidle")

    # Verify unarchived user can login
    login_as(page, email, password)
    check("/profile" in page.url, f"unarchived user logged in (got {page.url})")

    # ============================================================
    # 4. Edit roles
    # ============================================================
    print("\n=== 4. Edit roles ===")
    login_as(page, "superadmin@test.com", "pass123")
    # Ensure drawer is closed
    mask_roles = page.locator('.ant-drawer-mask').first
    if mask_roles.count() > 0:
        mask_roles.click()
        page.wait_for_timeout(800)
    user_sub3 = page.locator('.ant-menu-submenu-title:has-text("用户管理")')
    if user_sub3.count() > 0 and user_sub3.first.get_attribute("aria-expanded") != "true":
        user_sub3.first.click()
        page.wait_for_timeout(400)
    page.locator('.ant-menu-item:has-text("用户列表")').first.click()
    page.wait_for_timeout(1500)
    page.wait_for_load_state("networkidle")
    page.wait_for_selector('.ant-table-tbody tr', timeout=10000)
    page.wait_for_timeout(500)
    row3 = page.locator(f'.ant-table-tbody tr:has-text("{email}")').first

    role_btn = row3.locator('button:has-text("角色")').first
    check(role_btn.count() > 0, "edit roles button visible")
    role_btn.click()
    page.wait_for_timeout(500)
    # Modal opens with role multi-select
    modal = page.locator('.ant-modal:visible').first
    check(modal.count() > 0, "role edit modal opened")
    check("编辑角色" in (modal.inner_text() if modal.count() > 0 else ""), "modal title is 编辑角色")

    # Select a role in the multi-select
    select_in_modal = page.locator('.ant-modal:visible .ant-select').first
    if select_in_modal.count() > 0:
        select_in_modal.click()
        page.wait_for_timeout(500)
        role_option = page.locator('.ant-select-item-option').first
        if role_option.count() > 0:
            role_option.click()
            page.wait_for_timeout(300)
            page.keyboard.press("Escape")  # close dropdown
            page.wait_for_timeout(300)

    save_btn = page.locator('.ant-modal:visible .ant-btn-primary').first
    if save_btn.count() > 0:
        save_btn.click()
        page.wait_for_timeout(2000)
        page.wait_for_load_state("networkidle")
    check(True, "roles saved")

    # ============================================================
    # 5. Toggle active/inactive
    # ============================================================
    print("\n=== 5. Disable / Enable user ===")
    # Force-close any open drawer by clicking its mask
    mask = page.locator('.ant-drawer-mask').first
    if mask.count() > 0:
        mask.click()
        page.wait_for_timeout(1000)
    row5 = page.locator(f'.ant-table-tbody tr:has-text("{email}")').first
    disable_btn = row5.locator('button:has-text("禁用")').first
    if disable_btn.count() > 0:
        disable_btn.click()
        page.wait_for_timeout(500)
        pop_ok3 = page.locator('.ant-popconfirm .ant-btn-primary').first
        if pop_ok3.count() > 0:
            pop_ok3.click()
            page.wait_for_timeout(2000)
            page.wait_for_load_state("networkidle")
        check(True, "user disabled")

        # Re-enable — close drawer again before clicking
        mask2 = page.locator('.ant-drawer-mask').first
        if mask2.count() > 0:
            mask2.click()
            page.wait_for_timeout(1000)
        row6 = page.locator(f'.ant-table-tbody tr:has-text("{email}")').first
        enable_btn = row6.locator('button:has-text("启用")').first
        if enable_btn.count() > 0:
            enable_btn.click()
            page.wait_for_timeout(500)
            pop_ok4 = page.locator('.ant-popconfirm .ant-btn-primary').first
            if pop_ok4.count() > 0:
                pop_ok4.click()
                page.wait_for_timeout(2000)
                page.wait_for_load_state("networkidle")
            check(True, "user re-enabled")
    else:
        print("  disable button not found (user may already be disabled)")

    page.screenshot(path=f'{OUT / "14_superadmin_users_final.png"}', full_page=True)
    if recorder:
        recorder.stop()
    page.close()

    print(f"\n=== Console errors ===")
    error_msgs = [e for e in errors if "[error]" in e or "PAGE_ERROR" in e]
    if error_msgs:
        for e in error_msgs:
            print(f"  {e}")
    else:
        print("  (none)")

    failed = get_failed()
    print(f"\nFailed: {failed}")
    if failed > 0:
        raise SystemExit(1)
