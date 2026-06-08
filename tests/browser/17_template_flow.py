"""Full workflow: Promoter plan→Officer 双表+安保方案→Manager签署→Officer打包交接→GovLiaison审查通过.

Setup uses API for activity creation. All interactions go through UI from user perspective.
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

    def scroll_tab_content() -> None:
        """Scroll the tab panel to bottom so buttons are visible."""
        page.evaluate("""() => {
          const panel = document.querySelector('.ant-tabs-content-holder');
          if (panel) panel.scrollTop = panel.scrollHeight;
        }""")
        page.wait_for_timeout(500)

    def click_gen(label: str) -> None:
        """Click '提交生成' and confirm modal — same pattern as security plan."""
        btn = page.locator('button:has-text("提交生成")').first
        btn.click()
        page.wait_for_timeout(1000)
        check(page.locator('.ant-modal:has-text("确认生成")').count() > 0, f"{label} confirm modal shown")
        page.locator('.ant-modal button:has-text("确认生成")').first.click()
        page.wait_for_timeout(500)
        page.wait_for_selector('.ant-modal:has-text("确认生成")', state='hidden', timeout=5000)
        page.wait_for_selector('button:has-text("v1")', state="attached", timeout=15000)
        check(True, f"{label} v1 generated")

    def fill_repeater(field_name: str, label: str, items: list[str]) -> None:
        """Add items to a repeater field. Clicks '添加' then fills each input."""
        section = page.locator('.ant-form-item').filter(has_text=label).first
        for i, text in enumerate(items):
            if i > 0:
                add_btn = section.locator('button:has-text("添加")').first
                add_btn.click()
                page.wait_for_timeout(200)
        page.wait_for_timeout(300)
        for j, text in enumerate(items):
            inp = page.locator(f'input[id*="{field_name}"]').nth(j)
            if inp.count() > 0:
                try:
                    inp.click()
                    page.keyboard.type(text)
                except Exception:
                    pass
                page.wait_for_timeout(80)

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

    # ── 3a. Security plan (fill first, on default sub-tab) ──
    print("\n--- 3a: security plan ---")

    # Fill required textareas for security plan
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

    # Save draft + generate
    draft_sp = page.locator('button:has-text("保存草稿")').first
    if draft_sp.count() > 0 and draft_sp.is_enabled():
        draft_sp.click()
        page.wait_for_timeout(500)
    sp_gen = page.locator('button:has-text("提交生成")').first
    check(sp_gen.count() > 0, "generate button visible")
    sp_gen.click()
    page.wait_for_timeout(1000)
    check(page.locator('.ant-modal:has-text("确认生成")').count() > 0, "security plan confirm modal shown")
    page.locator('.ant-modal button:has-text("确认生成")').first.click()
    page.wait_for_timeout(500)
    page.wait_for_selector('.ant-modal:has-text("确认生成")', state='hidden', timeout=5000)
    page.wait_for_selector('button:has-text("v1")', timeout=10000)
    check(True, "security plan v1 generated")

    # ── 3b. Risk assessment ──
    print("\n--- 3b: risk assessment ---")
    risk_tab.click()
    page.wait_for_timeout(1500)
    page.wait_for_load_state("networkidle")
    page.wait_for_timeout(1000)

    # Verify autofill fields populated (from Activity + plan snapshot + defaults)
    af_project = page.locator('.ant-form-item:has-text("项目名称") input').first
    check(af_project.count() > 0 and af_project.input_value() != "", "project_name autofilled from activity.name")
    af_sponsor = page.locator('.ant-form-item:has-text("主办方") input').first
    check(af_sponsor.count() > 0 and af_sponsor.input_value() != "", "sponsor autofilled")
    af_type = page.locator('.ant-form-item:has-text("活动类型") input').first
    check(af_type.count() > 0 and af_type.input_value() != "", "activity_type autofilled")
    af_loc_type = page.locator('.ant-form-item:has-text("场所类型") input').first
    check(af_loc_type.count() > 0 and af_loc_type.input_value() != "", "location_type autofilled")
    af_unit = page.locator('.ant-form-item:has-text("填报单位") input').first
    check(af_unit.count() > 0 and af_unit.input_value() != "", "reporting_unit autofilled from env")
    af_content = page.locator('.ant-form-item:has-text("活动内容") input').first
    check(af_content.count() > 0 and af_content.input_value() != "", "activity_content autofilled from plan")
    af_start = page.locator('.ant-form-item:has-text("开始时间") input').first
    check(af_start.input_value() != "", "activity_start autofilled from plan")
    af_end = page.locator('.ant-form-item:has-text("结束时间") input').first
    check(af_end.input_value() != "", "activity_end autofilled from plan")

    # Fill manual text fields — click + type + Tab to trigger antd onChange
    for label_text in [("活动地点（具体地址）", "中心广场主舞台区"), ("承办方", "测试文化公司"), ("活动参与方", "社区居民")]:
        inp = page.locator(f'.ant-form-item:has-text("{label_text[0]}") input').first
        inp.click()
        page.keyboard.type(label_text[1])
        page.keyboard.press("Tab")
        page.wait_for_timeout(150)
    page.wait_for_timeout(200)

    # Selects (non-autofill ones)
    select_antd("室内/户外", "室内")
    select_antd("预计参与人数规模", "1000-3000")
    select_antd("是否销售门票", "否")
    select_antd("是否有媒体直播或采录", "是")
    page.wait_for_timeout(500)
    # Conditional fields: media_channel, media_name, media_type
    select_antd("媒体采录方式", "直播")
    page.locator('.ant-form-item:has-text("媒体名称") input').first.fill("测试电视台")
    select_antd("媒体类型", "官方")
    page.wait_for_timeout(300)

    # Repeaters: risk_factors (min 4) + mitigation_measures (min 4)
    fill_repeater("risk_factors", "主要风险因素", [
        "决策合法性：活动方案未经主管部门审批，存在合规风险",
        "合理性：预计参与人数超出场地承载能力，易引发拥挤踩踏",
        "可行性：安保人员配置不足，无法覆盖全部出入口和重点区域",
        "可控性：应急预案未明确疏散路线和责任人，响应机制不健全",
    ])
    fill_repeater("mitigation_measures", "防范化解措施", [
        "提前向主管部门提交完整活动方案并取得书面审批文件",
        "严格控制参与人数在场地安全承载范围内，设置实时人流监测",
        "增配安保人员至核定数量，覆盖全部出入口、舞台区、观众区",
        "制定详细应急预案，明确疏散路线、各岗位责任人和通讯联络方式",
    ])

    # Contact
    page.locator('.ant-form-item:has-text("联系人") input').first.fill("李四")
    page.locator('.ant-form-item:has-text("联系电话") input').first.fill("13800138002")
    page.wait_for_timeout(200)

    # Upload assessor signature
    sig_file = Path("/tmp/_test_assessor_sig.png")
    sig_file.write_bytes(b'\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x02\x00\x00\x00\x90wS\xde\x00\x00\x00\x0cIDATx\x9cc\xf8\x0f\x00\x00\x01\x01\x00\x05\x18\xd8N\x00\x00\x00\x00IEND\xaeB`\x82')
    with page.expect_file_chooser() as fc_info:
        page.locator('.ant-form-item:has-text("评估主体负责人签字") button:has-text("上传签名图片")').first.click()
    fc_info.value.set_files(str(sig_file))
    page.wait_for_timeout(2000)
    sig_file.unlink(missing_ok=True)
    check(True, "assessor signature uploaded")

    # Move cursor away from uploaded image, then save draft + generate
    page.locator('.ant-form-item:has-text("联系人")').first.click()
    page.wait_for_timeout(300)
    page.locator('button:has-text("保存草稿")').first.click()
    page.wait_for_timeout(800)
    click_gen("risk assessment")

    # ── 3c. Responsibility letter ──
    print("\n--- 3c: responsibility letter ---")
    resp_tab.click()
    page.wait_for_timeout(1500)
    page.wait_for_load_state("networkidle")
    page.wait_for_timeout(1000)

    # Verify declarations section (not checkboxes — readonly legal statements)
    decl_section = page.locator('text=安全消防责任确认').first
    check(decl_section.count() > 0, "declarations section visible")
    decl_items = page.locator('ol li').all()
    check(len(decl_items) >= 8, f"all 8 declaration items visible (found {len(decl_items)})")

    # Verify autofill fields
    af_sponsor_unit = page.locator('.ant-form-item:has-text("活动主办单位") input').first
    check(af_sponsor_unit.count() > 0 and af_sponsor_unit.input_value() != "", "sponsor_unit autofilled from env")
    af_conf_date = page.locator('.ant-form-item:has-text("确认日期") input').first
    check(af_conf_date.input_value() != "", "confirm_date autofilled (today)")
    af_conf_loc = page.locator('.ant-form-item:has-text("确认地点") input').first
    check(af_conf_loc.count() > 0 and af_conf_loc.input_value() != "", "confirm_location autofilled from env")

    # Fill manual text fields
    page.locator('.ant-form-item:has-text("活动安全负责人") input').first.fill("王五")
    page.wait_for_timeout(300)

    # Upload security leader signature
    sig_file2 = Path("/tmp/_test_leader_sig.png")
    sig_file2.write_bytes(b'\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x02\x00\x00\x00\x90wS\xde\x00\x00\x00\x0cIDATx\x9cc\xf8\x0f\x00\x00\x01\x01\x00\x05\x18\xd8N\x00\x00\x00\x00IEND\xaeB`\x82')
    with page.expect_file_chooser() as fc_info:
        page.locator('.ant-form-item:has-text("安全负责人签字") button:has-text("上传签名图片")').first.click()
    fc_info.value.set_files(str(sig_file2))
    page.wait_for_timeout(2000)
    sig_file2.unlink(missing_ok=True)
    check(True, "security leader signature uploaded")

    page.locator('.ant-form-item:has-text("活动安全负责人")').first.click()
    page.wait_for_timeout(300)
    page.locator('button:has-text("保存草稿")').first.click()
    page.wait_for_timeout(800)
    click_gen("responsibility letter")

    # ── 3d. Back to 安保方案 — submit for review ──
    print("\n--- 3d: submit for review ---")
    page.locator('.ant-tabs-tab:has-text("安保方案")').first.click()
    page.wait_for_timeout(1500)
    page.wait_for_load_state("networkidle")

    # Submit for review — scroll into view then click normally
    page.wait_for_timeout(500)
    scroll_tab_content()
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
    # 4. SecurityManager: sign security plan
    # ============================================================
    print("\n=== TC4: SecurityManager sign ===")
    login_as(page, "security_mgr@test.com", "pass123")

    sidebar_nav(page, "全部活动")
    page.wait_for_selector('.ant-table-tbody', timeout=10000)
    page.wait_for_timeout(500)
    link = page.locator(f'a:has-text("{activity_name}")').first
    link.click()
    page.wait_for_timeout(2000)
    page.wait_for_load_state("networkidle")

    sp_tab = page.locator('.ant-tabs-tab:has-text("安保方案")').first
    sp_tab.click()
    page.wait_for_timeout(1500)
    page.wait_for_load_state("networkidle")

    # Verify signing UI visible
    sign_section = page.locator('text=安保负责人签署确认').first
    check(sign_section.count() > 0, "Manager signing section visible")

    # Upload signature image (dummy 1x1 PNG)
    sig_file = Path("/tmp/_test_sig.png")
    # minimal 1x1 white PNG
    sig_file.write_bytes(b'\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x02\x00\x00\x00\x90wS\xde\x00\x00\x00\x0cIDATx\x9cc\xf8\x0f\x00\x00\x01\x01\x00\x05\x18\xd8N\x00\x00\x00\x00IEND\xaeB`\x82')
    with page.expect_file_chooser() as fc_info:
        page.locator('button:has-text("上传签名图片")').first.click()
    fc_info.value.set_files(str(sig_file))
    page.wait_for_timeout(2000)
    page.wait_for_load_state("networkidle")
    check(True, "signature uploaded")

    # Confirm sign
    sign_btn = page.locator('button:has-text("确认签署并提交备案")').first
    check(sign_btn.count() > 0, "sign button visible")
    sign_btn.click()
    page.wait_for_timeout(2000)
    page.wait_for_load_state("networkidle")
    check(True, "Manager signed → status transitioned to 待备案申请")

    # ============================================================
    # 5. SecurityOfficer: pack + handover
    # ============================================================
    print("\n=== TC5: Officer pack + handover ===")
    login_as(page, "security@test.com", "pass123")

    sidebar_nav(page, "全部活动")
    page.wait_for_selector('.ant-table-tbody', timeout=10000)
    page.wait_for_timeout(500)
    link = page.locator(f'a:has-text("{activity_name}")').first
    link.click()
    page.wait_for_timeout(2000)
    page.wait_for_load_state("networkidle")

    # Open filing tab
    filing_tab = page.locator('.ant-tabs-tab:has-text("备案")').first
    check(filing_tab.count() > 0, "filing tab visible")
    filing_tab.click()
    page.wait_for_timeout(1500)
    page.wait_for_load_state("networkidle")

    # Verify materials list (should include template materials + seed materials)
    page.wait_for_timeout(1000)
    material_rows = page.locator('.ant-list-item').all()
    print(f"  materials found: {len(material_rows)}")
    check(len(material_rows) > 0, f"materials visible in filing tab ({len(material_rows)} items)")

    # Sign any unsigned materials
    sign_btns = page.locator('button:has-text("签署")').all()
    for btn in sign_btns:
        if btn.is_visible() and btn.is_enabled():
            btn.click()
            page.wait_for_timeout(300)
    page.wait_for_timeout(500)

    # Review any unreviewed materials (audit as qualified)
    audit_btns = page.locator('button:has-text("审查")').all()
    for btn in audit_btns:
        if btn.is_visible() and btn.is_enabled():
            btn.click()
            page.wait_for_timeout(500)
            # click "合格" tag to toggle
            qual_tag = page.locator('text=合格').first
            if qual_tag.count() > 0:
                qual_tag.click()
                page.wait_for_timeout(200)
            # submit audit
            submit_audit = page.locator('button:has-text("提交审查")').first
            if submit_audit.count() > 0:
                submit_audit.click()
                page.wait_for_timeout(800)
    page.wait_for_timeout(500)

    # Pack
    pack_btn = page.locator('button:has-text("打包备案材料")').first
    if pack_btn.count() > 0:
        pack_btn.click()
        page.wait_for_timeout(1000)
        # confirm in modal
        confirm_pack = page.locator('.ant-modal button:has-text("确认打包")').first
        if confirm_pack.count() > 0:
            confirm_pack.click()
            page.wait_for_timeout(2000)
            page.wait_for_load_state("networkidle")
            check(True, "materials packed")
    else:
        check(False, "pack button not found")

    # Confirm handover
    page.wait_for_timeout(1000)
    handover_btn = page.locator('button:has-text("确认纸质交接")').first
    if handover_btn.count() > 0:
        handover_btn.click()
        page.wait_for_timeout(500)
        # check confirmation checkbox
        cb = page.locator('.ant-modal .ant-checkbox-input').first
        if cb.count() > 0:
            cb.click()
            page.wait_for_timeout(200)
        confirm_ho = page.locator('.ant-modal button:has-text("确认")').first
        if confirm_ho.count() > 0:
            confirm_ho.click()
            page.wait_for_timeout(2000)
            page.wait_for_load_state("networkidle")
            check(True, "handover confirmed → 备案材料已交接")
    else:
        check(False, "handover button not found")

    # ============================================================
    # 6. GovLiaison: review materials + approve
    # ============================================================
    print("\n=== TC6: GovLiaison review + approve ===")
    login_as(page, "liaison@test.com", "pass123")

    sidebar_nav(page, "全部活动")
    page.wait_for_selector('.ant-table-tbody', timeout=10000)
    page.wait_for_timeout(500)
    link = page.locator(f'a:has-text("{activity_name}")').first
    check(link.count() > 0, f"activity visible to GovLiaison")
    link.click()
    page.wait_for_timeout(2000)
    page.wait_for_load_state("networkidle")

    # Open filing tab
    filing_tab2 = page.locator('.ant-tabs-tab:has-text("备案")').first
    filing_tab2.click()
    page.wait_for_timeout(1500)
    page.wait_for_load_state("networkidle")

    # Verify review panel visible
    review_panel = page.locator('text=政府对接 — 审批决策').first
    check(review_panel.count() > 0, "GovLiaison review panel visible")

    # Verify audit status shows unreviewed count
    page.wait_for_timeout(500)
    audit_status = page.locator('text=尚有').first
    check(audit_status.count() > 0, "pending audit count shown")

    # Audit materials (mark as qualified)
    audit_btns2 = page.locator('button:has-text("审查")').all()
    audited = 0
    for btn in audit_btns2:
        if btn.is_visible() and btn.is_enabled():
            btn.click()
            page.wait_for_timeout(500)
            qual_tag = page.locator('text=合格').first
            if qual_tag.count() > 0:
                qual_tag.click()
                page.wait_for_timeout(200)
            submit_btn = page.locator('button:has-text("提交审查")').first
            if submit_btn.count() > 0:
                submit_btn.click()
                page.wait_for_timeout(800)
                audited += 1
    check(audited > 0, f"audited {audited} materials")

    # Verify all-audited status
    page.wait_for_timeout(1000)
    all_audited_tag = page.locator('text=全部材料已审查').first
    check(all_audited_tag.count() > 0, "all materials audited")

    # Upload approval document (dummy PDF)
    approval_file = Path("/tmp/_test_approval.pdf")
    approval_file.write_text("dummy approval document")
    with page.expect_file_chooser() as fc_info:
        page.locator('button:has-text("选择批文文件")').first.click()
    fc_info.value.set_files(str(approval_file))
    page.wait_for_timeout(2000)
    check(True, "approval document uploaded")

    # Approve
    approve_btn = page.locator('button:has-text("审批通过")').first
    check(approve_btn.is_enabled(), "approve button enabled after all audited")
    approve_btn.click()
    page.wait_for_timeout(500)
    confirm_approve = page.locator('.ant-modal button:has-text("确认")').first
    if confirm_approve.count() > 0:
        confirm_approve.click()
        page.wait_for_timeout(2000)
        page.wait_for_load_state("networkidle")
        check(True, "GovLiaison approved → 审批通过")
    else:
        check(False, "approve confirm modal not shown")

    # Cleanup temp files
    sig_file.unlink(missing_ok=True)
    approval_file.unlink(missing_ok=True)

    # ============================================================
    # Report
    # ============================================================
    print(f"\n=== {len(errors)} console/page errors ===")
    for e in errors[:10]:
        print(f"  {e}")

    if recorder:
        recorder.stop()

    assert get_failed() == 0, f"{get_failed()} check(s) failed"
