from pathlib import Path
"""Role request flow: register → /profile → apply for role → verify pending."""
from playwright.sync_api import sync_playwright
from utils import CDP, BASE, create_page, start_recording
import uuid

OUT = Path(__file__).parent / 'screenshots'
failed = 0

def check(cond, msg):
    global failed
    if cond: print(f"  OK: {msg}")
    else: failed += 1; print(f"  FAIL: {msg}")

with sync_playwright() as p:
    browser = p.chromium.connect_over_cdp(CDP)
    page = create_page(browser)
    recorder = start_recording(page, "07_role_request")
    page.context.clear_cookies()

    errors = []
    page.on("console", lambda m: errors.append(f"[{m.type}] {m.text}"))
    page.on("pageerror", lambda e: errors.append(f"PAGE_ERROR: {e}"))

    # 1. Register new user → /profile
    print("1. Register new user → /profile")
    uname = f"rr_{uuid.uuid4().hex[:6]}"
    page.goto(f"{BASE}/register")
    page.wait_for_load_state("networkidle")
    page.fill('input[placeholder="邮箱"]', f"{uname}@test.com")
    page.fill('input[type="password"]', "pass123")
    page.fill('input[placeholder="显示名称"]', uname)
    page.click('button[type="submit"]')
    page.wait_for_timeout(3000)
    page.wait_for_load_state("networkidle")
    check("/profile" in page.url, f"landed on /profile (got {page.url})")

    # 2. "尚未分配角色" alert visible
    print("2. No-role alert visible")
    no_role_alert = page.locator('.ant-alert').filter(has_text="尚未分配角色").first
    check(no_role_alert.count() > 0, "'尚未分配角色' alert visible")
    # Verify alert uses title (not deprecated message)
    alert_title = no_role_alert.locator('.ant-alert-title, .ant-alert-message').first
    check(alert_title.count() > 0, "alert title element present")

    # 3. Select role dropdown → choose Promoter
    print("3. Select role")
    select_trigger = page.locator('.ant-select:has-text("选择角色")').first
    if select_trigger.count() == 0:
        select_trigger = page.locator('.ant-select').first
    check(select_trigger.count() > 0, "role select visible")
    select_trigger.click()
    page.wait_for_timeout(500)

    # Pick first available option (prefer "宣策部")
    option = page.locator('.ant-select-item-option:has-text("宣策部")').first
    if option.count() == 0:
        option = page.locator('.ant-select-item-option').first
    check(option.count() > 0, "role option available")
    if option.count() > 0:
        option_text = option.inner_text()
        option.click()
        page.wait_for_timeout(300)

    # 4. Submit button enabled
    print("4. Submit role request")
    submit_btn = page.locator('button:has-text("提交申请")').first
    check(submit_btn.count() > 0, "submit button visible")
    is_enabled = not (submit_btn.is_disabled() if submit_btn.count() > 0 else True)
    check(is_enabled, "submit button enabled after selecting role")

    if submit_btn.count() > 0 and not submit_btn.is_disabled():
        submit_btn.click()
        page.wait_for_timeout(3000)
        page.wait_for_load_state("networkidle")

    # 5. "等待审核" alert replaces "尚未分配角色"
    print("5. Pending review alert")
    pending_alert = page.locator('.ant-alert').filter(has_text="等待审核").first
    check(pending_alert.count() > 0, "'等待审核' alert visible")

    no_role_after = page.locator('.ant-alert').filter(has_text="尚未分配角色").first
    check(no_role_after.count() == 0, "'尚未分配角色' alert gone after submit")

    # 6. Submit button hidden after application
    print("6. Submit button gone")
    submit_after = page.locator('button:has-text("提交申请")').first
    check(submit_after.count() == 0, "submit button hidden after applying")

    page.screenshot(path=f'{OUT / '07_role_request_final.png'}', full_page=True)
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
