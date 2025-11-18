# tests/test_users_refactor.py
import uuid
from typing import Any, Callable, Dict, Optional

import pytest
from fastapi import HTTPException
from pydantic import ValidationError

from app.utils.password import hash_password, verify_password
from app.services.auth_service import AuthService
from app.models.user_model import User, UserStatus
from app.schemas.user_schema import UserCreate, UserUpdate
from app.services.user_service import UserService


# ----------------------
# Helper: find hashed password attr on returned model
# ----------------------
def _get_hashed_password_field(user_obj: Any) -> Optional[str]:
    """Return the hashed password string from a User ORM/Pydantic object."""
    # common names used across codebases
    for attr in ("password", "hashed_password", "pwd_hash"):
        val = getattr(user_obj, attr, None)
        if isinstance(val, str) and val:
            return val
    return None


# ----------------------
# Factories
# ----------------------
@pytest.fixture
def db_user_factory(db_session) -> Callable[..., Any]:
    """
    Factory to create users directly in the DB (service layer).
    Usage:
        user = await db_user_factory(username="x", email="y@test.com")
    """
    async def _create(
        username: str = "user",
        email: str = None,
        phone_number: str = "000000000",
        password: str = "password123",
        **overrides
    ) -> User:
        if email is None:
            email = f"{username}@example.com"
        user_in = UserCreate(
            username=username,
            email=email,
            phone_number=phone_number,
            password=password,
            **overrides
        )
        return await UserService.create_user(db_session, user_in=user_in)
    return _create


@pytest.fixture
def api_user_factory(async_client) -> Callable[..., Any]:
    """
    Factory to create users via the API endpoint.
    Usage:
        user = await api_user_factory(username="x", email="y@test.com")
    Returns the response json as dict.
    """
    async def _create(
        username: str = "api_user",
        email: str = None,
        phone_number: str = "000000000",
        password: str = "password123",
        **overrides
    ) -> Dict[str, Any]:
        if email is None:
            email = f"{username}@example.com"
        user_in = UserCreate(
            username=username,
            email=email,
            phone_number=phone_number,
            password=password,
            **overrides
        )
        resp = await async_client.post("/users/", json=user_in.model_dump())
        assert resp.status_code in (200, 201), f"unexpected status: {resp.status_code}, body: {resp.text}"
        return resp.json()
    return _create


# ----------------------
# Classes of tests
# ----------------------
class TestUserCreationService:
    """Service-level tests (use db_user_factory)"""

    @pytest.mark.asyncio
    async def test_create_user_success(self, db_user_factory):
        user = await db_user_factory(
            username="auth_tester",
            email="auth@test.com",
            phone_number="+233200000000",
            password="strongpass123",
        )

        assert user.username == "auth_tester"
        assert user.email == "auth@test.com"
        assert str(user.id)

        hashed = _get_hashed_password_field(user)
        assert hashed is not None, "no hashed password field found on user"
        assert verify_password("strongpass123", hashed)

        # Default status expectation
        assert user.status == UserStatus.PENDING_KYC

    @pytest.mark.asyncio
    async def test_create_user_duplicate_email_raises(self, db_user_factory):
        await db_user_factory(username="first", email="dup@example.com")
        with pytest.raises(HTTPException):
            await db_user_factory(username="second", email="dup@example.com")

    @pytest.mark.asyncio
    async def test_create_user_duplicate_username_raises(self, db_user_factory):
        await db_user_factory(username="taken_user", email="a@example.com")
        with pytest.raises(HTTPException):
            await db_user_factory(username="taken_user", email="b@example.com")



