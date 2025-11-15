import pytest
from datetime import datetime, timedelta, timezone
from sqlalchemy import select, delete
from fastapi import HTTPException
from jose import jwt
from app.models.session_model import Session as UserSession
from app.schemas.user_schema import UserCreate
from app.schemas.session_schema import SessionCreate
from app.services.user_service import UserService
from app.services.session_service import SessionService
from app.config import settings


# -------------------------------------------------------------------
# TEST USER FIXTURE (only fixture kept here)
# -------------------------------------------------------------------

@pytest.fixture
async def test_user(db_session):
    user_in = UserCreate(
        username="auth_tester",
        email="auth@test.com",
        phone_number="+233200000000",
        password="strongpass123"
    )
    user = await UserService.create_user(db_session, user_in=user_in)
    await db_session.commit()
    await db_session.refresh(user)
    return user


# -------------------------------------------------------------------
# 1. LOGIN TESTS
# -------------------------------------------------------------------

@pytest.mark.asyncio
async def test_login_success(async_client, test_user):
    response = await async_client.post(
        "/auth/login",
        params={"email": "auth@test.com", "password": "strongpass123"},
        headers={"user-agent": "pytest", "X-Forwarded-For": "127.0.0.1"},
    )
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert "refresh_token" in data


@pytest.mark.asyncio
async def test_login_failure_wrong_email(async_client):
    res = await async_client.post("/auth/login", params={"email": "nope@test.com", "password": "strongpass123"})
    assert res.status_code == 401


@pytest.mark.asyncio
async def test_login_failure_wrong_password(async_client):
    res = await async_client.post("/auth/login", params={"email": "auth@test.com", "password": "wrong"})
    assert res.status_code == 401


@pytest.mark.asyncio
async def test_login_missing_params(async_client):
    res = await async_client.post("/auth/login", params={"email": "auth@test.com"})
    assert res.status_code == 422


# -------------------------------------------------------------------
# 2. LOGOUT TESTS
# -------------------------------------------------------------------

@pytest.mark.asyncio
async def test_logout_success(async_client, test_user):
    login = await async_client.post("/auth/login", params={"email": "auth@test.com", "password": "strongpass123"})
    tokens = login.json()

    res = await async_client.post(
        "/auth/logout",
        headers={
            "Authorization": f"Bearer {tokens['access_token']}",
            "X-Refresh-Token": tokens["refresh_token"],
        },
    )
    assert res.status_code == 200
    assert res.json()["message"] == "Logged out successfully"


@pytest.mark.asyncio
async def test_logout_missing_refresh_token(async_client, test_user):
    login = await async_client.post("/auth/login", params={"email": "auth@test.com", "password": "strongpass123"})
    tokens = login.json()

    res = await async_client.post(
        "/auth/logout",
        headers={"Authorization": f"Bearer {tokens['access_token']}"},
    )
    assert res.status_code == 400
    assert res.json()["detail"] == "Refresh token missing from headers"


@pytest.mark.asyncio
async def test_logout_invalid_refresh_token(async_client, test_user):
    login = await async_client.post("/auth/login", params={"email": "auth@test.com", "password": "strongpass123"})
    tokens = login.json()

    res = await async_client.post(
        "/auth/logout",
        headers={
            "Authorization": f"Bearer {tokens['access_token']}",
            "X-Refresh-Token": "invalid_token",
        },
    )
    assert res.status_code in (401, 404)


# -------------------------------------------------------------------
# 3. SESSION CREATION & INVALIDATION
# -------------------------------------------------------------------

@pytest.mark.asyncio
async def test_session_created_on_login(db_session, async_client, test_user):
    login = await async_client.post("/auth/login", params={"email": "auth@test.com", "password": "strongpass123"})
    refresh_token = login.json()["refresh_token"]

    result = await db_session.execute(select(UserSession).filter_by(refresh_token=refresh_token))
    session = result.scalar_one_or_none()

    assert session is not None
    assert session.user_id == test_user.id


@pytest.mark.asyncio
async def test_session_invalidated_after_logout(db_session, async_client, test_user):
    login = await async_client.post("/auth/login", params={"email": "auth@test.com", "password": "strongpass123"})
    tokens = login.json()

    await async_client.post(
        "/auth/logout",
        headers={
            "Authorization": f"Bearer {tokens['access_token']}",
            "X-Refresh-Token": tokens["refresh_token"],
        },
    )

    result = await db_session.execute(select(UserSession).filter_by(refresh_token=tokens["refresh_token"]))
    session = result.scalar_one()

    assert session.is_valid is False


# -------------------------------------------------------------------
# 4. REFRESH TOKEN VALIDATION SERVICE
# -------------------------------------------------------------------

