# app/services/auth_service.py

from datetime import datetime, timedelta, timezone
from typing import Optional

from jose import jwt
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import HTTPException, status

from app.config import settings
from app.models.user_model import User
from app.utils.verify_password import verify_password


JWT_SECRET_KEY = settings.JWT_SECRET_KEY
JWT_ALGORITHM = settings.JWT_ALGORITHM





# ---------------------------------------------------
# AUTH SERVICE CLASS
# ---------------------------------------------------

class AuthService:

    @staticmethod
    async def authenticate_user(db: AsyncSession, username: str, password: str) -> User:
        """
        Validates username + password and returns the user or raises an exception.
        """

        from sqlalchemy import select

        query = select(User).where(User.username == username)
        result = await db.execute(query)
        user = result.scalar_one_or_none()

        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid username or password",
            )

        if not verify_password(password, user.password):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid username or password",
            )

        return user

    @staticmethod
    async def generate_tokens(user: User):
        """
        Generates access + refresh tokens for the logged-in user.
        """

        payload = {"sub": str(user.id), "username": user.username}

        access_token = create_access_token(payload)
        refresh_token = create_refresh_token(payload)

        return {
            "access_token": access_token,
            "refresh_token": refresh_token,
            "token_type": "bearer",
        }

