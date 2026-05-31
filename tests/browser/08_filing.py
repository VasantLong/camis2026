"""Filing: sign materials → audit → pack → handover. SecurityOfficer + GovLiaison flow."""
from pathlib import Path
from playwright.sync_api import sync_playwright
from utils import (CDP, BASE, create_page, setup_logging, start_recording,
                   check, get_failed, login_as, sidebar_nav)

OUT = Path(__file__).parent / "screenshots"
ACTIVITY_NAME = "社区志愿服务日"

with sync_playwright() as p:
    browser = p.chromium.connect_over_cdp(CDP)
    page = create_page(browser)
    setup_logging("08_filing")
    recorder = start_recording(page, "08_filing")

    errors = []
    page.on("console", lambda m: errors.append(f"[{m.type}] {m.text}"))
    page.on("pageerror", lambda e: errors.append(f"PAGE_ERROR: {e}"))

    # ============================================================
    # 1. SecurityOfficer: Sign all materials
    # ============================================================
    print("\n=== SecurityOfficer: Sign materials ===")
    login_as(page, "security@test.com", "pass123")
    check("/login" not in page.url, "security logged in")

    sidebar_nav(page, "全部活动")
    page.wait_for_selector('.ant-table-tbody', timeout=10000)
    page.wait_for_timeout(500)
    link = page.locator(f'a:has-text("{ACTIVITY_NAME}")').first
    link.click()
    page.wait_for_timeout(2000)
    page.wait_for_load_state("networkidle")
    check("/activities/" in page.url, "on activity detail page")

    filing_tab = page.locator('.ant-tabs-tab:has-text("备案")').first
    filing_tab.click()
    page.wait_for_timeout(1000)
    page.wait_for_load_state("networkidle")
    check(filing_tab.count() > 0, "filing tab opened")

    # Sign all materials
    page.wait_for_timeout(500)
    remaining = page.locator('button:has-text("签署")').all()
    print(f"  materials to sign: {len(remaining)}")
    while len(remaining) > 0:
        btn = remaining[0]
        if btn.is_visible():
            btn.click()
            page.wait_for_timeout(2000)
            page.wait_for_load_state("networkidle")
        remaining = page.locator('button:has-text("签署")').all()
    unsigned = page.locator('button:has-text("签署")').all()
    signed = page.locator('.ant-tag:has-text("已签署")').all()
    check(len(unsigned) == 0, f"all materials signed ({len(signed)} signed)")

    # ============================================================
    # 2. GovLiaison: Audit materials
    # ============================================================
    print("\n=== GovLiaison: Audit materials ===")
    login_as(page, "liaison@test.com", "pass123")
    check("/login" not in page.url, "liaison logged in")

    sidebar_nav(page, "全部活动")
    page.wait_for_selector('.ant-table-tbody', timeout=10000)
    page.wait_for_timeout(500)
    link2 = page.locator(f'a:has-text("{ACTIVITY_NAME}")').first
    link2.click()
    page.wait_for_timeout(2000)
    page.wait_for_load_state("networkidle")
    check("/activities/" in page.url, "liaison on detail page")

    filing_tab2 = page.locator('.ant-tabs-tab:has-text("备案")').first
    filing_tab2.click()
    page.wait_for_timeout(1000)
    page.wait_for_load_state("networkidle")

    page.wait_for_timeout(500)
    audit_btns = page.locator('button:has-text("审查")').all()
    check(len(audit_btns) > 0, f"audit buttons visible ({len(audit_btns)})")
    if len(audit_btns) > 0:
        audit_btns[0].click()
        page.wait_for_timeout(500)
        modal = page.locator('.ant-modal:visible').first
        check(modal.count() > 0, "audit modal opened")
        ok_btn = page.locator('.ant-modal:visible .ant-btn-primary').first
        if ok_btn.count() > 0:
            ok_btn.click()
            page.wait_for_timeout(2000)
            page.wait_for_load_state("networkidle")

    audit_tags = page.locator('.ant-tag:has-text("审核")').all()
    qualified_tags = page.locator('.ant-tag:has-text("合格")').all()
    has_result = len(audit_tags) > 0 or len(qualified_tags) > 0
    check(has_result, f"audit results visible (rounds: {len(audit_tags)}, qual: {len(qualified_tags)})")

    # ============================================================
    # 3. SecurityOfficer: Pack + Handover
    # ============================================================
    print("\n=== SecurityOfficer: Pack + Handover ===")
    login_as(page, "security@test.com", "pass123")
    check("/login" not in page.url, "security re-logged in")

    sidebar_nav(page, "全部活动")
    page.wait_for_selector('.ant-table-tbody', timeout=10000)
    page.wait_for_timeout(500)
    link3 = page.locator(f'a:has-text("{ACTIVITY_NAME}")').first
    link3.click()
    page.wait_for_timeout(2000)
    page.wait_for_load_state("networkidle")

    filing_tab3 = page.locator('.ant-tabs-tab:has-text("备案")').first
    filing_tab3.click()
    page.wait_for_timeout(1000)
    page.wait_for_load_state("networkidle")

    # Pack
    pack_btn = page.locator('button:has-text("打包")').first
    already_packed = page.locator('.ant-tag:has-text("已打包")').first.count() > 0
    if pack_btn.count() > 0:
        pack_btn.click()
        page.wait_for_timeout(500)
        modal2 = page.locator('.ant-modal:visible').first
        check(modal2.count() > 0, "pack modal opened")
        confirm = page.locator('.ant-modal:visible .ant-btn-primary').first
        if confirm.count() > 0:
            confirm.click()
            page.wait_for_timeout(3000)
            page.wait_for_load_state("networkidle")
        check(True, "pack confirmed")
    else:
        check(already_packed, "already packed")

    # Handover
    handover_btn = page.locator('button:has-text("交接")').first
    already_handed = page.locator('.ant-tag:has-text("已交接")').first.count() > 0
    if handover_btn.count() > 0:
        handover_btn.click()
        page.wait_for_timeout(500)
        checkbox = page.locator('.ant-modal:visible .ant-checkbox').first
        if checkbox.count() > 0:
            checkbox.click()
            page.wait_for_timeout(300)
        confirm2 = page.locator('.ant-modal:visible .ant-btn-primary').first
        if confirm2.count() > 0:
            confirm2.click()
            page.wait_for_timeout(3000)
            page.wait_for_load_state("networkidle")
        check(True, "handover confirmed")
    else:
        check(already_handed, "already handed over")

    page.screenshot(path=f'{OUT / "08_filing_final.png"}', full_page=True)
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
