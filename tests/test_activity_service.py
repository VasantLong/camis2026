import uuid

import pytest


@pytest.mark.asyncio
async def test_create_activity(client, promoter_token):
    me = await client.get("/auth/me", headers={"Authorization": f"Bearer {promoter_token}"})
    uid = me.json()["id"]
    resp = await client.post("/activities", headers={
        "Authorization": f"Bearer {promoter_token}",
    }, json={
        "name": "测试活动",
        "type": "大型",
        "estimated_time": "2026-12-31T10:00:00+08:00",
        "location": "测试场地A",
        "sponsor": "测试主办方",
        "deadline": "2026-11-01T18:00:00+08:00",
        "designer_id": uid,
    })
    assert resp.status_code == 201
    data = resp.json()
    assert data["status"] == "待设计方案"
    assert data["name"] == "测试活动"


@pytest.mark.asyncio
async def test_create_activity_past_deadline(client, promoter_token):
    me = await client.get("/auth/me", headers={"Authorization": f"Bearer {promoter_token}"})
    uid = me.json()["id"]
    resp = await client.post("/activities", headers={
        "Authorization": f"Bearer {promoter_token}",
    }, json={
        "name": "测试",
        "type": "大型",
        "estimated_time": "2026-12-31T10:00:00+08:00",
        "location": "场地B",
        "sponsor": "主办方",
        "deadline": "2020-01-01T00:00:00+08:00",
        "designer_id": uid,
    })
    assert resp.status_code == 400


@pytest.mark.asyncio
async def test_list_activities(client, promoter_token):
    resp = await client.get("/activities", headers={
        "Authorization": f"Bearer {promoter_token}",
    })
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data, dict)
    assert "items" in data
    assert "total" in data


@pytest.mark.asyncio
async def test_get_activity_detail(client, promoter_token, test_activity):
    resp = await client.get(f"/activities/{test_activity}", headers={
        "Authorization": f"Bearer {promoter_token}",
    })
    assert resp.status_code == 200
    assert resp.json()["id"] == test_activity


@pytest.mark.asyncio
async def test_get_status_history(client, promoter_token, test_activity):
    resp = await client.get(f"/activities/{test_activity}/history", headers={
        "Authorization": f"Bearer {promoter_token}",
    })
    assert resp.status_code == 200
    history = resp.json()
    assert len(history) == 1
    assert history[0]["to_status"] == "待设计方案"


@pytest.mark.asyncio
async def test_no_role_user_forbidden(client, auth_token):
    me = await client.get("/auth/me", headers={"Authorization": f"Bearer {auth_token}"})
    uid = me.json()["id"]
    resp = await client.post("/activities", headers={
        "Authorization": f"Bearer {auth_token}",
    }, json={
        "name": "x", "type": "x",
        "estimated_time": "2026-12-31T10:00:00+08:00",
        "location": "x", "sponsor": "x",
        "deadline": "2026-11-01T18:00:00+08:00",
        "designer_id": uid,
    })
    assert resp.status_code == 403
