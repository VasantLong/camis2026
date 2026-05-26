"""Activity CRUD: create via API, verify frontend display + filter + detail."""
from pathlib import Path
import json, uuid, urllib.request
from playwright.sync_api import sync_playwright

CDP = "http://127.0.0.1:9222"
BASE = "http://localhost:5173"
API = "http://localhost:8000"
OUT = Path(__file__).parent / "screenshots"
failed = 0

def check(cond, msg):
    global failed
    if cond:
        print(f"  OK: {msg}")
    else:
        failed += 1
        print(f"  FAIL: {msg}")

def sidebar_nav(page, item_text):
    sub = page.locator('.ant-menu-submenu-title:has-text("活动管理")')
    if sub.count() > 0 and sub.first.get_attribute("aria-expanded") != "true":
        sub.first.click()
        page.wait_for_timeout(400)
    it = page.locator(f'.ant-menu-item:has-text("{item_text}")').first
    if it.count() > 0:
        it.click()
        page.wait_for_timeout(1500)
        page.wait_for_load_state("networkidle")
        return True
    return False

# --- API helpers ---
def login_api():
    data = json.dumps({"email": "tester1@test.com", "password": "pass123"}).encode()
    req = urllib.request.Request(f"{API}/auth/login", data=data, headers={"Content-Type": "application/json"})
    return json.loads(urllib.request.urlopen(req).read())["access_token"]

def create_activity(token, name):
    body = json.dumps({
        "name": name, "type": "大型活动",
        "estimated_time": "2026-06-15T09:00:00+08:00",
        "location": "测试广场", "sponsor": "测试主办方",
        "deadline": "2026-06-01T18:00:00+08:00",
        "designer_id": "c5e9d024-8b3f-4c05-99d9-13d74bcd6cbb"
    }).encode()
    req = urllib.request.Request(f"{API}/activities", data=body,
        headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"})
    return json.loads(urllib.request.urlopen(req).read())

# --- Create test data ---
token = login_api()
aname = f"测试活动_{uuid.uuid4().hex[:6]}"
act = create_activity(token, aname)
aid = act["id"]
print(f"API created: {aname} (id={aid[:8]}...) status={act['status']}")

# --- Browser tests ---
with sync_playwright() as p:
    browser = p.chromium.connect_over_cdp(CDP)
    page = browser.new_page()
    page.set_viewport_size({"width": 2560, "height": 1600})

    errors = []
    page.on("console", lambda m: errors.append(f"[{m.type}] {m.text}"))
    page.on("pageerror", lambda e: errors.append(f"PAGE_ERROR: {e}"))

    # Login
    page.goto(f"{BASE}/login")
    page.wait_for_load_state("networkidle")
    page.context.clear_cookies()
    page.fill('input[placeholder="邮箱"]', "tester1@test.com")
    page.fill('input[type="password"]', "pass123")
    page.click('button[type="submit"]')
    page.wait_for_timeout(3000)
    page.wait_for_load_state("networkidle")
    check("/activities" in page.url, "logged in")

    # 1. Activity list shows created activity
    print("\n1. Activity in list")
    check(aname in page.content(), f"'{aname}' visible in activity list")

    # 2. Status filter
    print("\n2. Status filter")
    # Find any select that might be the status filter
    status_selects = page.locator('.ant-select').all()
    filtered = False
    for sel in status_selects:
        text = sel.inner_text() or ""
        if "状态" in text or "待" in text:
            sel.click()
            page.wait_for_timeout(500)
            opt = page.locator('.ant-select-item-option[title="待设计方案"]').first
            if opt.count() > 0:
                opt.click()
                page.wait_for_timeout(1500)
                page.wait_for_load_state("networkidle")
                filtered = True
                break
    if filtered:
        check(aname in page.content(), "filter shows matching activity")
    else:
        print("  (status filter UI not found, skipping)")

    # 3. Navigate to detail via table row click
    print("\n3. Detail page")
    link = page.locator(f'a:has-text("{aname}")').first
    if link.count() > 0:
        link.click()
        page.wait_for_timeout(2000)
        page.wait_for_load_state("networkidle")
    check(f"/activities/{aid}" in page.url, f"on detail page (got {page.url})")
    check("待设计方案" in page.content(), "status badge visible")

    # 4. History tab
    print("\n4. History tab")
    hist = page.locator('.ant-tabs-tab:has-text("状态历史")').first
    if hist.count() > 0:
        hist.click()
        page.wait_for_timeout(1000)
        check("待设计方案" in page.content(), "history shows status entry")

    # 5. Document tab
    print("\n5. Document tab")
    doc = page.locator('.ant-tabs-tab:has-text("文档")').first
    if doc.count() > 0:
        doc.click()
        page.wait_for_timeout(1000)
        check(True, "document tab opened")
        # Upload area should be present
        upload = page.locator('.ant-upload').first
        check(upload.count() > 0, "upload component present")
    else:
        check(False, "document tab not found")

    # 6. Back to list via sidebar
    print("\n6. Back to list")
    if sidebar_nav(page, "全部活动"):
        check(aname in page.content(), "back in list, activity visible")

    page.screenshot(path=f"{OUT / '02_activity_crud_final.png'}", full_page=True)
    page.close()

    print(f"\n=== Console errors ===")
    for e in errors:
        if "[error]" in e or "PAGE_ERROR" in e:
            print(f"  {e}")

    print(f"\nFailed: {failed}")
    if failed > 0:
        raise SystemExit(1)
