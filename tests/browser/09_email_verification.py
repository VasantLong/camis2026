from pathlib import Path
"""Email verification: register → check Mailpit captured welcome email."""
import uuid, json, urllib.request
from playwright.sync_api import sync_playwright

CDP = "http://127.0.0.1:9222"
BASE = "http://localhost:5173"
MAILPIT_API = "http://localhost:8025/api/v1"
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
    page.context.clear_cookies()

    errors = []
    page.on("console", lambda m: errors.append(f"[{m.type}] {m.text}"))
    page.on("pageerror", lambda e: errors.append(f"PAGE_ERROR: {e}"))

    # 1. Check Mailpit is running
    print("1. Mailpit health check")
    try:
        req = urllib.request.Request(f"{MAILPIT_API}/messages")
        resp = urllib.request.urlopen(req)
        check(resp.status == 200, f"Mailpit API reachable (HTTP {resp.status})")
    except Exception as e:
        check(False, f"Mailpit not reachable: {e}")
        raise SystemExit(1)

    # Count existing messages before registration
    before_count = len(json.loads(urllib.request.urlopen(
        urllib.request.Request(f"{MAILPIT_API}/messages")
    ).read()).get("messages", []))

    # 2. Register a new user via frontend
    print("2. Register new user")
    uname = f"email_{uuid.uuid4().hex[:6]}"
    email_addr = f"{uname}@test.com"
    page.goto(f"{BASE}/register")
    page.wait_for_load_state("networkidle")
    page.fill('input[placeholder="邮箱"]', email_addr)
    page.fill('input[type="password"]', "pass123")
    page.fill('input[placeholder="显示名称"]', uname)
    page.click('button[type="submit"]')
    page.wait_for_timeout(3000)
    page.wait_for_load_state("networkidle")
    check("/profile" in page.url, f"registered and landed on /profile (got {page.url})")

    # 3. Check Mailpit captured the welcome email
    print("3. Check welcome email in Mailpit")
    page.wait_for_timeout(1000)  # give background task time to send

    all_msgs = json.loads(urllib.request.urlopen(
        urllib.request.Request(f"{MAILPIT_API}/messages")
    ).read()).get("messages", [])
    after_count = len(all_msgs)
    check(after_count > before_count,
          f"new email captured (before={before_count}, after={after_count})")

    # 4. Verify email content
    print("4. Verify email content")
    welcome_found = False
    for msg in all_msgs:
        if email_addr in str(msg.get("To", [])) or email_addr in str(msg.get("To", "")):
            msg_id = msg["ID"]
            detail = json.loads(urllib.request.urlopen(
                urllib.request.Request(f"{MAILPIT_API}/message/{msg_id}")
            ).read())
            subject = detail.get("Subject", "")
            html = detail.get("HTML", "")
            check("欢迎注册 CAMIS" in subject, f"subject is '欢迎注册 CAMIS' (got '{subject}')")
            check(uname in html, f"display name '{uname}' in email body")
            welcome_found = True
            break

    if not welcome_found and after_count > before_count:
        # Just check the latest message
        latest_id = all_msgs[0].get("ID")
        if latest_id:
            detail = json.loads(urllib.request.urlopen(
                urllib.request.Request(f"{MAILPIT_API}/message/{latest_id}")
            ).read())
            subject = detail.get("Subject", "")
            check("欢迎" in subject or "CAMIS" in subject,
                  f"latest email subject contains CAMIS (got '{subject}')")

    page.screenshot(path=f'{OUT / '09_email_final.png'}', full_page=True)
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
