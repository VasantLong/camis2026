import uuid

import pytest


@pytest.mark.asyncio
async def test_register_and_login(client):
    suffix = uuid.uuid4().hex[:8]
    email = f"user_{suffix}@test.com"

    resp = await client.post("/auth/register", json={
        "email": email,
        "password": "secret123",
        "display_name": f"user_{suffix}",
    })
    assert resp.status_code == 200
    token = resp.json()["access_token"]
    assert resp.json()["token_type"] == "bearer"

    resp = await client.post("/auth/login", json={
        "email": email,
        "password": "secret123",
    })
    assert resp.status_code == 200
    assert "access_token" in resp.json()


@pytest.mark.asyncio
async def test_me_with_token(auth_token, client):
    resp = await client.get("/auth/me", headers={"Authorization": f"Bearer {auth_token}"})
    assert resp.status_code == 200
    assert "@test.com" in resp.json()["email"]


@pytest.mark.asyncio
async def test_me_without_token(client):
    resp = await client.get("/auth/me")
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_me_invalid_token(client):
    resp = await client.get("/auth/me", headers={"Authorization": "Bearer invalid"})
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_duplicate_register(client):
    suffix = uuid.uuid4().hex[:8]
    email = f"dup_{suffix}@test.com"
    body = {"email": email, "password": "test1234", "display_name": f"dup_{suffix}"}

    resp = await client.post("/auth/register", json=body)
    assert resp.status_code == 200

    resp = await client.post("/auth/register", json=body)
    assert resp.status_code == 409


@pytest.mark.asyncio
async def test_login_wrong_password(client, auth_token):
    resp = await client.post("/auth/login", json={"email": "nonexistent@test.com", "password": "wrong"})
    assert resp.status_code == 401
