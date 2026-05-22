import pytest


@pytest.mark.asyncio
async def test_panel_data(client, admin_token):
    resp = await client.get("/dashboard", headers={
        "Authorization": f"Bearer {admin_token}",
    })
    assert resp.status_code == 200
    data = resp.json()
    assert "total" in data
    assert "by_status" in data
    assert "compliance_rate" in data
    assert "recent_anomalies" in data
    assert data["total"] >= 0


@pytest.mark.asyncio
async def test_activity_detail(client, admin_token, test_activity):
    resp = await client.get(f"/dashboard/activities/{test_activity}", headers={
        "Authorization": f"Bearer {admin_token}",
    })
    assert resp.status_code == 200
    data = resp.json()
    assert data["activity"]["id"] == test_activity
    assert len(data["status_history"]) >= 1


@pytest.mark.asyncio
async def test_monthly_report(client, admin_token):
    resp = await client.post("/dashboard/reports/monthly", headers={
        "Authorization": f"Bearer {admin_token}",
    }, json={"month": "2026-01"})
    assert resp.status_code == 200
    assert "report_url" in resp.json()
