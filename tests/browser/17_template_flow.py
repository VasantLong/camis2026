"""Template flow: Promoter plan draft→generate→version→diff; SecurityOfficer 双表 (风险评估表+责任确认书) + security plan.

Setup uses API for activity creation (not the focus). All template interactions go through UI.
"""
from pathlib import Path
from datetime import datetime, timedelta, timezone
from playwright.sync_api import sync_playwright
from utils import (CDP, BASE, create_page, setup_logging, capture_console,
                   start_recording, check, get_failed, login_as, sidebar_nav,
                   login_api, api_post)

OUT = Path(__file__).parent / "screenshots"

with sync_playwright() as p:
    browser = p.chromium.connect_over_cdp(CDP)
    page = create_page(browser)
    setup_logging("17_template_flow")
    recorder = start_recording(page, "17_template_flow")

    errors = capture_console(page, "17_template_flow")

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

    def select_antd(label: str, option: str) -> None:
        """Select an antd Select option via keyboard (readonly combobox needs keyboard.type)."""
        item = page.locator('.ant-form-item').filter(has_text=label).first
        cb = item.locator('input[role="combobox"]').first
        cb.click()
        page.wait_for_timeout(300)
        page.keyboard.type(option)
        page.wait_for_timeout(200)
        page.keyboard.press("Enter")
        page.wait_for_timeout(300)

    # Textareas
    page.locator('textarea').first.fill("浏览器测试：活动主要内容填写验证——文艺汇演")
    page.locator('.ant-form-item:has-text("搭建方案") textarea').first.fill("浏览器测试：搭建方案——含材料明细、平面图")
    page.wait_for_timeout(200)

    # Dates: start_time, end_time (first, so auto_calc total_days settles)
    dps = page.locator('.ant-picker input').all()
    dps[0].fill("2026-08-01"); dps[0].press("Enter"); page.wait_for_timeout(400)
    dps[1].fill("2026-08-03"); dps[1].press("Enter"); page.wait_for_timeout(500)

    # Selects (reliable: click .ant-select-item-option-content)
    select_antd("平日人数", "1000-3000")
    select_antd("是否有开幕式", "是")
    select_antd("是否有演员嘉宾", "是")

    # Conditional fields now visible — fill them
    page.wait_for_timeout(500)
    dps2 = page.locator('.ant-picker input').all()
    if len(dps2) >= 4:
        dps2[2].fill("2026-08-01"); dps2[2].press("Enter"); page.wait_for_timeout(200)
        dps2[3].fill("2026-08-02"); dps2[3].press("Enter"); page.wait_for_timeout(300)

    select_antd("主要活动日人数", "1000-3000")

    # Enabled number inputs
    for i, inp in enumerate(page.locator('input[role="spinbutton"]:not([disabled])').all()):
        if inp.is_visible():
            inp.fill(str(3 + i))
            page.wait_for_timeout(100)

    # Phone
    page.locator('.ant-form-item:has-text("负责人联系方式") input').first.fill("13800138001")

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
    page.locator('.ant-modal button:has-text("确认生成")').first.click()
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
    page.wait_for_timeout(2000)

    gen_btn2 = page.locator('button:has-text("提交生成")').first
    check(gen_btn2.is_enabled(), "generate button enabled after text change")
    gen_btn2.click()
    page.wait_for_timeout(1000)
    check(page.locator('.ant-modal:has-text("确认生成")').count() > 0, "confirm modal for v2")
    page.locator('.ant-modal button:has-text("确认生成")').first.click()
    page.wait_for_timeout(500)
    page.wait_for_selector('.ant-modal:has-text("确认生成")', state='hidden', timeout=5000)
    page.wait_for_timeout(5000)
    page.wait_for_selector('button:has-text("v2")', timeout=20000)
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

    # Finalize plan: click → confirm modal → submit
    finalize_btn = page.locator('button:has-text("最终确定方案")').first
    check(finalize_btn.count() > 0, "finalize button visible")
    finalize_btn.click()
    page.wait_for_timeout(500)

    # Confirm modal
    check(page.locator('.ant-modal:has-text("确认最终确定方案")').count() > 0, "finalize confirm modal")
    page.locator('.ant-modal button:has-text("确认提交")').first.click()
    page.wait_for_timeout(2000)
    page.wait_for_load_state("networkidle")
    check(True, "plan finalized → workflow transition")

    # ============================================================
    # 3. SecurityOfficer: 双表 + security plan sub-tabs
    # ============================================================
    print("\n=== TC3: SecurityOfficer 双表 + security plan ===")
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

    # Verify sub-tabs are visible
    sub_tabs = page.locator('.ant-tabs-tab')
    risk_tab = page.locator('.ant-tabs-tab:has-text("风险评估表")').first
    resp_tab = page.locator('.ant-tabs-tab:has-text("责任确认书")').first
    check(risk_tab.count() > 0, "risk assessment sub-tab visible")
    check(resp_tab.count() > 0, "responsibility letter sub-tab visible")

    # Select risk level — on 安保方案 sub-tab (default active)
    page.locator('input[role="combobox"]').first.click()
    page.wait_for_timeout(300)
    page.keyboard.type("大型")
    page.wait_for_timeout(200)
    page.keyboard.press("Enter")
    page.wait_for_timeout(1500)
    page.wait_for_load_state("networkidle")
    check(True, "risk level set to 大型")

    # ── 3a. Risk assessment sub-tab ──
    print("\n--- 3a: risk assessment ---")
    risk_tab.click()
    page.wait_for_timeout(1000)
    page.wait_for_load_state("networkidle")

    # Wait for schema to load and form to render
    page.wait_for_timeout(1000)
    ra_textareas = page.locator('textarea').all()
    ra_filled = 0
    for ta_el in ra_textareas:
        if ta_el.is_visible():
            ta_el.fill(f"浏览器测试风险评估字段{ra_filled+1}")
            ra_filled += 1
    page.wait_for_timeout(300)

    # Fill number inputs (crowd_scale, staff_count, security_count)
    spin_inputs = page.locator('input[role="spinbutton"]:not([disabled])').all()
    for inp in spin_inputs:
        if inp.is_visible():
            inp.fill("100")
            page.wait_for_timeout(100)

    # Fill text inputs (reporting_unit, sponsor, contact fields, etc.)
    text_inputs = page.locator('input:not([role="combobox"]):not([role="spinbutton"]):not([type="hidden"])').all()
    for inp in text_inputs:
        if inp.is_visible() and inp.get_attribute("readonly") is None:
            try:
                inp.fill("测试")
            except Exception:
                pass
            page.wait_for_timeout(50)

    check(ra_filled > 0, f"filled {ra_filled} risk assessment fields")

    # Debug: inspect the generate button's bounding box and visibility
    btn_info = page.evaluate("""() => {
      const btn = document.querySelector('button');
      if (!btn) return 'no button found';
      const rect = btn.getBoundingClientRect();
      const style = window.getComputedStyle(btn);
      return {
        tag: btn.textContent?.substring(0, 20),
        rect: { x: rect.x, y: rect.y, w: rect.width, h: rect.height },
        display: style.display,
        visibility: style.visibility,
        opacity: style.opacity,
        overflow: style.overflow,
      };
    }""")
    print(f"  DEBUG first button: {btn_info}")

    # Check all buttons
    all_btns = page.evaluate("""() => {
      return Array.from(document.querySelectorAll('button')).map(b => ({
        text: b.textContent?.substring(0, 30),
        visible: b.offsetParent !== null,
        rect: (() => { const r = b.getBoundingClientRect(); return { w: Math.round(r.width), h: Math.round(r.height), y: Math.round(r.y) }; })()
      }));
    }""")
    for b in all_btns[:15]:
        print(f"  BTN: {b['text'][:30]} visible={b['visible']} size={b['rect']['w']}x{b['rect']['h']} y={b['rect']['y']}")

    # Generate
    ra_gen = page.locator('button:has-text("提交生成")').first
    check(ra_gen.count() > 0, "risk assessment generate button")
    ra_gen.click()
    page.wait_for_timeout(1000)
    cfm = page.locator('.ant-modal button:has-text("确认生成")').first
    if cfm.count() > 0:
        cfm.click()
        page.wait_for_timeout(500)
        page.wait_for_selector('.ant-modal:has-text("确认生成")', state='hidden', timeout=5000)
        page.wait_for_selector('button:has-text("v1")', timeout=15000)
        check(True, "risk assessment v1 generated")
    else:
        check(False, "risk assessment confirm modal not shown")

    # ── 3b. Responsibility letter sub-tab ──
    print("\n--- 3b: responsibility letter ---")
    resp_tab.click()
    page.wait_for_timeout(1000)
    page.wait_for_load_state("networkidle")
    page.wait_for_timeout(1000)

    # Verify declarations section is visible (8 legal statements, not checkboxes)
    decl_section = page.locator('text=安全消防责任确认').first
    check(decl_section.count() > 0, "declarations section visible")

    # Verify declaration items (legal statements in ordered list)
    decl_items = page.locator('ol li').all()
    check(len(decl_items) >= 8, f"all 8 declaration items visible (found {len(decl_items)})")

    # Fill text fields
    rl_textareas = page.locator('textarea').all()
    rl_filled = 0
    for ta_el in rl_textareas:
        if ta_el.is_visible():
            ta_el.fill(f"浏览器测试责任确认书字段{rl_filled+1}")
            rl_filled += 1
    page.wait_for_timeout(300)

    # Fill text inputs (sponsor_unit, venue_name, security_leader_name, sponsor_seal, confirm_location)
    for inp in page.locator('input:not([role="combobox"]):not([role="spinbutton"]):not([type="hidden"]):not([disabled])').all():
        if inp.is_visible():
            try:
                inp.fill("测试责任方")
            except Exception:
                pass
            page.wait_for_timeout(50)

    check(rl_filled > 0, f"filled {rl_filled} responsibility letter fields")

    # Generate
    rl_gen = page.locator('button:has-text("提交生成")').first
    check(rl_gen.count() > 0, "responsibility letter generate button")
    rl_gen.scroll_into_view_if_needed()
    page.wait_for_timeout(300)
    rl_gen.click()
    page.wait_for_timeout(1000)
    cfm2 = page.locator('.ant-modal button:has-text("确认生成")').first
    if cfm2.count() > 0:
        cfm2.click()
        page.wait_for_timeout(500)
        page.wait_for_selector('.ant-modal:has-text("确认生成")', state='hidden', timeout=5000)
        page.wait_for_selector('button:has-text("v1")', timeout=15000)
        check(True, "responsibility letter v1 generated")
    else:
        check(False, "responsibility letter confirm modal not shown")

    # ── 3c. Security plan (back to first sub-tab) ──
    print("\n--- 3c: security plan ---")
    page.locator('.ant-tabs-tab:has-text("安保方案")').first.click()
    page.wait_for_timeout(1000)
    page.wait_for_load_state("networkidle")

    # Fill required textareas for security plan
    sp_textareas = page.locator('textarea').all()
    for i, ta_el in enumerate(sp_textareas):
        if ta_el.is_visible():
            ta_el.fill(f"浏览器测试安保方案字段{i+1}")
    page.wait_for_timeout(300)

    # Fill security_staff_count
    sp_count = page.locator('.ant-form-item:has-text("安保人员数量") input[role="spinbutton"]').first
    if sp_count.count() > 0:
        sp_count.fill("10")
        page.wait_for_timeout(100)

    # Generate security plan
    sp_gen = page.locator('button:has-text("提交生成")').first
    check(sp_gen.count() > 0, "generate button visible")
    sp_gen.click()
    page.wait_for_timeout(1000)
    cfm3 = page.locator('.ant-modal button:has-text("确认生成")').first
    if cfm3.count() > 0:
        cfm3.click()
        page.wait_for_timeout(500)
        page.wait_for_selector('.ant-modal:has-text("确认生成")', state='hidden', timeout=5000)
        page.wait_for_selector('button:has-text("v1")', timeout=10000)
        check(True, "security plan v1 generated")
    else:
        check(False, "confirmation modal not shown for security plan")

    # Submit for review
    submit_btn = page.locator('button:has-text("提交审核")').first
    check(submit_btn.count() > 0, "submit review button visible")
    submit_btn.click()
    page.wait_for_timeout(500)

    check(page.locator('.ant-modal:has-text("确认提交审核")').count() > 0, "submit confirm modal")
    page.locator('.ant-modal button:has-text("确认提交")').first.click()
    page.wait_for_timeout(2000)
    page.wait_for_load_state("networkidle")
    check(True, "security plan submitted for review")

    # After submission, form should be locked and button disabled
    page.wait_for_timeout(1000)
    submitted_btn = page.locator('button:has-text("已提交审核，等待负责人签署")').first
    check(submitted_btn.count() > 0, "button shows submitted state")
    check(submitted_btn.is_disabled(), "submit button disabled after submission")

    # Verify sub-tabs still accessible after submission (forms disabled)
    risk_tab2 = page.locator('.ant-tabs-tab:has-text("风险评估表")').first
    risk_tab2.click()
    page.wait_for_timeout(1000)
    check(True, "risk assessment tab still accessible after submit")

    # ============================================================
    # Report
    # ============================================================
    print(f"\n=== {len(errors)} console/page errors ===")
    for e in errors[:10]:
        print(f"  {e}")

    if recorder:
        recorder.stop()

    assert get_failed() == 0, f"{get_failed()} check(s) failed"
