"""用户归档：归档后无法登录，取消归档后恢复访问。"""
from pathlib import Path
import json, uuid, urllib.request
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
    hdrs = {"Content-Type": "application/json"}
    if token: hdrs["Authorization"] = f"Bearer {token}"
    req = urllib.request.Request(f"{API}{path}", data=data, headers=hdrs)
    return json.loads(urllib.request.urlopen(req).read())

def api_patch(path, body, token):
    data = json.dumps(body).encode()
    req = urllib.request.Request(f"{API}{path}", data=data, method="PATCH",
        headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"})
    return json.loads(urllib.request.urlopen(req).read())

def api_get(path, token):
    req = urllib.request.Request(f"{API}{path}",
        headers={"Authorization": f"Bearer {token}"})
    return json.loads(urllib.request.urlopen(req).read())

def login_api(email, password):
    resp = api_post("/auth/login", {"email": email, "password": password}, None)
    return resp["access_token"]

# --- Register dynamic user to avoid rate-limit ---
uname = f"archive_test_{uuid.uuid4().hex[:8]}"
email = f"{uname}@test.com"
password = "pass123"
api_post("/auth/register", {"email": email, "password": password, "display_name": uname}, None)
print(f"已注册: {email}")

sa_token = login_api("superadmin@test.com", "pass123")
users = api_get("/admin/users", sa_token)
test_user = next((u for u in users if u["email"] == email), None)
check(test_user is not None, f"找到新用户: {email}")
uid = test_user["id"]
check(test_user["is_active"] == True, "新用户状态正常")

# --- Archive user ---
result = api_post(f"/admin/users/{uid}/archive", {}, sa_token)
check(result.get("message") == "已归档", f"归档成功: {result}")

with sync_playwright() as p:
    browser = p.chromium.connect_over_cdp(CDP)
    page = create_page(browser)
    setup_logging("14_user_archive")
    recorder = start_recording(page, "14_user_archive")
    page.context.clear_cookies()

    errors = []
    page.on("console", lambda m: errors.append(f"[{m.type}] {m.text}"))
    page.on("pageerror", lambda e: errors.append(f"PAGE_ERROR: {e}"))

    # === Step 1: 归档用户无法登录 ===
    print("\n1. 归档用户登录被拦截")
    page.goto(f"{BASE}/login")
    page.wait_for_load_state("networkidle")
    page.fill('input[placeholder="邮箱"]', email)
    page.fill('input[type="password"]', password)
    page.click('button[type="submit"]')
    page.wait_for_timeout(1000)
    still_login = "/login" in page.url
    check(still_login, f"归档用户停留在 /login (got {page.url})")
    check("该账号已被归档" in page.content(), "归档错误提示可见")

    # === Step 2: 取消归档 + 确保活跃 ===
    print("\n2. 取消归档并确保状态正常")
    result2 = api_post(f"/admin/users/{uid}/unarchive", {}, sa_token)
    check(result2.get("message") == "已取消归档", f"取消归档成功: {result2}")
    patch_result = api_patch(f"/admin/users/{uid}/status", {"is_active": True}, sa_token)
    check(patch_result.get("is_active") == True, f"确保活跃: is_active={patch_result.get('is_active')}")
    u = api_get(f"/admin/users/{uid}", sa_token)
    check(u.get("is_active") == True and not u.get("is_archived"), "用户状态正常且未归档")

    # === Step 3: 取消归档后可正常登录 ===
    print("\n3. 取消归档后登录成功")
    page.context.clear_cookies()
    page.goto(f"{BASE}/login")
    page.wait_for_load_state("networkidle")
    page.fill('input[placeholder="邮箱"]', email)
    page.fill('input[type="password"]', password)
    page.click('button[type="submit"]')
    page.wait_for_timeout(3000)
    page.wait_for_load_state("networkidle")
    not_login = "/login" not in page.url
    check(not_login, f"取消归档后离开 /login (got {page.url})")

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
