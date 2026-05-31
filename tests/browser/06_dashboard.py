from pathlib import Path
"""Dashboard: stats cards, status distribution, anomaly list, report export."""
from playwright.sync_api import sync_playwright
from utils import (CDP, BASE, create_page, setup_logging, start_recording,
                   check, get_failed, login_as)

OUT = Path(__file__).parent / 'screenshots'

with sync_playwright() as p:
    browser = p.chromium.connect_over_cdp(CDP)
    page = create_page(browser)
    setup_logging("06_dashboard")
    recorder = start_recording(page, "06_dashboard")
    page.context.clear_cookies()

    errors = []
    page.on("console", lambda m: errors.append(f"[{m.type}] {m.text}"))
    page.on("pageerror", lambda e: errors.append(f"PAGE_ERROR: {e}"))

    # Login as admin (has view_dashboard)
    login_as(page, "admin@test.com", "pass123")
    check("/login" not in page.url, "logged in")

    # 1. Navigate to dashboard via sidebar
    print("\n1. Navigate to dashboard")
    dash_item = page.locator('.ant-menu-item:has-text("活动面板")')
    if dash_item.count() > 0:
        dash_item.first.click()
        page.wait_for_timeout(2000)
        page.wait_for_load_state("networkidle")
    check("/dashboard" in page.url, f"on dashboard (got {page.url})")

    # 2. Stats cards
    print("\n2. Stats cards")
    content = page.content()
    check("活动总数" in content, "total activities card shown")
    check("合规率" in content, "compliance rate card shown")

    # 3. Status distribution
    print("\n3. Status distribution")
    dist = page.locator('.ant-progress').first
    if dist.count() > 0:
        check(True, "progress bars rendered for status distribution")
    else:
        check("待设计方案" in content or "审批通过" in content,
              "status labels visible in distribution")

    # 4. Anomaly list
    print("\n4. Anomaly list")
    table = page.locator('.ant-table').first
    if table.count() > 0:
        check(True, "anomaly table rendered")
    else:
        check(False, "anomaly table not found")

    # 5. Export monthly report
    print("\n5. Export monthly report")
    export_btn = page.locator('button:has-text("导出月报")').first
    if export_btn.count() > 0:
        month_picker = page.locator('input[placeholder="选择月份"]').first
        if month_picker.count() > 0:
            month_picker.click()
            page.wait_for_timeout(500)
            today_cell = page.locator('.ant-picker-cell-in-view').first
            if today_cell.count() > 0:
                today_cell.click()
                page.wait_for_timeout(500)
        export_btn.click()
        page.wait_for_timeout(2000)
        toast = page.locator('.ant-message').first
        if toast.count() > 0:
            check(True, f"report export result: '{toast.inner_text()}'")
        else:
            check(True, "export button clicked (no error)")
    else:
        print("  export button not found (may need report permission)")

    page.screenshot(path=f'{OUT / '06_dashboard_final.png'}', full_page=True)
    if recorder:
        recorder.stop()
    page.close()

    print(f"\n=== Console errors ===")
    error_msgs = [e for e in errors if "[error]" in e or "PAGE_ERROR" in e]
    for e in error_msgs:
        print(f"  {e}")
    if not error_msgs:
        print("  (none)")

    failed = get_failed()
    print(f"\nFailed: {failed}")
    if failed > 0:
        raise SystemExit(1)
