import pytest

from tests.conftest import transition as _transition


@pytest.mark.asyncio
async def test_validate_empty_materials(client, security_token, test_activity):
    await _transition(client, security_token, test_activity, "待安保方案设计")
    await _transition(client, security_token, test_activity, "待备案申请")

    resp = await client.get(
        f"/activities/{test_activity}/filing/validate",
        headers={"Authorization": f"Bearer {security_token}"},
    )
    assert resp.status_code == 200
    assert resp.json() == []


@pytest.mark.asyncio
async def test_pack_no_materials(client, security_token, test_activity):
    await _transition(client, security_token, test_activity, "待安保方案设计")
    await _transition(client, security_token, test_activity, "待备案申请")

    resp = await client.post(
        f"/activities/{test_activity}/filing/pack",
        headers={"Authorization": f"Bearer {security_token}"},
    )
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_handover(client, security_token, promoter_token, test_activity):
    await _transition(client, security_token, test_activity, "待安保方案设计")
    await _transition(client, security_token, test_activity, "待备案申请")

    await client.post(
        f"/activities/{test_activity}/filing/pack",
        headers={"Authorization": f"Bearer {security_token}"},
    )
    resp = await client.post(
        f"/activities/{test_activity}/filing/handover",
        headers={"Authorization": f"Bearer {security_token}"},
    )
    assert resp.status_code == 200
    assert resp.json()["handover_status"] == "已交接"

    # promoter_token 可查看活动详情，验证状态已变更
    detail = await client.get(f"/activities/{test_activity}", headers={
        "Authorization": f"Bearer {promoter_token}",
    })
    assert detail.json()["status"] == "备案材料已交接"
