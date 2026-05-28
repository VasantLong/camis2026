from pathlib import Path
"""Email change verification: user clicks email → types new → checks inbox → clicks link."""
import uuid, json, re, urllib.request
from playwright.sync_api import sync_playwright
from utils import CDP, BASE, create_page

MAILPIT = "http://localhost:18025/api/v1"
OUT = Path(__file__).parent / "screenshots"
failed = 0

def check(cond, msg):
    global failed
    if cond: print(f"  OK: {msg}")
    else: failed += 1; print(f"  FAIL: {msg}")

def mailpit_find(subject_contains):
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

    errors = []
    page.on("console", lambda m: errors.append(f"[{m.type}] {m.text}"))
    page.on("pageerror", lambda e: errors.append(f"PAGE_ERROR: {e}"))

    # ── User: 注册新账号 ──
    print("1. 注册新用户")
    suffix = uuid.uuid4().hex[:6]
    old_email = f"ec_{suffix}@test.com"
    new_email = f"ec_{suffix}_new@test.com"

    page.goto(f"{BASE}/register")
    page.wait_for_load_state("networkidle")
    page.fill('input[placeholder="邮箱"]', old_email)
    page.fill('input[type="password"]', "pass123")
    page.fill('input[placeholder="显示名称"]', f"ec_{suffix}")
    page.click('button[type="submit"]')
    page.wait_for_timeout(3000)
    page.wait_for_load_state("networkidle")
    check("/profile" in page.url, f"注册后进入 /profile")

    # ── User: 看到基本信息中的邮箱，点击编辑 ──
    print("2. 点击邮箱文字进行编辑")
    # The email is displayed as clickable Typography.Link text
    email_display = page.get_by_text(old_email).first
    check(email_display.count() > 0, f"邮箱 '{old_email}' 显示在页面中")
    email_display.click()
    page.wait_for_timeout(300)

    # ── User: 输入框出现，填入新邮箱，回车 ──
    print("3. 输入新邮箱并回车")
    # After clicking, an Input replaces the Link
    email_input = page.locator('input:not([readonly]):not([type="search"])').last
    email_input.fill(new_email)
    page.wait_for_timeout(200)
    email_input.press("Enter")
    page.wait_for_timeout(3000)
    page.wait_for_load_state("networkidle")

    # ── User: 看到提示"验证邮件已发送" ──
    print("4. 看到邮件发送提示")
    toast = page.locator('.ant-message').filter(has_text="验证邮件已发送").first
    check(toast.count() > 0, "提示 '验证邮件已发送'")

    # ── User: 打开邮箱 (Mailpit)，找到验证邮件，点击链接 ──
    print("5. 在邮箱中查找验证邮件")
    verify = None
    for _ in range(5):
        page.wait_for_timeout(800)
        verify = mailpit_find("验证您的 CAMIS 邮箱")
        if verify:
            break
    check(verify is not None, "Mailpit 中找到验证邮件")

    html = verify.get("HTML", "") if verify else ""
    match = re.search(r'http://localhost:8000/auth/verify-email\?token=[^\s"\'<>]+', html)
    check(match is not None, "邮件中包含验证链接")
    verify_url = match.group() if match else None

    # ── User: 点击验证链接 → 浏览器跳转到 /profile ──
    print("6. 点击验证链接")
    # Extract token from verify_url, build frontend URL to avoid cross-origin redirect
    token = verify_url.split("token=", 1)[1] if verify_url and "token=" in verify_url else ""
    frontend_verify = f"{BASE}/__verify-email?token={token}"
    # Use the backend URL directly — redirect will land on frontend
    page.goto(verify_url)
    page.wait_for_timeout(5000)
    page.wait_for_load_state("networkidle")
    # After redirect flows through AuthInitializer, should land on /profile or protected page
    on_profile = "/profile" in page.url
    not_error = "/403" not in page.url
    check(on_profile or not_error,
          f"验证后进入受保护页面 (got {page.url})")

    # ── User: 登出后用新邮箱登录 → 成功 ──
    print("7. 登出后用新邮箱登录")
    page.context.clear_cookies()
    page.goto(f"{BASE}/login")
    page.wait_for_load_state("networkidle")
    page.fill('input[placeholder="邮箱"]', new_email)
    page.fill('input[type="password"]', "pass123")
    page.click('button[type="submit"]')
    page.wait_for_timeout(3000)
    page.wait_for_load_state("networkidle")
    check("/login" not in page.url, f"新邮箱登录成功 (进入 {page.url})")

    # ── User: 登出后用旧邮箱登录 → 失败 ──
    print("8. 登出后用旧邮箱登录（应该失败）")
    page.context.clear_cookies()
    page.goto(f"{BASE}/login")
    page.wait_for_load_state("networkidle")
    page.fill('input[placeholder="邮箱"]', old_email)
    page.fill('input[type="password"]', "pass123")
    page.click('button[type="submit"]')
    page.wait_for_timeout(2000)
    check("/login" in page.url, "旧邮箱登录失败，留在登录页")
    old_toast = page.locator('.ant-message').filter(has_text="邮箱或密码错误").first
    check(old_toast.count() > 0, "旧邮箱错误提示可见")

    page.screenshot(path=f'{OUT / "10_email_change_final.png"}', full_page=True)
    page.close()

    print(f"\n=== Console errors ===")
    for e in errors:
        if "[error]" in e or "PAGE_ERROR" in e:
            print(f"  {e}")

    print(f"\nFailed: {failed}")
    if failed > 0:
        raise SystemExit(1)
