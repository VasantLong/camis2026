import pytest
from sqlalchemy import text

from app.database import async_session
from tests.conftest import transition as _transition


@pytest.mark.asyncio
async def test_valid_transition(client, security_token, test_activity):
    resp = await _transition(client, security_token, test_activity, "待安保方案设计")
    assert resp.status_code == 200
    data = resp.json()
    assert data["from_status"] == "待设计方案"
    assert data["to_status"] == "待安保方案设计"


@pytest.mark.asyncio
async def test_invalid_transition(client, security_token, test_activity):
    resp = await _transition(client, security_token, test_activity, "审批通过")
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_reject_loop(client, security_token, test_activity):
    await _transition(client, security_token, test_activity, "待安保方案设计")
    resp = await client.post(
        f"/activities/{test_activity}/reject",
        headers={"Authorization": f"Bearer {security_token}"},
        json={"reason": "安保人员不足"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["from_status"] == "待安保方案设计"
    assert data["to_status"] == "待安保方案设计"


@pytest.mark.asyncio
async def test_force_cancel(client, admin_token, test_activity):
    resp = await client.post(
        f"/activities/{test_activity}/force-cancel",
        headers={"Authorization": f"Bearer {admin_token}"},
        json={"reason": "暴雨取消"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["to_status"] == "已取消"

    # 验证 implementation_records 已写入
    async with async_session() as db:
        result = await db.execute(text(
            "SELECT change_status, change_reason FROM implementation_records WHERE activity_id = :aid"
        ), {"aid": test_activity})
        row = result.fetchone()
        assert row is not None
        assert row[0] == "已取消"


@pytest.mark.asyncio
async def test_promoter_cannot_manage_security(client, promoter_token, test_activity):
    resp = await _transition(client, promoter_token, test_activity, "待安保方案设计")
    assert resp.status_code == 403
