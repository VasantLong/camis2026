import pytest


@pytest.mark.asyncio
async def test_upload_success(client, auth_token, test_activity):
    resp = await client.post(
        "/documents/upload",
        headers={"Authorization": f"Bearer {auth_token}"},
        data={"activity_id": test_activity, "tags": "doc,test"},
        files={"file": ("hello.pdf", b"hello world", "application/pdf")},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["filename"] == "hello.pdf"
    assert data["activity_id"] == test_activity
    assert data["file_size"] == 11
    assert data["content_type"] == "application/pdf"
    assert data["tags"] == ["doc", "test"]
    assert data["minio_path"].startswith(f"activities/{test_activity}/")


@pytest.mark.asyncio
async def test_upload_unauthenticated(client, test_activity):
    resp = await client.post(
        "/documents/upload",
        data={"activity_id": test_activity},
        files={"file": ("hello.pdf", b"hello", "application/pdf")},
    )
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_upload_invalid_format(client, auth_token, test_activity):
    resp = await client.post(
        "/documents/upload",
        headers={"Authorization": f"Bearer {auth_token}"},
        data={"activity_id": test_activity},
        files={"file": ("virus.exe", b"x", "application/x-msdownload")},
    )
    assert resp.status_code == 400
