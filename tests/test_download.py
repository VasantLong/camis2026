import pytest


@pytest.mark.asyncio
async def test_download_redirect(client, auth_token, test_project):
    # Upload first
    upload_resp = await client.post(
        "/documents/upload",
        headers={"Authorization": f"Bearer {auth_token}"},
        data={"project_id": test_project},
        files={"file": ("data.txt", b"test content", "text/plain")},
    )
    doc_id = upload_resp.json()["id"]

    # Download — should redirect
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
async def test_list_project_documents(client, auth_token, test_project):
    # Upload two files
    for i in range(2):
        await client.post(
            "/documents/upload",
            headers={"Authorization": f"Bearer {auth_token}"},
            data={"project_id": test_project},
            files={"file": (f"doc{i}.txt", f"content {i}", "text/plain")},
        )

    resp = await client.get(
        f"/documents/project/{test_project}",
        headers={"Authorization": f"Bearer {auth_token}"},
    )
    assert resp.status_code == 200
    docs = resp.json()
    assert len(docs) >= 2
    assert all(d["project_id"] == test_project for d in docs)
