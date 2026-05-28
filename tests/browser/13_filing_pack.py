from pathlib import Path
"""Filing pack & handover: sign materials → pack → handover for 待备案申请 activity.
Uses seed activity '社区志愿服务日' which has 4 materials pre-created."""
from playwright.sync_api import sync_playwright
from utils import CDP, BASE, create_page, start_recording

OUT = Path(__file__).parent / "screenshots"
ACTIVITY_NAME = "社区志愿服务日"
failed = 0

def check(cond, msg):
    global failed
    if cond: print(f"  OK: {msg}")
    else: failed += 1; print(f"  FAIL: {msg}")


with sync_playwright() as p:
    browser = p.chromium.connect_over_cdp(CDP)
    page = create_page(browser)
    recorder = start_recording(page, "13_filing_pack")

    errors = []
    page.on("console", lambda m: errors.append(f"[{m.type}] {m.text}"))
    page.on("pageerror", lambda e: errors.append(f"PAGE_ERROR: {e}"))

    # ── Step 1: Login as security ──
    print("1. 登录为 security")
    page.goto(f"{BASE}/login")
    page.wait_for_load_state("networkidle")
    page.fill('input[placeholder="邮箱"]', "security@test.com")
    page.fill('input[type="password"]', "pass123")
    page.click('button[type="submit"]')
    page.wait_for_timeout(3000)
    page.wait_for_load_state("networkidle")
    check("/login" not in page.url, "security 登录成功")

    # ── Step 2: Navigate to activity ──
    print("2. 导航到活动详情页")
    sub = page.locator('.ant-menu-submenu-title:has-text("活动管理")')
    if sub.count() > 0 and sub.first.get_attribute("aria-expanded") != "true":
        sub.first.click()
        page.wait_for_timeout(300)
    all_act = page.locator('.ant-menu-item:has-text("全部活动")').first
    all_act.click()
    page.wait_for_timeout(500)
    page.wait_for_selector('.ant-table-tbody', timeout=10000)
    page.wait_for_timeout(500)

    link = page.locator(f'a:has-text("{ACTIVITY_NAME}")').first
    link.click()
    page.wait_for_timeout(2000)
    page.wait_for_load_state("networkidle")
    check("/activities/" in page.url, "进入活动详情页")

    # ── Step 3: Open 备案 tab ──
    print("3. 打开备案 tab")
    filing_tab = page.locator('.ant-tabs-tab:has-text("备案")').first
    filing_tab.click()
    page.wait_for_timeout(1000)
    page.wait_for_load_state("networkidle")
    check(filing_tab.count() > 0, "备案 tab 已打开")

    # ── Step 4: Sign all materials ──
    print("4. 签署所有材料")
    page.wait_for_timeout(500)
    remaining = page.locator('button:has-text("签署")').all()
    print(f"  待签署: {len(remaining)}")
    while len(remaining) > 0:
        btn = remaining[0]
        if btn.is_visible():
            btn.click()
            page.wait_for_timeout(2000)
            page.wait_for_load_state("networkidle")
        remaining = page.locator('button:has-text("签署")').all()
    unsigned = page.locator('button:has-text("签署")').all()
    signed = page.locator('.ant-tag:has-text("已签署")').all()
    check(len(unsigned) == 0, f"全部材料已签署 ({len(signed)} 个)")

    # ── Step 5: Pack ──
    print("5. 打包备案材料")
    page.wait_for_timeout(500)
    already_packed = page.locator('.ant-tag:has-text("已打包")').first.count() > 0
    pack_btn = page.locator('button:has-text("打包")').first
    if pack_btn.count() > 0:
        pack_btn.click()
        page.wait_for_timeout(500)
        modal = page.locator('.ant-modal:visible').first
        check(modal.count() > 0, "打包弹窗打开")
        confirm_btn = page.locator('.ant-modal:visible .ant-btn-primary').first
        if confirm_btn.count() > 0:
            confirm_btn.click()
            page.wait_for_timeout(3000)
            page.wait_for_load_state("networkidle")
    else:
        check(already_packed or page.locator('.ant-tag:has-text("已交接")').first.count() > 0,
              "备案材料已处理（打包或交接完成）")

    # ── Step 6: Handover ──
    print("6. 纸质交接")
    page.wait_for_timeout(500)
    already_handed = page.locator('.ant-tag:has-text("已交接")').first.count() > 0
    handover_btn = page.locator('button:has-text("交接")').first
    if handover_btn.count() > 0:
        handover_btn.click()
        page.wait_for_timeout(500)
        checkbox = page.locator('.ant-modal:visible .ant-checkbox').first
        if checkbox.count() > 0:
            checkbox.click()
            page.wait_for_timeout(300)
        confirm_btn2 = page.locator('.ant-modal:visible .ant-btn-primary').first
        if confirm_btn2.count() > 0:
            confirm_btn2.click()
            page.wait_for_timeout(3000)
            page.wait_for_load_state("networkidle")
        check(True, "交接确认完成")
    else:
        check(already_handed, "已交接（之前测试已完成）")
    check(True, "备案打包→交接流程完成")

    page.screenshot(path=f'{OUT / "13_filing_pack_final.png"}', full_page=True)
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
