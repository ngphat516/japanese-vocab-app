import jwt
import pytest
from sqlalchemy import select

from app.core.exceptions import AppError
from app.core.security import hasher
from app.modules.auth.models import User
from app.modules.auth.service import require_admin
from tests.conftest import auth


async def test_AUTH_01_register_argon2(client, db):
    response = await client.post(
        "/api/v1/auth/register", json={"email": "a@example.com", "password": "password123"}
    )
    assert response.status_code == 201
    user = await db.scalar(select(User))
    assert user.password_hash.startswith("$argon2")
    assert hasher.verify(user.password_hash, "password123")
    assert "password_hash" not in response.json()
    assert (
        await client.post(
            "/api/v1/auth/register", json={"email": "a@example.com", "password": "password123"}
        )
    ).status_code == 409
    assert (
        await client.post("/api/v1/auth/register", json={"email": "x", "password": "x"})
    ).status_code == 422


async def test_AUTH_02_login_expiry(client):
    _, tokens = await auth(client)
    access = jwt.decode(tokens["access_token"], options={"verify_signature": False})
    refresh = jwt.decode(tokens["refresh_token"], options={"verify_signature": False})
    assert access["exp"] - access["iat"] == 15 * 60
    assert refresh["exp"] - refresh["iat"] == 7 * 86400
    assert (
        await client.post(
            "/api/v1/auth/login", json={"email": "a@example.com", "password": "wrong"}
        )
    ).status_code == 401
    assert (
        await client.post(
            "/api/v1/auth/login", json={"email": "missing@example.com", "password": "wrong"}
        )
    ).status_code == 401


async def test_AUTH_03_refresh_rotate_logout(authorized):
    client, tokens = authorized
    rotated = await client.post(
        "/api/v1/auth/refresh", json={"refresh_token": tokens["refresh_token"]}
    )
    assert rotated.status_code == 200
    assert rotated.json()["refresh_token"] != tokens["refresh_token"]
    assert (
        await client.post("/api/v1/auth/refresh", json={"refresh_token": tokens["refresh_token"]})
    ).status_code == 401
    assert (
        await client.post(
            "/api/v1/auth/logout", json={"refresh_token": rotated.json()["refresh_token"]}
        )
    ).status_code == 200
    assert (
        await client.post(
            "/api/v1/auth/refresh", json={"refresh_token": rotated.json()["refresh_token"]}
        )
    ).status_code == 401
    assert (
        await client.post("/api/v1/auth/refresh", json={"refresh_token": tokens["access_token"]})
    ).status_code == 401


async def test_AUTH_04_profile(authorized):
    client, _ = authorized
    assert (await client.get("/api/v1/me")).json()["email"] == "a@example.com"
    assert (await client.patch("/api/v1/me", json={"display_name": "Tên mới"})).json()[
        "display_name"
    ] == "Tên mới"
    client.headers.clear()
    assert (await client.get("/api/v1/me")).status_code == 401
    client.headers["Authorization"] = "Bearer invalid"
    assert (await client.get("/api/v1/me")).status_code == 401


async def test_AUTH_05_roles(authorized, db):
    client, _ = authorized
    assert (
        await client.post("/api/v1/textbooks", json={"name": "Public", "visibility": "public"})
    ).status_code == 403
    user = await db.scalar(select(User))
    with pytest.raises(AppError):
        require_admin(user)
    user.role = "admin"
    await db.flush()
    assert require_admin(user) is user
    assert (
        await client.post("/api/v1/textbooks", json={"name": "Public", "visibility": "public"})
    ).status_code == 201
    assert (
        await client.post(
            "/api/v1/auth/register",
            json={"email": "b@example.com", "password": "password123", "role": "admin"},
        )
    ).status_code == 422
