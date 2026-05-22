import pytest


@pytest.mark.asyncio
async def test_upload_success(client, auth_token, test_activity):
    resp = await client.post(
        "/documents/upload",
        headers={"Authorization": f"Bearer {auth_token}"},
        data={"activity_id": test_activity, "tags": "doc,test"},
        files={"file": ("hello.txt", b"hello world", "text/plain")},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["filename"] == "hello.txt"
    assert data["activity_id"] == test_activity
    assert data["file_size"] == 11
    assert data["content_type"] == "text/plain"
    assert data["tags"] == ["doc", "test"]
    assert data["minio_path"].startswith(f"activities/{test_activity}/")


@pytest.mark.asyncio
async def test_upload_unauthenticated(client, test_activity):
    resp = await client.post(
        "/documents/upload",
        data={"activity_id": test_activity},
        files={"file": ("hello.txt", b"hello", "text/plain")},
    )
    assert resp.status_code == 401
