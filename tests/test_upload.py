import pytest


@pytest.mark.asyncio
async def test_upload_success(client, auth_token, test_project):
    resp = await client.post(
        "/documents/upload",
        headers={"Authorization": f"Bearer {auth_token}"},
        data={"project_id": test_project, "tags": "doc,test"},
        files={"file": ("hello.txt", b"hello world", "text/plain")},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["filename"] == "hello.txt"
    assert data["project_id"] == test_project
    assert data["file_size"] == 11
    assert data["content_type"] == "text/plain"
    assert data["tags"] == ["doc", "test"]
    assert data["minio_path"].startswith(f"projects/{test_project}/")


@pytest.mark.asyncio
async def test_upload_unauthenticated(client, test_project):
    resp = await client.post(
        "/documents/upload",
        data={"project_id": test_project},
        files={"file": ("hello.txt", b"hello", "text/plain")},
    )
    assert resp.status_code == 403
