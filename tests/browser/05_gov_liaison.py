"""GovLiaison scenario: approve, supplement, reject on 备案材料已交接 activities."""
from pathlib import Path
from playwright.sync_api import sync_playwright
from utils import CDP, BASE, create_page, setup_logging, start_recording

OUT = Path(__file__).parent / "screenshots"
failed = 0

def check(cond, msg):
    global failed
    if cond: print(f"  OK: {msg}")
    else: failed += 1; print(f"  FAIL: {msg}")

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

with sync_playwright() as p:
    browser = p.chromium.connect_over_cdp(CDP)
    page = create_page(browser)
    setup_logging("05_gov_liaison")
    recorder = start_recording(page, "05_gov_liaison")
    page.context.clear_cookies()

    errors = []
    page.on("console", lambda m: errors.append(f"[{m.type}] {m.text}"))
    page.on("pageerror", lambda e: errors.append(f"PAGE_ERROR: {e}"))

    # Login
    page.goto(f"{BASE}/login")
    page.wait_for_load_state("networkidle")
    page.fill('input[placeholder="邮箱"]', "tester1@test.com")
    page.fill('input[type="password"]', "pass123")
    page.click('button[type="submit"]')
    page.wait_for_timeout(3000)
    page.wait_for_load_state("networkidle")
    check("/activities" in page.url, "logged in")

    # Find gov_test activities in the list
    sidebar_nav(page, "全部活动")

    # 1. Approve: 审批通过
    print("\n1. Approve (审批通过)")
    gov_rows = page.locator('a:has-text("gov_test_")').all()
    if len(gov_rows) >= 1:
        gov_rows[0].click()
        page.wait_for_timeout(2000)
        page.wait_for_load_state("networkidle")
    check("/activities/" in page.url, f"on detail (got {page.url})")
    check("备案材料已交接" in page.content(), "status is 备案材料已交接")

    approve = page.locator('button:has-text("审批通过")').first
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
    else:
        check(False, "approve button not found")

    # 2. Supplement: 需补充材料
    print("\n2. Supplement (需补充材料)")
    sidebar_nav(page, "全部活动")
    if len(gov_rows) >= 2:
        page.locator('a:has-text("gov_test_")').nth(1).click()
        page.wait_for_timeout(2000)
        page.wait_for_load_state("networkidle")
    supplement = page.locator('button:has-text("需补充材料")').first
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
    else:
        check(False, "supplement button not found")

    # 3. Reject: 驳回—不通过
    print("\n3. Reject (驳回—不通过)")
    sidebar_nav(page, "全部活动")
    if len(gov_rows) >= 3:
        page.locator('a:has-text("gov_test_")').nth(2).click()
        page.wait_for_timeout(2000)
        page.wait_for_load_state("networkidle")
    reject = page.locator('button:has-text("驳回—不通过")').first
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
    else:
        check(False, "reject button not found")

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
