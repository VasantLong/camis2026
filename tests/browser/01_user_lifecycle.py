"""User lifecycle: login, register, role request, email verification, email change, phone edit — all basic user operations in one script."""
from pathlib import Path
import uuid, json, re, urllib.request
from playwright.sync_api import sync_playwright
from utils import (CDP, BASE, API, create_page, setup_logging, start_recording,
                   check, get_failed, login_as)

MAILPIT = "http://localhost:18025/api/v1"
OUT = Path(__file__).parent / "screenshots"


def mailpit_find(subject_contains: str) -> dict | None:
    msgs = json.loads(urllib.request.urlopen(
        urllib.request.Request(f"{MAILPIT}/messages")
    ).read()).get("messages", [])
    for m in msgs:
        detail = json.loads(urllib.request.urlopen(
            urllib.request.Request(f"{MAILPIT}/message/{m['ID']}")
        ).read())
        if subject_contains in (detail.get("Subject") or ""):
            return detail
    return None


with sync_playwright() as p:
    browser = p.chromium.connect_over_cdp(CDP)
    page = create_page(browser)
    setup_logging("01_user_lifecycle")
    recorder = start_recording(page, "01_user_lifecycle")

    errors = []
    page.on("console", lambda m: errors.append(f"[{m.type}] {m.text}"))
    page.on("pageerror", lambda e: errors.append(f"PAGE_ERROR: {e}"))

    # ============================================================
    # 1. Wrong password → error toast
    # ============================================================
    print("\n=== 1. Wrong password ===")
    page.goto(f"{BASE}/login")
    page.wait_for_load_state("networkidle")
    page.fill('input[placeholder="邮箱"]', "devtest@test.com")
    page.fill('input[type="password"]', "wrongpassword")
    page.click('button[type="submit"]')
    page.wait_for_timeout(2000)
    check("/login" in page.url, f"stayed on /login after wrong password (got {page.url})")
    toast = page.locator('.ant-message').filter(has_text="邮箱或密码错误").first
    check(toast.count() > 0, "error toast visible after wrong password")

    # ============================================================
    # 2. Wrong username → error toast
    # ============================================================
    print("\n=== 2. Wrong username ===")
    page.context.clear_cookies()
    page.goto(f"{BASE}/login")
    page.wait_for_load_state("networkidle")
    page.fill('input[placeholder="邮箱"]', "nonexistent@test.com")
    page.fill('input[type="password"]', "pass123")
    page.click('button[type="submit"]')
    page.wait_for_timeout(2000)
    check("/login" in page.url, f"stayed on /login after wrong username (got {page.url})")
    toast2 = page.locator('.ant-message').filter(has_text="邮箱或密码错误").first
    check(toast2.count() > 0, "error toast visible after wrong username")

    # ============================================================
    # 3. Correct login → sidebar visible → logout
    # ============================================================
    print("\n=== 3. Correct login + logout ===")
    login_as(page, "promoter@test.com", "pass123")
    check("/login" not in page.url, "logged in")
    sidebar = page.locator('.ant-layout-sider')
    check(sidebar.count() > 0, "sidebar visible after login")

    # Logout via header user dropdown
    user_btn = page.locator('header button:has(.anticon-user)').first
    if user_btn.count() > 0:
        user_btn.click()
        page.wait_for_timeout(500)
        logout_item = page.locator('.ant-dropdown-menu-item:has-text("退出登录")').first
        if logout_item.count() > 0:
            logout_item.click()
            page.wait_for_timeout(2000)
            page.wait_for_load_state("networkidle")
            check("/login" in page.url, f"redirected to /login after logout (got {page.url})")

    # ============================================================
    # 4. Register new user → /profile → check welcome email
    # ============================================================
    print("\n=== 4. Register + welcome email ===")
    suffix = uuid.uuid4().hex[:6]
    email = f"ul_{suffix}@test.com"
    display_name = f"ul_{suffix}"

    # Count existing Mailpit messages
    before_msgs = json.loads(urllib.request.urlopen(
        urllib.request.Request(f"{MAILPIT}/messages")
    ).read()).get("messages", [])
    before_count = len(before_msgs)

    page.goto(f"{BASE}/register")
    page.wait_for_load_state("networkidle")
    page.fill('input[placeholder="邮箱"]', email)
    page.fill('input[type="password"]', "pass123")
    page.fill('input[placeholder="显示名称"]', display_name)
    page.click('button[type="submit"]')
    page.wait_for_timeout(3000)
    page.wait_for_load_state("networkidle")
    check("/profile" in page.url, f"registered, landed on /profile (got {page.url})")

    # Check Mailpit for welcome email
    page.wait_for_timeout(1000)
    after_msgs = json.loads(urllib.request.urlopen(
        urllib.request.Request(f"{MAILPIT}/messages")
    ).read()).get("messages", [])
    check(len(after_msgs) > before_count, f"new email captured ({before_count}→{len(after_msgs)})")
    # Verify subject
    for msg in sorted(after_msgs, key=lambda m: m.get("Created", ""), reverse=True):
        if email in str(msg.get("To", [])):
            detail = json.loads(urllib.request.urlopen(
                urllib.request.Request(f"{MAILPIT}/message/{msg['ID']}")
            ).read())
            check("欢迎注册 CAMIS" in detail.get("Subject", ""),
                  f"welcome email subject ok (got '{detail.get('Subject', '')}')")
            break

    # ============================================================
    # 5. Role request: no-role alert → select role → submit → pending
    # ============================================================
    print("\n=== 5. Role request ===")
    no_role_alert = page.locator('.ant-alert').filter(has_text="尚未分配角色").first
    check(no_role_alert.count() > 0, "'尚未分配角色' alert visible")

    select_trigger = page.locator('.ant-select').first
    select_trigger.click()
    page.wait_for_timeout(500)
    option = page.locator('.ant-select-item-option').first
    option.click()
    page.wait_for_timeout(300)

    submit_btn = page.locator('button:has-text("提交申请")').first
    check(not submit_btn.is_disabled(), "submit button enabled after selecting role")
    submit_btn.click()
    page.wait_for_timeout(3000)
    page.wait_for_load_state("networkidle")

    pending_alert = page.locator('.ant-alert').filter(has_text="等待审核").first
    check(pending_alert.count() > 0, "'等待审核' alert visible")
    check(page.locator('button:has-text("提交申请")').count() == 0, "submit button gone")

    # ============================================================
    # 6. Edit email → verify → login with new email
    # ============================================================
    print("\n=== 6. Email change ===")
    new_email = f"ul_{suffix}_new@test.com"

    email_display = page.get_by_text(email).first
    check(email_display.count() > 0, f"email '{email}' displayed")
    email_display.click()
    page.wait_for_timeout(300)

    email_input = page.locator('input:not([readonly]):not([type="search"])').last
    email_input.fill(new_email)
    page.wait_for_timeout(200)
    email_input.press("Enter")
    page.wait_for_timeout(3000)
    page.wait_for_load_state("networkidle")

    toast3 = page.locator('.ant-message').filter(has_text="验证邮件已发送").first
    check(toast3.count() > 0, "verification email sent toast")

    # Find verification link in Mailpit
    verify = None
    for _ in range(5):
        page.wait_for_timeout(800)
        verify = mailpit_find("验证您的 CAMIS 邮箱")
        if verify:
            break
    check(verify is not None, "verification email found in Mailpit")
    html = verify.get("HTML", "") if verify else ""
    match = re.search(r'http://localhost:8000/auth/verify-email\?token=[^\s"\'<>]+', html)
    check(match is not None, "verification link in email")
    verify_url = match.group() if match else ""

    # Click verification link
    page.goto(verify_url)
    page.wait_for_timeout(5000)
    page.wait_for_load_state("networkidle")
    check("/login" in page.url and "verified=1" in page.url,
          f"verified, redirect to /login?verified=1 (got {page.url})")

    # Login with new email
    login_as(page, new_email, "pass123")
    check("/login" not in page.url, f"login with new email successful (got {page.url})")

    # ============================================================
    # 7. Edit contact phone on profile
    # ============================================================
    print("\n=== 7. Edit contact phone ===")
    phone_link = page.get_by_text("点击添加").first
    if phone_link.count() == 0:
        phone_link = page.locator('.ant-descriptions-item:has-text("联系方式") .ant-typography').first
    if phone_link.count() > 0:
        phone_link.click()
        page.wait_for_timeout(300)
        phone_input = page.locator('input[placeholder*="138"]').first
        if phone_input.count() == 0:
            phone_input = page.locator('input:not([readonly]):not([type="search"])').last
        if phone_input.count() > 0:
            phone_input.fill("13912345678")
            page.wait_for_timeout(200)
            phone_input.press("Enter")
            page.wait_for_timeout(2000)
    check("13912345678" in page.content(), "phone number updated in display")

    # ============================================================
    # 8. Old session kick after email change
    # ============================================================
    print("\n=== 8. Session kick after email change (API) ===")
    brow_resp = json.loads(urllib.request.urlopen(urllib.request.Request(
        f"{API}/auth/login", json.dumps({"email": new_email, "password": "pass123"}).encode(),
        headers={"Content-Type": "application/json"})).read())
    brow_token = brow_resp["access_token"]
    another_email = f"{uuid.uuid4().hex}@test.com"
    change_req = urllib.request.Request(
        f"{API}/auth/me/email-change",
        json.dumps({"new_email": another_email}).encode(),
        headers={"Authorization": f"Bearer {brow_token}", "Content-Type": "application/json"},
    )
    change_resp = urllib.request.urlopen(change_req)
    check(change_resp.status == 202, f"email change request accepted (status={change_resp.status})")

    # Find verification token and verify
    vtoken = None
    for _ in range(5):
        mail_resp = json.loads(urllib.request.urlopen(
            urllib.request.Request(f"{MAILPIT}/messages")
        ).read())
        msgs = sorted(mail_resp.get("messages", []), key=lambda m: m.get("Created", ""), reverse=True)
        for m in msgs:
            detail = json.loads(urllib.request.urlopen(
                urllib.request.Request(f"{MAILPIT}/message/{m['ID']}")
            ).read())
            to_list = [a.get("Address", "") for a in detail.get("To", [])]
            if another_email not in to_list:
                continue
            body = detail.get("HTML") or detail.get("Text") or ""
            m2 = re.search(r'verify-email\?token=([^"\s<>]+)', body)
            if m2:
                vtoken = m2.group(1)
                break
        if vtoken:
            break
        import time
        time.sleep(1)
    check(vtoken is not None, "second verification token found")
    urllib.request.urlopen(urllib.request.Request(f"{API}/auth/verify-email?token={vtoken}"))

    # Old session should be kicked
    page.goto(f"{BASE}/activities")
    page.wait_for_timeout(3000)
    page.wait_for_load_state("networkidle")
    check("/login" in page.url, f"old session kicked to /login (got {page.url})")

    # ============================================================
    # 9. Old email blocked from login
    # ============================================================
    print("\n=== 9. Old email blocked ===")
    login_as(page, email, "pass123")
    check("/login" in page.url, "old email login blocked, stayed on /login")
    old_toast = page.locator('.ant-message').filter(has_text="邮箱或密码错误").first
    check(old_toast.count() > 0, "old email error toast visible")

    page.screenshot(path=f'{OUT / "01_user_lifecycle_final.png"}', full_page=True)
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
