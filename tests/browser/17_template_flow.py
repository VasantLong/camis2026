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

    def fill_repeater(label: str, count: int, prefix: str) -> None:
        """Add `count` items to a repeater field. Clicks the '添加' button then fills each input."""
        section = page.locator('.ant-form-item').filter(has_text=label).first
        for i in range(count):
            add_btn = section.locator('button:has-text("添加")').first
            add_btn.click()
            page.wait_for_timeout(200)
        # fill each added input
        inputs = section.locator('input:not([role="combobox"]):not([type="hidden"])').all()
        for j, inp in enumerate(inputs):
            if inp.is_visible():
                try:
                    inp.fill(f"{prefix}{j+1}")
                except Exception:
                    pass
                page.wait_for_timeout(50)

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

    # Textareas
    page.locator('textarea').first.fill("浏览器测试：活动主要内容填写验证——文艺汇演")
    page.locator('.ant-form-item:has-text("搭建方案") textarea').first.fill("浏览器测试：搭建方案——含材料明细、平面图")
    page.wait_for_timeout(200)

    # Dates: start_time, end_time (first, so auto_calc total_days settles)
    dps = page.locator('.ant-picker input').all()
    dps[0].fill("2026-08-01"); dps[0].press("Enter"); page.wait_for_timeout(400)
    dps[1].fill("2026-08-03"); dps[1].press("Enter"); page.wait_for_timeout(500)

    # Selects — these values become cross-entity autofill sources for 双表
    select_antd("平日人数", "1000-3000")
    select_antd("是否有开幕式", "是")
    select_antd("是否有演员嘉宾", "是")
    page.wait_for_timeout(500)

    # Conditional fields
    dps2 = page.locator('.ant-picker input').all()
    if len(dps2) >= 4:
        dps2[2].fill("2026-08-01"); dps2[2].press("Enter"); page.wait_for_timeout(200)
        dps2[3].fill("2026-08-02"); dps2[3].press("Enter"); page.wait_for_timeout(300)
    select_antd("主要活动日人数", "1000-3000")
    page.wait_for_timeout(300)

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
    check(page.locator('.ant-modal:has-text("确认生成")').count() > 0, "confirmation modal shown")
    page.locator('.ant-modal button:has-text("确认生成")').first.click()
    page.wait_for_timeout(500)
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

    # Diff v1 vs v2
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

    # Finalize plan
    finalize_btn = page.locator('button:has-text("最终确定方案")').first
    check(finalize_btn.count() > 0, "finalize button visible")
    finalize_btn.click()
    page.wait_for_timeout(500)
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

    # Verify sub-tabs
    risk_tab = page.locator('.ant-tabs-tab:has-text("风险评估表")').first
    resp_tab = page.locator('.ant-tabs-tab:has-text("责任确认书")').first
    check(risk_tab.count() > 0, "risk assessment sub-tab visible")
    check(resp_tab.count() > 0, "responsibility letter sub-tab visible")

    # Select risk level on 安保方案 sub-tab (default active)
    page.locator('input[role="combobox"]').first.click()
    page.wait_for_timeout(300)
    page.keyboard.type("大型")
    page.wait_for_timeout(200)
    page.keyboard.press("Enter")
    page.wait_for_timeout(1500)
    page.wait_for_load_state("networkidle")
    check(True, "risk level set to 大型")

    # ── 3a. Risk assessment ──
    print("\n--- 3a: risk assessment ---")
    risk_tab.click()
    page.wait_for_timeout(1500)
    page.wait_for_load_state("networkidle")
    page.wait_for_timeout(1000)

    # Verify autofill fields populated (from Activity + plan snapshot)
    af_name = page.locator('.ant-form-item:has-text("活动名称") input').first
    check(af_name.count() > 0 and af_name.input_value() != "", "activity_name autofilled")
    af_sponsor = page.locator('.ant-form-item:has-text("主办方") input').first
    check(af_sponsor.count() > 0 and af_sponsor.input_value() != "", "sponsor autofilled")
    af_location = page.locator('.ant-form-item:has-text("活动地点") input').first
    check(af_location.count() > 0 and af_location.input_value() != "", "activity_location autofilled")

    # Also verify date+content autofilled from plan snapshot
    af_start = page.locator('.ant-form-item:has-text("开始时间") input').first
    check(af_start.input_value() != "", "activity_start autofilled from plan")
    af_end = page.locator('.ant-form-item:has-text("结束时间") input').first
    check(af_end.input_value() != "", "activity_end autofilled from plan")

    # Fill manual text fields
    page.locator('.ant-form-item:has-text("填报单位") input').first.fill("测试街道办")
    page.locator('.ant-form-item:has-text("项目名称") input').first.fill("春节文艺汇演")
    page.locator('.ant-form-item:has-text("承办方") input').first.fill("测试文化公司")
    page.locator('.ant-form-item:has-text("活动参与方") input').first.fill("社区居民")
    page.wait_for_timeout(200)

    # Selects
    select_antd("活动类型", "文艺汇演")
    select_antd("室内/户外", "室内")
    select_antd("场所类型", "中心广场")
    select_antd("预计参与人数规模", "1000-3000")
    select_antd("是否销售门票", "是")
    select_antd("媒体直播", "无")
    page.wait_for_timeout(300)

    # Repeaters: risk_factors (min 4) + mitigation_measures (min 4)
    fill_repeater("主要风险因素", 4, "风险因素")
    fill_repeater("防范化解措施", 4, "防范措施")

    # Contact
    page.locator('.ant-form-item:has-text("联系人") input').first.fill("李四")
    page.locator('.ant-form-item:has-text("联系电话") input').first.fill("13800138002")
    page.wait_for_timeout(200)

    # Scroll to bottom and generate
    page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
    page.wait_for_timeout(500)
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

    # ── 3b. Responsibility letter ──
    print("\n--- 3b: responsibility letter ---")
    resp_tab.click()
    page.wait_for_timeout(1500)
    page.wait_for_load_state("networkidle")
    page.wait_for_timeout(1000)

    # Verify declarations section (not checkboxes — readonly legal statements)
    decl_section = page.locator('text=安全消防责任确认').first
    check(decl_section.count() > 0, "declarations section visible")
    decl_items = page.locator('ol li').all()
    check(len(decl_items) >= 8, f"all 8 declaration items visible (found {len(decl_items)})")

    # Fill text fields
    page.locator('.ant-form-item:has-text("活动主办单位") input').first.fill("测试主办方")
    page.locator('.ant-form-item:has-text("举办场所名称") input').first.fill("中心广场")
    page.locator('.ant-form-item:has-text("活动安全负责人") input').first.fill("王五")
    page.locator('.ant-form-item:has-text("主办单位（公章）") input').first.fill("测试街道办公章")
    page.locator('.ant-form-item:has-text("确认地点") input').first.fill("中心广场会议室")
    page.wait_for_timeout(300)

    # Generate
    page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
    page.wait_for_timeout(500)
    rl_gen = page.locator('button:has-text("提交生成")').first
    check(rl_gen.count() > 0, "responsibility letter generate button")
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

    # ── 3c. Security plan ──
    print("\n--- 3c: security plan ---")
    page.locator('.ant-tabs-tab:has-text("安保方案")').first.click()
    page.wait_for_timeout(1500)
    page.wait_for_load_state("networkidle")

    # Fill security plan textareas
    sp_textareas = page.locator('textarea').all()
    for i, ta_el in enumerate(sp_textareas):
        if ta_el.is_visible():
            ta_el.fill(f"浏览器测试安保方案字段{i+1}")
    page.wait_for_timeout(300)

    # security_staff_count
    sp_count = page.locator('.ant-form-item:has-text("安保人员数量") input[role="spinbutton"]').first
    if sp_count.count() > 0:
        sp_count.fill("10")
        page.wait_for_timeout(100)

    # Generate
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

    # After submission, form locked and button disabled
    page.wait_for_timeout(1000)
    submitted_btn = page.locator('button:has-text("已提交审核，等待负责人签署")').first
    check(submitted_btn.count() > 0, "button shows submitted state")
    check(submitted_btn.is_disabled(), "submit button disabled after submission")

    # Sub-tabs still accessible after submit
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
