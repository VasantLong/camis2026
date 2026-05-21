import uuid

import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from app.database import async_session
from app.main import app
from app.models.project import Project


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


@pytest_asyncio.fixture
async def test_project(client, auth_token):
    resp = await client.get("/auth/me", headers={"Authorization": f"Bearer {auth_token}"})
    user_id = resp.json()["id"]

    async with async_session() as db:
        project = Project(name=f"project_{uuid.uuid4().hex[:8]}", owner_id=user_id)
        db.add(project)
        await db.commit()
        await db.refresh(project)
        return str(project.id)
