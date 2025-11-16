import uuid
import pytest
from fastapi import status
from app.utils.password import hash_password, verify_password
from app.services.auth_service import AuthService
from fastapi import HTTPException
from app.models.user_model import User


# =====================================================================
# 1. CREATE USER (SUCCESS)
# =====================================================================
@pytest.mark.asyncio
async def test_create_user_success(async_client):
    payload = {
        "username": "john_doe",
        "email": "john@example.com",
        "phone_number": "123456789",
        "password": "password123",

    }
    response = await async_client.post("/users/", json=payload)
    assert response.status_code == status.HTTP_201_CREATED
    data = response.json()
    assert data["username"] == "john_doe"
    assert data["email"] == "john@example.com"
    assert "id" in data


# =====================================================================
# 2. CREATE USER (DUPLICATE EMAIL)
# =====================================================================
@pytest.mark.asyncio
async def test_create_user_duplicate_email(async_client):
    payload = {
        "username": "jane_doe",
        "email": "john@example.com",
        "phone_number": "987654321",
        "password": "password123",
    }
    response = await async_client.post("/users/", json=payload)
    assert response.status_code == 400
    assert "Email already registered" in response.text


# =====================================================================
# 3. CREATE USER (DUPLICATE USERNAME)
# =====================================================================
@pytest.mark.asyncio
async def test_create_user_duplicate_username(async_client):
    payload = {
        "username": "john_doe",
        "email": "john2@example.com",
        "phone_number": "555666777",
        "password": "password123",
    }
    response = await async_client.post("/users/", json=payload)
    assert response.status_code == 400
    assert "Username already taken" in response.text


# =====================================================================
# 4. LIST USERS
# =====================================================================
@pytest.mark.asyncio
async def test_list_users(async_client):
    response = await async_client.get("/users/")
    assert response.status_code == 200
    users = response.json()
    assert isinstance(users, list)
    assert len(users) >= 1


# =====================================================================
# 5. GET USER BY ID (SUCCESS)
# =====================================================================
@pytest.mark.asyncio
async def test_get_user_by_id(async_client):
    users = (await async_client.get("/users/")).json()
    user_id = users[0]["id"]

    response = await async_client.get(f"/users/{user_id}")
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == user_id


# =====================================================================
# 6. GET USER BY ID (NOT FOUND)
# =====================================================================
@pytest.mark.asyncio
async def test_get_user_not_found(async_client):
    missing_uuid = str(uuid.uuid4())
    response = await async_client.get(f"/users/{missing_uuid}")
    assert response.status_code == 404


# =====================================================================
# 7. UPDATE USER (SUCCESS)
# =====================================================================
@pytest.mark.asyncio
async def test_update_user(async_client):
    users = (await async_client.get("/users/")).json()
    user_id = users[0]["id"]

    payload = {"username": "john_updated"}
    response = await async_client.put(f"/users/{user_id}", json=payload)

    assert response.status_code == 200
    assert response.json()["username"] == "john_updated"


# =====================================================================
# 8. UPDATE USER (DUPLICATE EMAIL)
# =====================================================================
@pytest.mark.asyncio
async def test_update_user_duplicate_email(async_client):
    # Create second user
    await async_client.post("/users/", json={
        "username": "dup_user",
        "email": "dup@example.com",
        "phone_number": "444333222",
        "password": "password123",
    })

    first_user_id = (await async_client.get("/users/")).json()[0]["id"]

    response = await async_client.put(
        f"/users/{first_user_id}",
        json={"email": "dup@example.com"}
    )

    assert response.status_code == 400
    assert "Email already registered" in response.text


# =====================================================================
# 9. DELETE USER (SUCCESS)
# =====================================================================
@pytest.mark.asyncio
async def test_delete_user(async_client):
    user = (await async_client.post("/users/", json={
        "username": "delete_me",
        "email": "delete@example.com",
        "phone_number": "000111222",
        "password": "password123",
    })).json()

    response = await async_client.delete(f"/users/{user['id']}")
    assert response.status_code == 204


# =====================================================================
# 10. DELETE NON-EXISTENT USER
# =====================================================================
@pytest.mark.asyncio
async def test_delete_user_not_found(async_client):
    missing_uuid = str(uuid.uuid4())
    response = await async_client.delete(f"/users/{missing_uuid}")
    assert response.status_code == 404


# =====================================================================
# 11. PASSWORD HASHING WORKS
# =====================================================================
def test_password_hashing():
    password = "securePass!"
    hashed = hash_password(password)
    assert hashed != password
    assert verify_password(password, hashed)


# =====================================================================
# 12. INVALID PASSWORD VERIFY FAILS
# =====================================================================
def test_invalid_password_verify():
    password = "securePass!"
    hashed = hash_password(password)
    assert not verify_password("wrongPass!", hashed)


# =====================================================================
# 13. PASSWORD LENGTH VALIDATION
# =====================================================================
@pytest.mark.asyncio
async def test_create_user_short_password(async_client):
    payload = {
        "username": "shortpass",
        "email": "shortpass@example.com",
        "phone_number": "123123123",
        "password": "123",
    }
    response = await async_client.post("/users/", json=payload)
    assert response.status_code == 422


# =====================================================================
# 14. INVALID EMAIL VALIDATION
# =====================================================================
@pytest.mark.asyncio
async def test_create_user_invalid_email(async_client):
    payload = {
        "username": "bademail",
        "email": "notanemail",
        "phone_number": "321321321",
        "password": "password123",
    }
    response = await async_client.post("/users/", json=payload)
    assert response.status_code == 422


# =====================================================================
# 15. AUTHENTICATE USER FAILURE
# =====================================================================
@pytest.mark.asyncio
async def test_authenticate_user_invalid_credentials(db_session):
    user = User(
        username="auth_user",
        email="auth@example.com",
        phone_number="123123123",
        hashed_password=hash_password("correctpass"),
    )
    db_session.add(user)
    await db_session.commit()

    with pytest.raises(HTTPException) as exc:
        await AuthService.authenticate_user(
            db_session, "auth@example.com", "wrongpass"
        )

    assert exc.value.status_code == 401
