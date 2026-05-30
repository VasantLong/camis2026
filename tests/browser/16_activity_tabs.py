"""活动列表分类：待操作 / 已完成 Tab。"""
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
    return resp["access_token"]

def login_as(page, email, password):
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

# --- Create activity as promoter ---
p_token = login_api("promoter@test.com", "pass123")
me = api_get("/auth/me", p_token)
uname = f"tab_{uuid.uuid4().hex[:6]}"
aid = api_post("/activities", {
    "name": uname, "type": "大型活动",
    "estimated_time": "2026-08-15T09:00:00+08:00",
    "location": f"Tab测试广场_{uname}", "sponsor": "测试主办方",
    "deadline": "2026-08-01T18:00:00+08:00",
    "designer_id": me["id"],
}, p_token)["id"]
print(f"API created: {uname} (待设计方案)")

with sync_playwright() as p:
    browser = p.chromium.connect_over_cdp(CDP)
    page = create_page(browser)
    setup_logging("16_activity_tabs")
    recorder = start_recording(page, "16_activity_tabs")
    page.context.clear_cookies()

    errors = []
    page.on("console", lambda m: errors.append(f"[{m.type}] {m.text}"))
    page.on("pageerror", lambda e: errors.append(f"PAGE_ERROR: {e}"))

    # === Step 1: Pending tab shows new activity ===
    print("\n1. Pending tab shows activity")
    login_as(page, "promoter@test.com", "pass123")
    sidebar_nav(page, "全部活动")
    check("待操作" in page.content(), "pending tab visible")
    check(uname in page.content(), "activity visible in pending tab")

    # === Step 2: Switch to completed tab → activity NOT there ===
    print("\n2. Completed tab is empty for new activity")
    comp_tab = page.locator('.ant-tabs-tab:has-text("已完成")')
    if comp_tab.count() > 0:
        comp_tab.first.click()
        page.wait_for_timeout(1500)
        page.wait_for_load_state("networkidle")
    check(uname not in page.content() or "暂无" in page.content(),
          "activity NOT in completed tab")

    # === Step 3: Move to terminal state via force cancel ===
    print("\n3. Force cancel activity → completed tab")
    sa_token = login_api("superadmin@test.com", "pass123")
    api_post(f"/activities/{aid}/force-cancel", {"reason": "测试完成"}, sa_token)

    # Navigate back to activities via sidebar, then switch to completed tab
    sidebar_nav(page, "全部活动")
    page.wait_for_timeout(1000)
    comp_tab2 = page.locator('.ant-tabs-tab:has-text("已完成")')
    if comp_tab2.count() > 0:
        comp_tab2.first.click()
        page.wait_for_timeout(2000)
        page.wait_for_load_state("networkidle")
    check(uname in page.content(), "已完成 tab 可见活动")

    # Switch to pending → should NOT show it (terminal, now in completed)
    pend_tab = page.locator('.ant-tabs-tab:has-text("待操作")')
    if pend_tab.count() > 0:
        pend_tab.first.click()
        page.wait_for_timeout(1500)
        page.wait_for_load_state("networkidle")
    check(uname not in page.content() or "暂无" in page.content(),
          "activity NOT in pending tab after completion")

    page.screenshot(path=f"{OUT / '16_activity_tabs_final.png'}", full_page=True)
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
