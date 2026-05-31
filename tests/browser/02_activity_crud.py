"""Activity CRUD: create via API, verify frontend display + filter + detail."""
from pathlib import Path
import uuid
from playwright.sync_api import sync_playwright
from utils import (CDP, BASE, API, create_page, setup_logging, start_recording,
                   check, get_failed, login_as, sidebar_nav, api_post, login_api)

OUT = Path(__file__).parent / "screenshots"

# --- Create test data ---
token, user_id = login_api("promoter@test.com", "pass123")
aname = f"测试活动_{uuid.uuid4().hex[:6]}"
act = api_post("/activities", {
    "name": aname, "type": "大型活动",
    "estimated_time": "2026-06-15T09:00:00+08:00",
    "location": "测试广场", "sponsor": "测试主办方",
    "sponsor_contact": "张三", "sponsor_phone": "13800138000",
    "deadline": "2026-06-01T18:00:00+08:00",
    "designer_id": user_id,
}, token)
aid = act["id"]
print(f"API created: {aname} (id={aid[:8]}...) status={act['status']}")

# --- Browser tests ---
with sync_playwright() as p:
    browser = p.chromium.connect_over_cdp(CDP)
    page = create_page(browser)
    setup_logging("02_activity_crud")
    recorder = start_recording(page, "02_activity_crud")

    errors = []
    page.on("console", lambda m: errors.append(f"[{m.type}] {m.text}"))
    page.on("pageerror", lambda e: errors.append(f"PAGE_ERROR: {e}"))

    # Login — 登录后默认跳转到 /profile，用户通过侧边栏导航到活动管理
    print("\n0. Login")
    login_as(page, "promoter@test.com", "pass123")
    check("/login" not in page.url, "logged in")

    sidebar_nav(page, "全部活动")
    check("/activities" in page.url, "navigated to activity list")

    # 1. Activity list shows created activity
    print("\n1. Activity in list")
    check(aname in page.content(), f"'{aname}' visible in activity list")

    # 2. Status filter
    print("\n2. Status filter")
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
        upload = page.locator('.ant-upload').first
        check(upload.count() > 0, "upload component present")
    else:
        check(False, "document tab not found")

    # 6. Back to list via sidebar
    print("\n6. Back to list")
    sidebar_nav(page, "全部活动")
    check(aname in page.content(), "back in list, activity visible")

    page.screenshot(path=f"{OUT / '02_activity_crud_final.png'}", full_page=True)
    if recorder:
        recorder.stop()
    page.close()

    print(f"\n=== Console errors ===")
    for e in errors:
        if "[error]" in e or "PAGE_ERROR" in e:
            print(f"  {e}")

    failed = get_failed()
    print(f"\nFailed: {failed}")
    if failed > 0:
        raise SystemExit(1)
