"""Workflow + Filing: state transitions via browser UI, data via API."""
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

# --- API helpers ---
def api_post(path, body, token):
    data = json.dumps(body).encode()
    req = urllib.request.Request(f"{API}{path}", data=data,
        headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"})
    return json.loads(urllib.request.urlopen(req).read())

def login_api():
    return api_post("/auth/login", {"email":"tester1@test.com","password":"pass123"}, None)["access_token"]

def create_activity_via_api(token, name):
    return api_post("/activities", {
        "name": name, "type": "大型活动",
        "estimated_time": "2026-06-15T09:00:00+08:00",
        "location": "测试广场", "sponsor": "测试主办方",
        "deadline": "2026-06-01T18:00:00+08:00",
        "designer_id": "c5e9d024-8b3f-4c05-99d9-13d74bcd6cbb"
    }, token)["id"]

token = login_api()

def sidebar_nav(page, text):
    sub = page.locator('.ant-menu-submenu-title:has-text("活动管理")')
    if sub.count() > 0 and sub.first.get_attribute("aria-expanded") != "true":
        sub.first.click()
        page.wait_for_timeout(400)
    it = page.locator(f'.ant-menu-item:has-text("{text}")').first
    if it.count() > 0:
        it.click()
        page.wait_for_timeout(1500)
        page.wait_for_load_state("networkidle")

with sync_playwright() as p:
    browser = p.chromium.connect_over_cdp(CDP)
    page = create_page(browser)
    setup_logging("03_workflow")
    recorder = start_recording(page, "03_workflow")
    page.context.clear_cookies()

    errors = []
    page.on("console", lambda m: errors.append(f"[{m.type}] {m.text}"))
    page.on("pageerror", lambda e: errors.append(f"PAGE_ERROR: {e}"))

    # Login
    page.goto(f"{BASE}/login")
    page.wait_for_load_state("networkidle")
    page.fill('input[placeholder="邮箱"]', "tester1@test.com")
    page.fill('input[type="password"]', "pass123")
    page.click('button[type="submit"]')
    page.wait_for_timeout(3000)
    page.wait_for_load_state("networkidle")
    check("/activities" in page.url, "logged in")

    # 1. Create activity for workflow testing via API
    print("\n1. Create activity (API)")
    aid = create_activity_via_api(token, f"wf_{uuid.uuid4().hex[:6]}")
    print(f"  created: {aid[:8]}...")

    # Navigate to detail via list click (client-side, avoids auth loss)
    sidebar_nav(page, "全部活动")
    page.wait_for_timeout(1000)
    # Click the activity name link in the table
    link = page.locator('td a').first  # first link in the table
    if link.count() > 0:
        link.click()
        page.wait_for_timeout(2000)
        page.wait_for_load_state("networkidle")
    check("/activities/" in page.url, f"on detail page (got {page.url})")
    check("待设计方案" in page.content(), "activity in 待设计方案 status")

    # 2. Transition: 待设计方案 → 待安保方案设计
    print("\n2. Transition to 待安保方案设计")
    btn = page.locator('button:has-text("提交到安保方案设计")').first
    if btn.count() > 0:
        btn.click()
        page.wait_for_timeout(800)
        txt = page.locator('.ant-modal:visible textarea').first
        if txt.count() > 0: txt.fill("提交安保方案")
        ok = page.locator('.ant-modal:visible .ant-btn-primary').first
        if ok.count() > 0: ok.click()
        page.wait_for_timeout(3000)
        page.wait_for_load_state("networkidle")
    check("待安保方案设计" in page.content(), "status → 待安保方案设计")

    # 3. Reject (loop)
    print("\n3. Reject (loop)")
    rej = page.locator('button:has-text("驳回")').first
    if rej.count() > 0:
        rej.click()
        page.wait_for_timeout(800)
        txt = page.locator('.ant-modal:visible textarea').first
        if txt.count() > 0: txt.fill("材料需要补充")
        ok = page.locator('.ant-modal:visible .ant-btn-primary').first
        if ok.count() > 0: ok.click()
        page.wait_for_timeout(3000)
        page.wait_for_load_state("networkidle")
    check("待安保方案设计" in page.content(), "status unchanged after loop reject")

    # 4. Sign complete → 待备案申请
    print("\n4. Sign complete")
    sign = page.locator('button:has-text("签署完成")').first
    if sign.count() > 0:
        sign.click()
        page.wait_for_timeout(800)
        txt = page.locator('.ant-modal:visible textarea').first
        if txt.count() > 0: txt.fill("材料已签署")
        ok = page.locator('.ant-modal-footer button.ant-btn-primary').first
        if ok.count() > 0: ok.click()
        page.wait_for_timeout(3000)
        page.wait_for_load_state("networkidle")
    check("待备案申请" in page.content(), "status → 待备案申请")

    # 5. Force cancel on a new activity
    print("\n5. Force cancel")
    aid2 = create_activity_via_api(token, f"wf_cancel_{uuid.uuid4().hex[:4]}")
    # Navigate via list
    sidebar_nav(page, "全部活动")
    page.wait_for_timeout(1000)
    # Click first activity in the table
    link2 = page.locator('td a').first
    if link2.count() > 0:
        link2.click()
        page.wait_for_timeout(2000)
        page.wait_for_load_state("networkidle")
    cancel = page.locator('button:has-text("强制取消")').first
    if cancel.count() > 0:
        cancel.click()
        page.wait_for_timeout(800)
        cb = page.locator('.ant-modal:visible .ant-checkbox').first
        if cb.count() > 0: cb.click(); page.wait_for_timeout(300)
        txt = page.locator('.ant-modal:visible textarea').first
        if txt.count() > 0: txt.fill("测试强制取消")
        ok = page.locator('.ant-modal:visible .ant-btn-primary').first
        if ok.count() > 0: ok.click()
        page.wait_for_timeout(3000)
        page.wait_for_load_state("networkidle")
        check("已取消" in page.content(), "status → 已取消")
        btns = page.locator('button:has-text("提交")').count()
        check(btns == 0, "no action buttons on terminal state")
    else:
        check(False, "force cancel button not found")

    page.screenshot(path=f"{OUT / '03_workflow_final.png'}", full_page=True)
    if recorder:
        recorder.stop()
    page.close()

    print(f"\n=== Console errors ===")
    for e in errors:
        if "[error]" in e or "PAGE_ERROR" in e:
            print(f"  {e}")

    print(f"\nFailed: {failed}")
    if failed > 0:
        raise SystemExit(1)
