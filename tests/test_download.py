import pytest


@pytest.mark.asyncio
async def test_download_redirect(client, auth_token, test_activity):
    upload_resp = await client.post(
        "/documents/upload",
        headers={"Authorization": f"Bearer {auth_token}"},
        data={"activity_id": test_activity},
        files={"file": ("data.pdf", b"test content", "application/pdf")},
    )
    doc_id = upload_resp.json()["id"]

    resp = await client.get(
        f"/documents/{doc_id}",
        headers={"Authorization": f"Bearer {auth_token}"},
        follow_redirects=False,
    )
    assert resp.status_code == 302
    assert resp.headers["location"].startswith("http://")


@pytest.mark.asyncio
async def test_download_not_found(client, auth_token):
    resp = await client.get(
        "/documents/00000000-0000-0000-0000-000000000000",
        headers={"Authorization": f"Bearer {auth_token}"},
    )
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_list_activity_documents(client, promoter_token, test_activity):
    for i in range(2):
        await client.post(
            "/documents/upload",
            headers={"Authorization": f"Bearer {promoter_token}"},
            data={"activity_id": test_activity},
            files={"file": (f"doc{i}.pdf", f"content {i}", "application/pdf")},
        )

    resp = await client.get(
        f"/activities/{test_activity}/documents",
        headers={"Authorization": f"Bearer {promoter_token}"},
    )
    assert resp.status_code == 200
    docs = resp.json()
    assert len(docs) >= 2
