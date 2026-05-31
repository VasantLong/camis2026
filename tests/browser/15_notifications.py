"""通知中心：铃铛 badge，下拉面板，自动标记已读。"""
from pathlib import Path
import json, uuid, urllib.request
from playwright.sync_api import sync_playwright
from utils import CDP, BASE, create_page, setup_logging, start_recording

API = "http://localhost:8000"
OUT = Path(__file__).parent / "screenshots"
failed = 0

def check(cond, msg):
    global failed
    if cond: print(f"  OK: {msg}")
    else: failed += 1; print(f"  FAIL: {msg}")

def api_post(path, body, token):
    data = json.dumps(body).encode()
    hdrs = {"Content-Type": "application/json"}
    if token: hdrs["Authorization"] = f"Bearer {token}"
    req = urllib.request.Request(f"{API}{path}", data=data, headers=hdrs)
    return json.loads(urllib.request.urlopen(req).read())

def api_get(path, token):
    req = urllib.request.Request(f"{API}{path}",
        headers={"Authorization": f"Bearer {token}"})
    return json.loads(urllib.request.urlopen(req).read())

def login_api(email, password):
    resp = api_post("/auth/login", {"email": email, "password": password}, None)
    return resp["access_token"], resp.get("user_id")

def login_as(page, email, password):
    page.goto(f"{BASE}/login")
    page.wait_for_load_state("networkidle")
    page.fill('input[placeholder="邮箱"]', email)
    page.fill('input[type="password"]', password)
    page.click('button[type="submit"]')
    page.wait_for_timeout(3000)
    page.wait_for_load_state("networkidle")

def api_put(path, body, token):
    data = json.dumps(body).encode()
    req = urllib.request.Request(f"{API}{path}", data=data, method="PUT",
        headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"})
    return json.loads(urllib.request.urlopen(req).read())


# --- Trigger notification: create activity, transition → security officer gets notified ---
p_token, _ = login_api("promoter@test.com", "pass123")
sa_token, _ = login_api("superadmin@test.com", "pass123")
uname = f"notify_{uuid.uuid4().hex[:6]}"
aid = api_post("/activities", {
    "name": uname, "type": "大型活动",
    "estimated_time": "2026-07-15T09:00:00+08:00",
    "location": f"通知测试广场_{uname}", "sponsor": "测试主办方",
    "sponsor_contact": "张三", "sponsor_phone": "13800138000",
    "deadline": "2026-07-01T18:00:00+08:00",
    "designer_id": api_get("/auth/me", p_token)["id"],
}, p_token)["id"]

# SuperAdmin transitions → triggers notify_role("SecurityOfficer", ...)
api_put(f"/activities/{aid}/status", {"to_status": "待安保方案设计"}, sa_token)
print(f"API: activity {uname} → 待安保方案设计, notification sent to SecurityOfficer")

with sync_playwright() as p:
    browser = p.chromium.connect_over_cdp(CDP)
    page = create_page(browser)
    setup_logging("15_notifications")
    recorder = start_recording(page, "15_notifications")
    page.context.clear_cookies()

    errors = []
    page.on("console", lambda m: errors.append(f"[{m.type}] {m.text}"))
    page.on("pageerror", lambda e: errors.append(f"PAGE_ERROR: {e}"))

    # === Step 1: SecurityOfficer logs in, sees badge ===
    print("\n1. SecurityOfficer sees notification badge")
    login_as(page, "security@test.com", "pass123")
    check("/login" not in page.url, "security logged in")

    badge = page.locator('.ant-badge-count, .ant-scroll-number')
    badge_count = badge.count()
    check(badge_count > 0, "notification badge visible")

    # === Step 2: Click bell, dropdown opens ===
    print("\n2. Click bell opens dropdown")
    bell = page.locator('button[aria-label="通知"]')
    if bell.count() > 0:
        bell.first.click()
        page.wait_for_timeout(800)
    dropdown = page.locator('.ant-dropdown-menu').first
    check(dropdown.count() > 0 or "暂无通知" in page.content(), "dropdown or empty state visible")

    # === Step 3: Badge cleared after opening ===
    print("\n3. Badge cleared after opening dropdown")
    page.wait_for_timeout(1000)
    badge_after = page.locator('.ant-badge-count, .ant-scroll-number').count()
    check(badge_after == 0, "badge cleared after opening")

    # === Step 4: Click notification item navigates to activity detail ===
    print("\n4. Click notification navigates to activity detail")
    # Re-open the bell dropdown
    bell2 = page.locator('button[aria-label="通知"]')
    if bell2.count() > 0:
        bell2.first.click()
        page.wait_for_timeout(800)
    # Click the notification item that references the activity
    item = page.locator(f'.ant-dropdown-menu-item:has-text("{uname}")').first
    if item.count() > 0:
        item.click()
        page.wait_for_timeout(2000)
        page.wait_for_load_state("networkidle")
    check(f"/activities/{aid}" in page.url, f"navigated to activity detail (got {page.url})")
    check(uname in page.content(), "activity name visible on detail page")
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

    print(f"\nFailed: {failed}")
    if failed > 0:
        raise SystemExit(1)
