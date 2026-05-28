from pathlib import Path
"""Filing materials sign/audit: SecurityOfficer signs materials, GovLiaison audits.
User-perspective flow: login → sidebar nav → table click → tab → action buttons."""
from playwright.sync_api import sync_playwright
from utils import CDP, BASE, create_page, start_recording

OUT = Path(__file__).parent / "screenshots"
failed = 0

def check(cond, msg):
    global failed
    if cond: print(f"  OK: {msg}")
    else: failed += 1; print(f"  FAIL: {msg}")

def login_as(page, email, password):
    """User opens login page, fills form, clicks submit."""
    page.context.clear_cookies()
    page.goto(f"{BASE}/login")
    page.wait_for_load_state("networkidle")
    page.fill('input[placeholder="邮箱"]', email)
    page.fill('input[type="password"]', password)
    page.click('button[type="submit"]')
    page.wait_for_timeout(3000)
    page.wait_for_load_state("networkidle")

def navigate_to_activity(page, activity_name):
    """User clicks sidebar '活动管理' → '全部活动', then clicks the activity name in table.
    All client-side navigation — no full page reload."""
    # Expand sidebar "活动管理" submenu
    sub = page.locator('.ant-menu-submenu-title:has-text("活动管理")')
    if sub.count() > 0 and sub.first.get_attribute("aria-expanded") != "true":
        sub.first.click()
        page.wait_for_timeout(300)

    # Click "全部活动"
    all_activities = page.locator('.ant-menu-item:has-text("全部活动")').first
    if all_activities.count() > 0:
        all_activities.click()
        page.wait_for_timeout(500)

    # Wait for table to render with data
    page.wait_for_selector('.ant-table-tbody', timeout=10000)
    page.wait_for_timeout(500)

    # Click the activity name link in the table (client-side navigate)
    link = page.locator(f'a:has-text("{activity_name}")').first
    if link.count() > 0:
        link.click()
        page.wait_for_timeout(2000)
        page.wait_for_load_state("networkidle")
        return True
    return False

