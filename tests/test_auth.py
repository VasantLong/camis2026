import uuid

import pytest


@pytest.mark.asyncio
async def test_register_and_login(client):
    suffix = uuid.uuid4().hex[:8]
    username = f"user_{suffix}"

    resp = await client.post("/auth/register", json={
        "username": username,
        "email": f"{username}@test.com",
        "password": "secret123",
    })
    assert resp.status_code == 200
    token = resp.json()["access_token"]
    assert resp.json()["token_type"] == "bearer"

    resp = await client.post("/auth/login", json={
        "username": username,
        "password": "secret123",
    })
    assert resp.status_code == 200
    assert "access_token" in resp.json()


@pytest.mark.asyncio
async def test_me_with_token(auth_token, client):
    resp = await client.get("/auth/me", headers={"Authorization": f"Bearer {auth_token}"})
    assert resp.status_code == 200
    assert resp.json()["username"].startswith("test_")


@pytest.mark.asyncio
async def test_me_without_token(client):
    resp = await client.get("/auth/me")
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_me_invalid_token(client):
    resp = await client.get("/auth/me", headers={"Authorization": "Bearer invalid"})
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_duplicate_register(client):
    suffix = uuid.uuid4().hex[:8]
    username = f"dup_{suffix}"
    body = {"username": username, "email": f"{username}@test.com", "password": "test1234"}

    resp = await client.post("/auth/register", json=body)
    assert resp.status_code == 200

    resp = await client.post("/auth/register", json=body)
    assert resp.status_code == 409


@pytest.mark.asyncio
async def test_login_wrong_password(client, auth_token):
    resp = await client.post("/auth/login", json={"username": "nonexistent", "password": "wrong"})
    assert resp.status_code == 401
