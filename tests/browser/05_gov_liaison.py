"""GovLiaison scenario: approve, supplement, reject on 备案材料已交接 activities."""
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
    req = urllib.request.Request(f"{API}{path}", data=data,
        headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"})
    return json.loads(urllib.request.urlopen(req).read())

def api_put(path, body, token):
    data = json.dumps(body).encode()
    req = urllib.request.Request(f"{API}{path}", data=data,
        headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
        method="PUT")
    return json.loads(urllib.request.urlopen(req).read())

def login_api(email, password):
    resp = api_post("/auth/login", {"email": email, "password": password}, None)
    token = resp["access_token"]
    req = urllib.request.Request(f"{API}/auth/me", headers={"Authorization": f"Bearer {token}"})
    user = json.loads(urllib.request.urlopen(req).read())
    return token, user["id"]

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

# --- Create 3 activities in 备案材料已交接 via API (devtest, all permissions) ---
token, user_id = login_api("devtest@test.com", "pass123")

gov_names = []
for prefix in ["gov_approve", "gov_supplement", "gov_reject"]:
    name = f"{prefix}_{uuid.uuid4().hex[:4]}"
    act = api_post("/activities", {
        "name": name, "type": "大型活动",
        "estimated_time": "2026-06-15T09:00:00+08:00",
        "location": f"测试广场_{prefix}_{uuid.uuid4().hex[:4]}", "sponsor": "测试主办方",
        "sponsor_contact": "张三", "sponsor_phone": "13800138000",
        "deadline": "2026-06-01T18:00:00+08:00",
        "designer_id": user_id,
    }, token)
    aid = act["id"]
    # Transition: 待设计方案 → 待安保方案设计 → 待备案申请 → 备案材料已交接
    for to_status in ["待安保方案设计", "待备案申请", "备案材料已交接"]:
        api_put(f"/activities/{aid}/status",
            {"to_status": to_status, "comment": f"auto transition to {to_status}"}, token)
    gov_names.append(name)
    print(f"  prepared: {name}")

print(f"API setup: 3 activities in 备案材料已交接")

with sync_playwright() as p:
    browser = p.chromium.connect_over_cdp(CDP)
    page = create_page(browser)
    setup_logging("05_gov_liaison")
    recorder = start_recording(page, "05_gov_liaison")
    page.context.clear_cookies()

    errors = []
    page.on("console", lambda m: errors.append(f"[{m.type}] {m.text}"))
    page.on("pageerror", lambda e: errors.append(f"PAGE_ERROR: {e}"))

    # Login as GovLiaison
    page.goto(f"{BASE}/login")
    page.wait_for_load_state("networkidle")
    page.fill('input[placeholder="邮箱"]', "liaison@test.com")
    page.fill('input[type="password"]', "pass123")
    page.click('button[type="submit"]')
    page.wait_for_timeout(3000)
    page.wait_for_load_state("networkidle")
    check("/activities" in page.url, "logged in")

    # 1. Approve: 审批通过
    print("\n1. Approve (审批通过)")
    sidebar_nav(page, "全部活动")
    approve_link = page.locator(f'a:has-text("{gov_names[0]}")').first
    if approve_link.count() > 0:
        approve_link.click()
        page.wait_for_timeout(2000)
        page.wait_for_load_state("networkidle")
    check("/activities/" in page.url, f"on detail (got {page.url})")
    check("备案材料已交接" in page.content(), "status is 备案材料已交接")

    approve = page.locator('button:has-text("审批通过")').first
    check(approve.count() > 0, "approve button visible")
    if approve.count() > 0:
        approve.click()
        page.wait_for_timeout(800)
        txt = page.locator('.ant-modal:visible textarea').first
        if txt.count() > 0: txt.fill("批文已上传，同意通过")
        ok = page.locator('.ant-modal:visible .ant-btn-primary').first
        if ok.count() > 0: ok.click()
        page.wait_for_timeout(3000)
        page.wait_for_load_state("networkidle")
        check("审批通过" in page.content(), "status → 审批通过")

    # 2. Supplement: 需补充材料
    print("\n2. Supplement (需补充材料)")
    sidebar_nav(page, "全部活动")
    supplement_link = page.locator(f'a:has-text("{gov_names[1]}")').first
    if supplement_link.count() > 0:
        supplement_link.click()
        page.wait_for_timeout(2000)
        page.wait_for_load_state("networkidle")
    check("/activities/" in page.url, f"on detail (got {page.url})")
    check("备案材料已交接" in page.content(), "status is 备案材料已交接")

    supplement = page.locator('button:has-text("需补充材料")').first
    check(supplement.count() > 0, "supplement button visible")
    if supplement.count() > 0:
        supplement.click()
        page.wait_for_timeout(800)
        txt = page.locator('.ant-modal:visible textarea').first
        if txt.count() > 0: txt.fill("缺少风险评估表")
        ok = page.locator('.ant-modal:visible .ant-btn-primary').first
        if ok.count() > 0: ok.click()
        page.wait_for_timeout(3000)
        page.wait_for_load_state("networkidle")
        check("待补充备案材料" in page.content(), "status → 待补充备案材料")

    # 3. Reject: 驳回—不通过
    print("\n3. Reject (驳回—不通过)")
    sidebar_nav(page, "全部活动")
    reject_link = page.locator(f'a:has-text("{gov_names[2]}")').first
    if reject_link.count() > 0:
        reject_link.click()
        page.wait_for_timeout(2000)
        page.wait_for_load_state("networkidle")
    check("/activities/" in page.url, f"on detail (got {page.url})")
    check("备案材料已交接" in page.content(), "status is 备案材料已交接")

    reject = page.locator('button:has-text("驳回—不通过")').first
    check(reject.count() > 0, "reject button visible")
    if reject.count() > 0:
        reject.click()
        page.wait_for_timeout(800)
        txt = page.locator('.ant-modal:visible textarea').first
        if txt.count() > 0: txt.fill("材料不符合要求")
        ok = page.locator('.ant-modal:visible .ant-btn-primary').first
        if ok.count() > 0: ok.click()
        page.wait_for_timeout(3000)
        page.wait_for_load_state("networkidle")
        check("不通过/已终止" in page.content(), "status → 不通过/已终止")

    page.screenshot(path=f"{OUT / '05_gov_liaison_final.png'}", full_page=True)
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
