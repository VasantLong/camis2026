"""活动列表分类：待操作 / 已完成 Tab。"""
from pathlib import Path
import uuid
from playwright.sync_api import sync_playwright
from utils import (CDP, BASE, API, create_page, setup_logging, start_recording,
                   check, get_failed, login_as, sidebar_nav, api_post, api_get, login_api)

OUT = Path(__file__).parent / "screenshots"

# --- Create activity as promoter ---
p_token, me = login_api("promoter@test.com", "pass123")
# We need the full user object for designer_id
me_full = api_get("/auth/me", p_token)
uname = f"tab_{uuid.uuid4().hex[:6]}"
aid = api_post("/activities", {
    "name": uname, "type": "大型活动",
    "estimated_time": "2026-08-15T09:00:00+08:00",
    "location": f"Tab测试广场_{uname}", "sponsor": "测试主办方",
    "sponsor_contact": "张三", "sponsor_phone": "13800138000",
    "deadline": "2026-08-01T18:00:00+08:00",
    "designer_id": me_full["id"],
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
    sa_token, _ = login_api("superadmin@test.com", "pass123")
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

    failed = get_failed()
    print(f"\nFailed: {failed}")
    if failed > 0:
        raise SystemExit(1)
