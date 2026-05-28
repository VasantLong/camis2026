from pathlib import Path
"""Document upload: navigate to activity → documents tab → upload file → verify in list."""
import uuid, json, urllib.request
from playwright.sync_api import sync_playwright
from utils import CDP, BASE, create_page, setup_logging, start_recording

API = "http://localhost:8000"
OUT = Path(__file__).parent / "screenshots"
failed = 0

def check(cond, msg):
    global failed
    if cond: print(f"  OK: {msg}")
    else: failed += 1; print(f"  FAIL: {msg}")

# Create a small test file (must be allowed type: pdf/jpg/png/doc/docx)
test_file = Path("/tmp/camis_test_upload.jpg")
test_file.write_text(f"CAMIS test upload {uuid.uuid4().hex[:8]}")

# ── API: create activity for testing ──
def api_post(path, body, token):
    data = json.dumps(body).encode()
    req = urllib.request.Request(f"{API}{path}", data=data,
        headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"})
    return json.loads(urllib.request.urlopen(req).read())

# Get token as devtest
token = api_post("/auth/login",
    {"email": "devtest@test.com", "password": "pass123"}, None)["access_token"]

# Get user ID
req = urllib.request.Request(f"{API}/auth/me",
    headers={"Authorization": f"Bearer {token}"})
user = json.loads(urllib.request.urlopen(req).read())
user_id = user["id"]

# Create test activity
aname = f"doc_upload_{uuid.uuid4().hex[:4]}"
act = api_post("/activities", {
    "name": aname, "type": "大型活动",
    "estimated_time": "2026-07-01T09:00:00+08:00",
    "location": "测试广场", "sponsor": "测试主办方",
    "deadline": "2026-06-15T18:00:00+08:00",
    "designer_id": user_id,
}, token)
aid = act["id"]
print(f"Created activity: {aname} (id={aid[:8]}...)")

with sync_playwright() as p:
    browser = p.chromium.connect_over_cdp(CDP)
    page = create_page(browser)
    setup_logging("12_document_upload")
    recorder = start_recording(page, "12_document_upload")

    errors = []
    page.on("console", lambda m: errors.append(f"[{m.type}] {m.text}"))
    page.on("pageerror", lambda e: errors.append(f"PAGE_ERROR: {e}"))

    # ── Step 1: Login ──
    print("1. 登录")
    page.goto(f"{BASE}/login")
    page.wait_for_load_state("networkidle")
    page.fill('input[placeholder="邮箱"]', "devtest@test.com")
    page.fill('input[type="password"]', "pass123")
    page.click('button[type="submit"]')
    page.wait_for_timeout(3000)
    page.wait_for_load_state("networkidle")
    check("/login" not in page.url, "登录成功")

    # ── Step 2: Navigate to activity detail ──
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

    link = page.locator(f'a:has-text("{aname}")').first
    link.click()
    page.wait_for_timeout(2000)
    page.wait_for_load_state("networkidle")
    check(f"/activities/{aid}" in page.url, f"进入活动详情页")

    # ── Step 3: Click "文档" tab ──
    print("3. 打开文档 tab")
    doc_tab = page.locator('.ant-tabs-tab:has-text("文档")').first
    doc_tab.click()
    page.wait_for_timeout(1000)
    page.wait_for_load_state("networkidle")
    check(doc_tab.count() > 0, "文档 tab 已打开")

    # ── Step 4: Upload file ──
    print("4. 上传文件")
    # Click the upload button inside the Upload component
    upload_btn = page.locator('button:has-text("选择文件上传")').first
    check(upload_btn.count() > 0, "上传按钮存在")
    if upload_btn.count() > 0:
        with page.expect_file_chooser() as fc_info:
            upload_btn.click()
        file_chooser = fc_info.value
        file_chooser.set_files(str(test_file))
        page.wait_for_timeout(5000)
        page.wait_for_load_state("networkidle")

    # ── Step 5: Verify file appears in list ──
    print("5. 验证文件出现在列表中")
    page.wait_for_timeout(2000)
    # Debug: check what's displayed in the document tab
    doc_content = page.locator('.ant-tabs-tabpane-active').first.inner_text()[:500]
    print(f"  doc tab content: {doc_content[:200]}")
    found = test_file.name in doc_content
    check(found, f"文件 '{test_file.name}' 出现在文档列表中")

    # Cleanup
    test_file.unlink(missing_ok=True)

    page.screenshot(path=f'{OUT / "12_document_upload_final.png"}', full_page=True)
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