@pytest.mark.asyncio
async def test_validate_refresh_token_success(db_session, test_user):
    session_in = SessionCreate(
        user_id=test_user.id,
        refresh_token="validtoken",
        user_agent="pytest",
        ip_address="127.0.0.1",
        expires_at=datetime.now(timezone.utc) + timedelta(days=1),
    )
    await SessionService.create_session(db_session, session_in=session_in)
    await db_session.commit()

    result = await SessionService.validate_refresh_token(db_session, "validtoken", test_user.id)
    result_db = await db_session.execute(select(UserSession).filter_by(refresh_token="validtoken"))
    session = result_db.scalar_one()

    assert session.refresh_token == "validtoken"


@pytest.mark.asyncio
async def test_validate_refresh_token_invalid(db_session, test_user):
    with pytest.raises(HTTPException):
        await SessionService.validate_refresh_token(db_session, "nonexistent", test_user.id)


@pytest.mark.asyncio
async def test_validate_refresh_token_expired(db_session, test_user):
    expired = SessionCreate(
        user_id=test_user.id,
        refresh_token="expiredtoken",
        user_agent="pytest",
        ip_address="127.0.0.1",
        expires_at=datetime.now(timezone.utc) - timedelta(days=1),
    )
    await SessionService.create_session(db_session, session_in=expired)
    await db_session.commit()

    with pytest.raises(HTTPException):
        await SessionService.validate_refresh_token(db_session, "expiredtoken", test_user.id)


# -------------------------------------------------------------------
# 5. TOKEN SIGNATURE TESTS
# -------------------------------------------------------------------

@pytest.mark.asyncio
async def test_access_token_expired_signature(async_client):
    payload = {"sub": "auth@test.com", "exp": datetime.utcnow() - timedelta(seconds=1)}
    expired_token = jwt.encode(payload, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)

    res = await async_client.post(
        "/auth/logout",
        headers={"Authorization": f"Bearer {expired_token}", "X-Refresh-Token": "fake"}
    )
    assert res.status_code in (401, 403)


@pytest.mark.asyncio
async def test_access_token_invalid_signature(async_client):
    payload = {"sub": "auth@test.com", "exp": datetime.utcnow() + timedelta(hours=1)}
    tampered_token = jwt.encode(payload, "WRONG_SECRET", algorithm=settings.JWT_ALGORITHM)

    res = await async_client.post(
        "/auth/logout",
        headers={"Authorization": f"Bearer {tampered_token}", "X-Refresh-Token": "fake"}
    )
    assert res.status_code in (401, 403)


# -------------------------------------------------------------------
# 6. MULTIPLE SESSION BEHAVIOR
# -------------------------------------------------------------------

@pytest.mark.asyncio
async def test_refresh_token_reuse_invalidates_old_session(db_session, async_client, test_user):
    login1 = await async_client.post("/auth/login", params={"email": "auth@test.com", "password": "strongpass123"})
    rt1 = login1.json()["refresh_token"]

    login2 = await async_client.post("/auth/login", params={"email": "auth@test.com", "password": "strongpass123"})
    rt2 = login2.json()["refresh_token"]

    old_sess = (await db_session.execute(select(UserSession).filter_by(refresh_token=rt1))).scalar_one()
    new_sess = (await db_session.execute(select(UserSession).filter_by(refresh_token=rt2))).scalar_one()

    assert old_sess.is_valid is False
    assert new_sess.is_valid is True


@pytest.mark.asyncio
async def test_multiple_concurrent_sessions_allowed(db_session, async_client, test_user):
    await async_client.post("/auth/login", params={"email": "auth@test.com", "password": "strongpass123"})
    await async_client.post("/auth/login", params={"email": "auth@test.com", "password": "strongpass123"})

    result = await db_session.execute(select(UserSession).filter_by(user_id=test_user.id))
    sessions = result.scalars().all()

    assert len(sessions) >= 2


# -------------------------------------------------------------------
# 7. RATE LIMIT MOCK TEST
# -------------------------------------------------------------------

@pytest.mark.asyncio
async def test_brute_force_lockout(monkeypatch, async_client, test_user):
    from app.services import user_service

    attempts = []

    async def fake_increment_attempt(email):
        attempts.append(email)
        if len(attempts) > 5:
            raise HTTPException(status_code=429, detail="Too many failed attempts")

    monkeypatch.setattr(user_service, "increment_failed_attempt", fake_increment_attempt)

    for _ in range(5):
        await async_client.post("/auth/login", params={"email": "auth@test.com", "password": "wrongpass"})

    res = await async_client.post("/auth/login", params={"email": "auth@test.com", "password": "wrongpass"})
    assert res.status_code == 429


# -------------------------------------------------------------------
# 8. CLEANUP
# -------------------------------------------------------------------

@pytest.mark.asyncio
async def test_cleanup_sessions(db_session):
    await db_session.execute(delete(UserSession))
    await db_session.commit()

    remaining = (await db_session.execute(select(UserSession))).scalars().all()
    assert len(remaining) == 0