class TestUserApiEndpoints:
    """API-level tests (use async_client & api_user_factory)"""

    @pytest.mark.asyncio
    async def test_list_users(self, async_client, api_user_factory, auth_override):
        # ensure at least one user exists
        await api_user_factory(username="list_one", email="list_one@test.com")
        resp = await async_client.get("/users/")
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, list)
        assert len(data) >= 1

    @pytest.mark.asyncio
    async def test_get_user_by_id_success(self, db_user_factory, async_client, auth_override):
        user = await db_user_factory(username="fetch_user", email="fetch@test.com")
        resp = await async_client.get(f"/users/{user.id}")
        assert resp.status_code == 200
        payload = resp.json()
        assert payload["id"] == str(user.id)

    @pytest.mark.asyncio
    async def test_get_user_not_found(self, async_client, auth_override):
        resp = await async_client.get(f"/users/{uuid.uuid4()}")
        assert resp.status_code == 404

    @pytest.mark.asyncio
    async def test_update_user_success(self, db_user_factory, async_client, auth_override):
        user = await db_user_factory(username="update_me", email="update_me@test.com")
        update_in = UserUpdate(username="updated_name")

        resp = await async_client.put(
            f"/users/{user.id}",
            json=update_in.model_dump(exclude_unset=True),
        )

        assert resp.status_code == 200
        assert resp.json()["username"] == "update_me"

    @pytest.mark.asyncio
    async def test_update_user_duplicate_email(self, db_user_factory, async_client, auth_override):
        u1 = await db_user_factory(username="u1", email="one@test.com")
        u2 = await db_user_factory(username="u2", email="two@test.com")

        update_in = UserUpdate(email="one@test.com")  # conflict with u1

        resp = await async_client.put(
            f"/users/{u2.id}",
            json=update_in.model_dump(exclude_unset=True),
        )

        assert resp.status_code == 400
        assert "Email already registered" in resp.text

    @pytest.mark.asyncio
    async def test_delete_user_success(self, db_user_factory, async_client, auth_override):
        user = await db_user_factory(username="to_delete", email="del@test.com")
        resp = await async_client.delete(f"/users/{user.id}")
        assert resp.status_code == 204

    @pytest.mark.asyncio
    async def test_delete_user_not_found(self, async_client, auth_override):
        resp = await async_client.delete(f"/users/{uuid.uuid4()}")
        assert resp.status_code == 404


class TestPasswordUtilities:
    def test_password_hashing_and_verify(self):
        password = "securePass!"
        hashed = hash_password(password)
        assert hashed != password
        assert verify_password(password, hashed)

    def test_invalid_password_verify_fails(self):
        password = "securePass!"
        hashed = hash_password(password)
        assert not verify_password("wrongPass!", hashed)


class TestValidationAndSchema:
    """Tests that exercise Pydantic schema validation via UserCreate/UserUpdate"""

    @pytest.mark.parametrize("bad_email", ["not-an-email", "no-at-symbol", "a@b", ""])
    def test_usercreate_invalid_emails_raise(self, bad_email):
        with pytest.raises(ValidationError):
            UserCreate(
                username="bademail",
                email=bad_email,
                phone_number="321321321",
                password="password123",
            )

    @pytest.mark.parametrize("short_pass", ["", "1", "12", "123", "pw"])
    def test_usercreate_short_password_raises(self, short_pass):
        with pytest.raises(ValidationError):
            UserCreate(
                username="shortpass",
                email="shortpass@example.com",
                phone_number="123123123",
                password=short_pass,
            )


class TestAuthentication:
    @pytest.mark.asyncio
    async def test_authenticate_user_invalid_credentials(self, db_session):
        user = User(
            username="auth_user",
            email="auth@example.com",
            phone_number="123123123",
            hashed_password=hash_password("correctpass"),
            status=UserStatus.PENDING_KYC,
        )

        db_session.add(user)
        await db_session.commit()
        await db_session.refresh(user)

        with pytest.raises(HTTPException) as excinfo:
            await AuthService.authenticate_user(
                db_session,
                identifier="auth@example.com",
                password="wrongpass",
            )

        assert excinfo.value.status_code == 401
        assert "Invalid login credentials" in str(excinfo.value.detail)