with sync_playwright() as p:
    browser = p.chromium.connect_over_cdp(CDP)
    page = create_page(browser)
    recorder = start_recording(page, "08_filing_materials")

    errors = []
    page.on("console", lambda m: errors.append(f"[{m.type}] {m.text}"))
    page.on("pageerror", lambda e: errors.append(f"PAGE_ERROR: {e}"))

    # === SecurityOfficer: Sign materials ===
    # User: security officer logs in, navigates to an activity, opens filing tab, signs materials
    print("=== SecurityOfficer: 签署材料 ===")

    # Step 1: Login
    print("1. Login as security")
    login_as(page, "security@test.com", "pass123")
    check("/login" not in page.url, f"security logged in (got {page.url})")

    # Step 2: Navigate to activity list, find and click a gov_test activity
    print("2. Navigate to activity via sidebar + table")
    # We need an activity name — get it from the table after navigation
    # First, go to activity list
    sub = page.locator('.ant-menu-submenu-title:has-text("活动管理")')
    if sub.count() > 0 and sub.first.get_attribute("aria-expanded") != "true":
        sub.first.click()
        page.wait_for_timeout(300)
    all_act = page.locator('.ant-menu-item:has-text("全部活动")').first
    if all_act.count() > 0:
        all_act.click()
        page.wait_for_timeout(500)

    # Wait for table
    page.wait_for_selector('.ant-table-tbody', timeout=10000)
    page.wait_for_timeout(500)

    # Find a gov_test_ activity link
    gov_link = page.locator('.ant-table-tbody a:has-text("gov_test_")').first
    if gov_link.count() == 0:
        # Fallback: click any activity link in the table
        gov_link = page.locator('.ant-table-tbody a').first
    check(gov_link.count() > 0, "activity link found in table")

    activity_name = ""
    if gov_link.count() > 0:
        activity_name = (gov_link.inner_text() or "").strip()
        print(f"  activity: {activity_name}")
        gov_link.click()
        page.wait_for_timeout(2000)
        page.wait_for_load_state("networkidle")
    check("/activities/" in page.url, f"on activity detail page (got {page.url})")

    # Step 3: Click "备案" tab
    print("3. Open 备案 tab")
    filing_tab = page.locator('.ant-tabs-tab:has-text("备案")').first
    check(filing_tab.count() > 0, "备案 tab visible")
    if filing_tab.count() > 0:
        filing_tab.click()
        page.wait_for_timeout(1000)
        page.wait_for_load_state("networkidle")

    # Step 4: Sign each unsigned material
    print("4. Sign materials")
    page.wait_for_timeout(500)
    # Sign materials one by one, re-query each time (DOM updates after each click)
    remaining = page.locator('button:has-text("签署")').all()
    print(f"  materials to sign: {len(remaining)}")
    while len(remaining) > 0:
        btn = remaining[0]
        if btn.is_visible():
            btn.click()
            page.wait_for_timeout(2000)
            page.wait_for_load_state("networkidle")
        remaining = page.locator('button:has-text("签署")').all()

    unsigned_after = page.locator('button:has-text("签署")').all()
    signed_tags = page.locator('.ant-tag:has-text("已签署")').all()
    check(len(unsigned_after) == 0,
          f"all materials signed ({len(signed_tags)} signed tags)")

    # === GovLiaison: Audit materials ===
    # User: government liaison logs in, navigates to same activity, audits materials
    print("\n=== GovLiaison: 审查材料 ===")

    # Step 5: Login as liaison
    print("5. Login as liaison")
    login_as(page, "liaison@test.com", "pass123")
    check("/login" not in page.url, f"liaison logged in (got {page.url})")

    # Step 6: Navigate to same activity
    print("6. Navigate to activity")
    navigated = navigate_to_activity(page, activity_name)
    if not navigated:
        # Fallback: search in table for any gov_test
        page.wait_for_selector('.ant-table-tbody', timeout=10000)
        page.wait_for_timeout(500)
        fallback_link = page.locator('.ant-table-tbody a:has-text("gov_test_")').first
        if fallback_link.count() == 0:
            fallback_link = page.locator('.ant-table-tbody a').first
        if fallback_link.count() > 0:
            fallback_link.click()
            page.wait_for_timeout(2000)
            page.wait_for_load_state("networkidle")
    check("/activities/" in page.url, f"liaison on activity detail (got {page.url})")

    # Step 7: Open 备案 tab
    print("7. Open 备案 tab")
    filing_tab2 = page.locator('.ant-tabs-tab:has-text("备案")').first
    if filing_tab2.count() > 0:
        filing_tab2.click()
        page.wait_for_timeout(1000)
        page.wait_for_load_state("networkidle")

    # Step 8: Click "审查" on first material
    print("8. Audit material")
    page.wait_for_timeout(500)
    audit_btns = page.locator('button:has-text("审查")').all()
    check(len(audit_btns) > 0, f"audit buttons visible ({len(audit_btns)})")
    if len(audit_btns) > 0:
        audit_btns[0].click()
        page.wait_for_timeout(500)

        # Audit modal opens
        modal = page.locator('.ant-modal:visible').first
        check(modal.count() > 0, "audit modal opened")

        # Click "提交审查"
        ok_btn = page.locator('.ant-modal:visible .ant-btn-primary').first
        if ok_btn.count() > 0:
            ok_btn.click()
            page.wait_for_timeout(2000)
            page.wait_for_load_state("networkidle")

    # Step 9: Verify audit results visible
    print("9. Verify audit results")
    audit_round_tags = page.locator('.ant-tag:has-text("审核")').all()
    qualified_tags = page.locator('.ant-tag:has-text("合格")').all()
    unqualified_tags = page.locator('.ant-tag:has-text("不合格")').all()
    has_result = len(audit_round_tags) > 0 or len(qualified_tags) > 0 or len(unqualified_tags) > 0
    check(has_result,
          f"audit tags visible (rounds: {len(audit_round_tags)}, qualified: {len(qualified_tags)}, unqualified: {len(unqualified_tags)})")

    # Step 10: Check audit/sign history
    print("10. Audit history")
    history_entries = page.locator('.ant-list-item').all()
    check(len(history_entries) > 0, f"history entries visible ({len(history_entries)})")

    page.screenshot(path=f'{OUT / '08_filing_materials_final.png'}', full_page=True)
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
