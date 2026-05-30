"""User archive: archived user cannot login, unarchive restores access."""
from pathlib import Path
import json, urllib.request
from playwright.sync_api import sync_playwright
from utils import CDP, BASE, create_page, setup_logging, start_recording

API = "http://localhost:8000"
OUT = Path(__file__).parent / "screenshots"
failed = 0

def check(cond, msg):
    global failed
    if cond: print(f"  OK: {msg}")
    else: failed += 1; print(f"  FAIL: {msg}")

# --- API helpers ---
def api_post(path, body, token):
    data = json.dumps(body).encode()
    req = urllib.request.Request(f"{API}{path}", data=data,
        headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"})
    return json.loads(urllib.request.urlopen(req).read())

def api_get(path, token):
    req = urllib.request.Request(f"{API}{path}",
        headers={"Authorization": f"Bearer {token}"})
    return json.loads(urllib.request.urlopen(req).read())

def login_api(email, password):
    resp = api_post("/auth/login", {"email": email, "password": password}, None)
    return resp["access_token"]

# --- Archive testuser via API ---
sa_token = login_api("superadmin@test.com", "pass123")
users = api_get("/admin/users", sa_token)
test_user = next((u for u in users if u["email"] == "testuser@test.com"), None)
check(test_user is not None, "testuser found in user list")
uid = test_user["id"]

result = api_post(f"/admin/users/{uid}/archive", {}, sa_token)
check(result.get("message") == "已归档", f"archive success: {result}")

with sync_playwright() as p:
    browser = p.chromium.connect_over_cdp(CDP)
    page = create_page(browser)
    setup_logging("14_user_archive")
    recorder = start_recording(page, "14_user_archive")
    page.context.clear_cookies()

    errors = []
    page.on("console", lambda m: errors.append(f"[{m.type}] {m.text}"))
    page.on("pageerror", lambda e: errors.append(f"PAGE_ERROR: {e}"))

    # === Step 1: Archived user cannot login ===
    print("\n1. Archived user login blocked")
    page.goto(f"{BASE}/login")
    page.wait_for_load_state("networkidle")
    page.fill('input[placeholder="邮箱"]', "testuser@test.com")
    page.fill('input[type="password"]', "pass123")
    page.click('button[type="submit"]')
    page.wait_for_timeout(3000)
    still_login = "/login" in page.url
    check(still_login, f"stayed on /login after archive login attempt (got {page.url})")
    toast = page.locator('.ant-message').filter(has_text="已归档").first
    check(toast.count() > 0, "archive error toast visible")

    # === Step 2: Unarchive ===
    print("\n2. Unarchive testuser")
    result2 = api_post(f"/admin/users/{uid}/unarchive", {}, sa_token)
    check(result2.get("message") == "已取消归档", f"unarchive success: {result2}")

    # === Step 3: Unarchived user can login ===
    print("\n3. Unarchived user login succeeds")
    page.context.clear_cookies()
    page.goto(f"{BASE}/login")
    page.wait_for_load_state("networkidle")
    page.fill('input[placeholder="邮箱"]', "testuser@test.com")
    page.fill('input[type="password"]', "pass123")
    page.click('button[type="submit"]')
    page.wait_for_timeout(3000)
    page.wait_for_load_state("networkidle")
    not_login = "/login" not in page.url
    check(not_login, f"redirected away from /login after unarchive (got {page.url})")

    page.screenshot(path=f"{OUT / '14_user_archive_final.png'}", full_page=True)
    if recorder:
        recorder.stop()
    page.close()

    print(f"\n=== Console errors ===")
    error_msgs = [e for e in errors if "[error]" in e or "PAGE_ERROR" in e]
    if error_msgs:
        for e in error_msgs:
            print(f"  {e}")
    else:
        print("  (none)")

    print(f"\nFailed: {failed}")
    if failed > 0:
        raise SystemExit(1)
