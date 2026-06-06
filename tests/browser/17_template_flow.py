"""Template flow: Promoter plan draft→generate→version→diff; SecurityOfficer security plan.

Setup uses API for activity creation (not the focus). All template interactions go through UI.
"""
from pathlib import Path
from datetime import datetime, timedelta, timezone
from playwright.sync_api import sync_playwright
from utils import (CDP, BASE, create_page, setup_logging, start_recording,
                   check, get_failed, login_as, sidebar_nav, login_api, api_post)

OUT = Path(__file__).parent / "screenshots"

with sync_playwright() as p:
    browser = p.chromium.connect_over_cdp(CDP)
    page = create_page(browser)
    setup_logging("17_template_flow")
    recorder = start_recording(page, "17_template_flow")

    errors: list[str] = []
    page.on("console", lambda m: errors.append(f"[{m.type}] {m.text}"))
    page.on("pageerror", lambda e: errors.append(f"PAGE_ERROR: {e}"))

    # ============================================================
    # SETUP: create activity via API (Promoter owns it)
    # ============================================================
    print("\n=== Setup: create activity ===")
    token, promoter_id = login_api("promoter@test.com", "pass123")
    tz = timezone(timedelta(hours=8))
    t = datetime.now(tz) + timedelta(days=14)
    resp = api_post("/activities", {
        "name": f"模板测试活动_{datetime.now(tz).strftime('%m%d%H%M')}",
        "type": "文艺汇演",
        "estimated_time": t.isoformat(),
        "location": "中心广场",
        "sponsor": "测试主办方",
        "sponsor_contact": "张三",
        "sponsor_phone": "13800138000",
        "deadline": (datetime.now(tz) + timedelta(days=7)).isoformat(),
    }, token)
    activity_id = resp["id"]
    activity_name = resp["name"]
    check("id" in resp, f"activity created: {activity_id[:8]}...")

    # ============================================================
    # 1. Promoter: activity plan draft → generate → version
    # ============================================================
    print("\n=== TC1: Promoter activity plan ===")
    login_as(page, "promoter@test.com", "pass123")
    check("/login" not in page.url, "promoter logged in")

    sidebar_nav(page, "全部活动")
    page.wait_for_selector('.ant-table-tbody', timeout=10000)
    page.wait_for_timeout(500)
    link = page.locator(f'a:has-text("{activity_name}")').first
    link.click()
    page.wait_for_timeout(2000)
    page.wait_for_load_state("networkidle")

    # Open plan tab
    plan_tab = page.locator('.ant-tabs-tab:has-text("活动方案")').first
    check(plan_tab.count() > 0, "plan tab visible")
    plan_tab.click()
    page.wait_for_timeout(1500)
    page.wait_for_load_state("networkidle")
    page.wait_for_selector('textarea', timeout=5000)

    # Fill required fields
    ta = page.locator('textarea').first
    ta.fill("浏览器测试：活动主要内容填写验证——文艺汇演")

    num_inputs = page.locator('input[type="text"][role="spinbutton"]').all()
    for inp in num_inputs:
        inp.fill("3")
        break

    date_inputs = page.locator('.ant-picker input').all()
    if len(date_inputs) >= 2:
        date_inputs[0].fill("2026-08-01")
        date_inputs[0].press("Enter")
        page.wait_for_timeout(300)
        date_inputs[1].fill("2026-08-03")
        date_inputs[1].press("Enter")
        page.wait_for_timeout(300)

    # Save draft
    draft_btn = page.locator('button:has-text("保存草稿")').first
    check(draft_btn.count() > 0, "save draft button")
    draft_btn.click()
    page.wait_for_timeout(2000)
    page.wait_for_load_state("networkidle")

    # Generate
    gen_btn = page.locator('button:has-text("提交生成")').first
    gen_btn.click()
    page.wait_for_timeout(1000)

    # Confirm modal → click OK
    check(page.locator('.ant-modal:has-text("确认生成")').count() > 0, "confirmation modal shown")
    page.locator('.ant-modal-footer .ant-btn-primary:has-text("确认生成")').first.click()
    page.wait_for_timeout(500)

    # Wait for modal to close and v1 to appear (setQueryData makes this instant)
    page.wait_for_selector('.ant-modal:has-text("确认生成")', state='hidden', timeout=5000)
    page.wait_for_selector('button:has-text("v1")', timeout=10000)
    check(True, "v1 appears in timeline")

    # ============================================================
    # 2. Generate v2 then diff v1 vs v2
    # ============================================================
    print("\n=== TC2: v2 + diff ===")
    ta = page.locator('textarea').first
    ta.fill("浏览器测试：v2 修改后的活动方案内容——增加消防措施")

    gen_btn.click()
    page.wait_for_timeout(1000)
    page.locator('.ant-modal-footer .ant-btn-primary:has-text("确认生成")').first.click()
    page.wait_for_timeout(500)
    page.wait_for_selector('.ant-modal:has-text("确认生成")', state='hidden', timeout=5000)
    page.wait_for_selector('button:has-text("v2")', timeout=10000)
    check(True, "v2 appears in timeline")

    # Select v1 and v2 for diff
    page.locator('button:has-text("v1")').first.click()
    page.locator('button:has-text("v2")').first.click()
    page.wait_for_timeout(300)

    diff_btn = page.locator('button:has-text("对比")').first
    check(diff_btn.count() > 0, "diff button appears")
    diff_btn.click()
    page.wait_for_timeout(1500)

    diff_modal = page.locator('.ant-modal:has-text("版本对比")').first
    check(diff_modal.count() > 0, "diff modal open")
    changed = diff_modal.locator('.ant-descriptions').count()
    check(changed > 0, f"diff shows {changed} changed field(s)")

    diff_modal.locator('.ant-modal-close').first.click()
    page.wait_for_timeout(500)

    # ============================================================
    # 3. SecurityOfficer: risk level → security plan → generate
    # ============================================================
    print("\n=== TC3: SecurityOfficer security plan ===")
    login_as(page, "security@test.com", "pass123")

    sidebar_nav(page, "全部活动")
    page.wait_for_selector('.ant-table-tbody', timeout=10000)
    page.wait_for_timeout(500)
    link = page.locator(f'a:has-text("{activity_name}")').first
    check(link.count() > 0, f"activity '{activity_name}' visible to SecurityOfficer")
    link.click()
    page.wait_for_timeout(2000)
    page.wait_for_load_state("networkidle")

    # Open security plan tab
    sp_tab = page.locator('.ant-tabs-tab:has-text("安保方案")').first
    check(sp_tab.count() > 0, "security plan tab visible")
    sp_tab.click()
    page.wait_for_timeout(1500)
    page.wait_for_load_state("networkidle")

    # Select risk level if needed
    risk_selector = page.locator('.ant-select-selector').first
    if risk_selector.count() > 0:
        risk_selector.click()
        page.wait_for_timeout(500)
        option = page.locator('.ant-select-item-option:has-text("大型")').first
        if option.count() > 0:
            option.click()
            page.wait_for_timeout(1500)
            page.wait_for_load_state("networkidle")
            check(True, "risk level set to 大型")

    # Fill required textareas for security plan
    sp_textareas = page.locator('textarea').all()
    for i, ta_el in enumerate(sp_textareas):
        if ta_el.is_visible():
            ta_el.fill(f"浏览器测试安保方案字段{i+1}")
    page.wait_for_timeout(300)

    # Generate security plan
    sp_gen = page.locator('button:has-text("提交生成")').first
    check(sp_gen.count() > 0, "generate button visible")
    sp_gen.click()
    page.wait_for_timeout(1000)
    cfm = page.locator('.ant-modal-footer .ant-btn-primary:has-text("确认生成")').first
    if cfm.count() > 0:
        cfm.click()
        page.wait_for_timeout(500)
        page.wait_for_selector('.ant-modal:has-text("确认生成")', state='hidden', timeout=5000)
        page.wait_for_selector('button:has-text("v1")', timeout=10000)
        check(True, "security plan v1 generated")
    else:
        check(False, "confirmation modal not shown for security plan")

    # ============================================================
    # Report
    # ============================================================
    print(f"\n=== {len(errors)} console/page errors ===")
    for e in errors[:10]:
        print(f"  {e}")

    if recorder:
        recorder.stop()

    assert get_failed() == 0, f"{get_failed()} check(s) failed"
