"""
CleanTrack AI — Auth Endpoint Tests
"""
import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_register_success(client: AsyncClient):
    resp = await client.post("/api/v1/auth/register", json={
        "email": "new@test.com",
        "full_name": "New User",
        "password": "Password1",
        "role": "citizen",
    })
    assert resp.status_code == 201
    data = resp.json()
    assert data["email"] == "new@test.com"
    assert data["role"] == "citizen"
    assert "hashed_password" not in data


@pytest.mark.asyncio
async def test_register_duplicate_email(client: AsyncClient):
    payload = {
        "email": "dup@test.com",
        "full_name": "Dup User",
        "password": "Password1",
        "role": "citizen",
    }
    await client.post("/api/v1/auth/register", json=payload)
    resp = await client.post("/api/v1/auth/register", json=payload)
    assert resp.status_code == 409


@pytest.mark.asyncio
async def test_login_success(client: AsyncClient):
    await client.post("/api/v1/auth/register", json={
        "email": "login@test.com",
        "full_name": "Login User",
        "password": "Password1",
    })
    resp = await client.post("/api/v1/auth/login", json={
        "email": "login@test.com",
        "password": "Password1",
    })
    assert resp.status_code == 200
    data = resp.json()
    assert "access_token" in data
    assert "refresh_token" in data
    assert data["token_type"] == "bearer"


@pytest.mark.asyncio
async def test_login_wrong_password(client: AsyncClient):
    await client.post("/api/v1/auth/register", json={
        "email": "wrong@test.com",
        "full_name": "Wrong User",
        "password": "Password1",
    })
    resp = await client.post("/api/v1/auth/login", json={
        "email": "wrong@test.com",
        "password": "WrongPass1",
    })
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_get_me(client: AsyncClient, citizen_token: str):
    resp = await client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {citizen_token}"},
    )
    assert resp.status_code == 200
    assert resp.json()["role"] == "citizen"


@pytest.mark.asyncio
async def test_weak_password_rejected(client: AsyncClient):
    resp = await client.post("/api/v1/auth/register", json={
        "email": "weak@test.com",
        "full_name": "Weak",
        "password": "password",  # No uppercase, no digit
    })
    assert resp.status_code == 422
