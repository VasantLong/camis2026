"""Workflow: state transitions with single-role users + notification checks."""
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

def login_api(email, password):
    resp = api_post("/auth/login", {"email": email, "password": password}, None)
    token = resp["access_token"]
    req = urllib.request.Request(f"{API}/auth/me", headers={"Authorization": f"Bearer {token}"})
    user = json.loads(urllib.request.urlopen(req).read())
    return token, user["id"]

# --- Browser helpers ---
def login_as(page, email, password):
    page.context.clear_cookies()
    page.goto(f"{BASE}/login")
    page.wait_for_load_state("networkidle")
    page.fill('input[placeholder="邮箱"]', email)
    page.fill('input[type="password"]', password)
    page.click('button[type="submit"]')
    page.wait_for_timeout(3000)
    page.wait_for_load_state("networkidle")

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

def find_activity_link(page, name):
    """Click activity by name in the table."""
    sidebar_nav(page, "全部活动")
    page.wait_for_timeout(1000)
    # Wait for table rows to appear
    page.wait_for_selector('.ant-table-tbody tr', timeout=5000)
    page.wait_for_timeout(500)
    link = page.locator(f'a:has-text("{name}")').first
    if link.count() > 0:
        link.click()
        page.wait_for_timeout(2000)
        page.wait_for_load_state("networkidle")
        return True
    return False

# --- Create one activity via API ---
p_token, p_user_id = login_api("promoter@test.com", "pass123")
wf_name = f"wf_{uuid.uuid4().hex[:6]}"
aid = api_post("/activities", {
    "name": wf_name, "type": "大型活动",
    "estimated_time": "2026-06-15T09:00:00+08:00",
    "location": f"测试广场_{wf_name}", "sponsor": "测试主办方",
    "sponsor_contact": "张三", "sponsor_phone": "13800138000",
    "deadline": "2026-06-01T18:00:00+08:00",
    "designer_id": p_user_id,
}, p_token)["id"]
print(f"API created: {wf_name}")

with sync_playwright() as p:
    browser = p.chromium.connect_over_cdp(CDP)
    page = create_page(browser)
    setup_logging("03_workflow")
    recorder = start_recording(page, "03_workflow")
    page.context.clear_cookies()

    errors = []
    page.on("console", lambda m: errors.append(f"[{m.type}] {m.text}"))
    page.on("pageerror", lambda e: errors.append(f"PAGE_ERROR: {e}"))

    # === Step 1: Promoter submits (only "提交到安保方案设计" button) ===
    print("\n1. Promoter: submit to 待安保方案设计")
    login_as(page, "promoter@test.com", "pass123")
    check("/login" not in page.url, "promoter logged in")
    find_activity_link(page, wf_name)
    check("/activities/" in page.url, f"on detail page (got {page.url})")
    check("待设计方案" in page.content(), "activity in 待设计方案 status")

    # Promoter only sees submit button, not sign or reject
    has_submit = page.locator('button:has-text("提交到安保方案设计")').count() > 0
    has_sign = page.locator('button:has-text("签署完成")').count() > 0
    has_reject = page.locator('button:has-text("驳回")').count() > 0
    check(has_submit, "promoter sees submit button")
    check(not has_sign, "promoter does NOT see sign button")
    check(not has_reject, "promoter does NOT see reject button")

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

    # === Step 1b: SecurityOfficer notification ===
    print("\n1b. SecurityOfficer notification")
    login_as(page, "security@test.com", "pass123")
    check("/login" not in page.url, "security logged in")
    bell = page.locator('button[aria-label="通知"]')
    badge = page.locator('.ant-badge-count, .ant-scroll-number')
    check(badge.count() > 0, "security has notification badge after submit")
    if bell.count() > 0:
        bell.first.click()
        page.wait_for_timeout(800)
    check("需进行安保方案设计" in page.content() or wf_name in page.content(), "notification content visible")

    # Click notification item → navigate to activity detail
    item = page.locator(f'.ant-dropdown-menu-item:has-text("{wf_name}")').first
    if item.count() > 0:
        item.click()
        page.wait_for_timeout(2000)
        page.wait_for_load_state("networkidle")
    check(f"/activities/{aid}" in page.url, f"notification click navigated to activity detail (got {page.url})")
    check(wf_name in page.content(), "activity name visible after notification click")

    # === Step 2: SecurityManager rejects ===
    print("\n2. SecurityManager: reject")
    login_as(page, "security_mgr@test.com", "pass123")
    check("/login" not in page.url, "security mgr logged in")
    find_activity_link(page, wf_name)
    check("/activities/" in page.url, f"on detail page (got {page.url})")
    check("待安保方案设计" in page.content(), "activity in 待安保方案设计 status")

    # SecurityManager sees reject button (has reject_approval)
    has_reject2 = page.locator('button:has-text("驳回")').count() > 0
    check(has_reject2, "security mgr sees reject button")

    rej = page.locator('button:has-text("驳回")').first
    if rej.count() > 0:
        rej.click()
        page.wait_for_timeout(1000)
        txt = page.locator('.ant-modal:visible textarea').first
        if txt.count() > 0: txt.fill("材料需要补充")
        ok = page.locator('button:has-text("确认驳回")').first
        if ok.count() > 0:
            ok.click()
            page.wait_for_timeout(3000)
            page.wait_for_load_state("networkidle")
    check("待安保方案设计" in page.content(), "status still 待安保方案设计 after self-loop reject")

    # === Step 3: SecurityOfficer signs complete ===
    print("\n3. SecurityOfficer: sign complete")
    login_as(page, "security@test.com", "pass123")
    check("/login" not in page.url, "security logged in")
    find_activity_link(page, wf_name)
    check("待安保方案设计" in page.content(), "activity in 待安保方案设计 status")

    sign = page.locator('button:has-text("签署完成")').first
    check(sign.count() > 0, "sign button visible")
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

    # === Step 4: AdminManager force cancels ===
    print("\n4. AdminManager: force cancel")
    login_as(page, "admin_mgr@test.com", "pass123")
    check("/login" not in page.url, "admin mgr logged in")
    find_activity_link(page, wf_name)
    check("/activities/" in page.url, f"on cancel activity detail (got {page.url})")

    cancel = page.locator('button:has-text("强制取消")').first
    check(cancel.count() > 0, "force cancel button visible")
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

    # === Step 4b: AdminStaff notification ===
    print("\n4b. AdminStaff notification for force cancel")
    login_as(page, "admin@test.com", "pass123")
    check("/login" not in page.url, "admin logged in")
    bell2 = page.locator('button[aria-label="通知"]')
    badge2 = page.locator('.ant-badge-count, .ant-scroll-number')
    check(badge2.count() > 0, "notification badge after force cancel")
    if bell2.count() > 0:
        bell2.first.click()
        page.wait_for_timeout(800)
    check("已变更为 已取消" in page.content() or wf_name in page.content(), "notification shows cancelled activity")

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
