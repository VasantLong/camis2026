import uuid

import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy import text

from app.database import async_session
from app.main import app


@pytest_asyncio.fixture
async def client():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c


@pytest_asyncio.fixture
async def auth_token(client):
    suffix = uuid.uuid4().hex[:8]
    resp = await client.post("/auth/register", json={
        "email": f"test_{suffix}@test.com",
        "password": "test1234",
        "display_name": f"test_{suffix}",
    })
    return resp.json()["access_token"]


@pytest_asyncio.fixture
async def promoter_token(client):
    """用户注册后赋予 Promoter 角色。"""
    suffix = uuid.uuid4().hex[:8]
    resp = await client.post("/auth/register", json={
        "email": f"promoter_{suffix}@test.com",
        "password": "test1234",
        "display_name": f"promoter_{suffix}",
    })
    token = resp.json()["access_token"]
    me = await client.get("/auth/me", headers={"Authorization": f"Bearer {token}"})
    user_id = me.json()["id"]

    async with async_session() as db:
        await db.execute(text(
            "INSERT INTO user_roles (user_id, role_id) "
            "SELECT :uid, id FROM roles WHERE name='Promoter' "
            "ON CONFLICT DO NOTHING"
        ), {"uid": user_id})
        await db.commit()
    return token


@pytest_asyncio.fixture
async def security_token(client):
    """用户注册后赋予 SecurityOfficer 角色。"""
    suffix = uuid.uuid4().hex[:8]
    resp = await client.post("/auth/register", json={
        "email": f"security_{suffix}@test.com",
        "password": "test1234",
        "display_name": f"security_{suffix}",
    })
    token = resp.json()["access_token"]
    me = await client.get("/auth/me", headers={"Authorization": f"Bearer {token}"})
    user_id = me.json()["id"]

    async with async_session() as db:
        await db.execute(text(
            "INSERT INTO user_roles (user_id, role_id) "
            "SELECT :uid, id FROM roles WHERE name IN ('SecurityOfficer', 'SecurityManager') "
            "ON CONFLICT DO NOTHING"
        ), {"uid": user_id})
        await db.commit()
    return token


async def transition(client, token, activity_id, to_status, comment=""):
    """测试辅助：执行状态转换。"""
    resp = await client.put(
        f"/activities/{activity_id}/status",
        headers={"Authorization": f"Bearer {token}"},
        json={"to_status": to_status, "comment": comment},
    )
    return resp


@pytest_asyncio.fixture
async def admin_token(client):
    """用户注册后赋予 AdminStaff 角色。"""
    suffix = uuid.uuid4().hex[:8]
    resp = await client.post("/auth/register", json={
        "email": f"admin_{suffix}@test.com",
        "password": "test1234",
        "display_name": f"admin_{suffix}",
    })
    token = resp.json()["access_token"]
    me = await client.get("/auth/me", headers={"Authorization": f"Bearer {token}"})
    user_id = me.json()["id"]

    async with async_session() as db:
        await db.execute(text(
            "INSERT INTO user_roles (user_id, role_id) "
            "SELECT :uid, id FROM roles WHERE name='AdminStaff' "
            "ON CONFLICT DO NOTHING"
        ), {"uid": user_id})
        await db.commit()
    return token


@pytest_asyncio.fixture
async def test_activity(client, promoter_token):
    """创建一个待设计方案的活动。"""
    me = await client.get("/auth/me", headers={"Authorization": f"Bearer {promoter_token}"})
    user_id = me.json()["id"]

    resp = await client.post("/activities", headers={
        "Authorization": f"Bearer {promoter_token}",
    }, json={
        "name": f"test_activity_{uuid.uuid4().hex[:8]}",
        "type": "测试",
        "estimated_time": "2026-12-31T10:00:00+08:00",
        "location": f"loc_{uuid.uuid4().hex[:6]}",
        "sponsor": "测试主办方",
        "sponsor_contact": "张三",
        "sponsor_phone": "13800138000",
        "deadline": "2026-11-01T18:00:00+08:00",
        "designer_id": user_id,
    })
    return resp.json()["id"]
