import uuid

import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from app.main import app


@pytest_asyncio.fixture
async def client():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c


@pytest_asyncio.fixture
async def auth_token(client):
    suffix = uuid.uuid4().hex[:8]
    username = f"test_{suffix}"
    resp = await client.post("/auth/register", json={
        "username": username,
        "email": f"{username}@test.com",
        "password": "test1234",
    })
    return resp.json()["access_token"]
