from typing import Optional, cast
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import jwt, JWTError, ExpiredSignatureError
from sqlalchemy.ext.asyncio import AsyncSession  # Changed import for AsyncSession
from sqlalchemy import select  # Import select for modern querying
from uuid import UUID
from app.models.user_model import User, UserStatus
from app.db import get_db
from app.config import settings

# --- Configuration ---
JWT_SECRET_KEY = settings.JWT_SECRET_KEY
JWT_ALGORITHM = settings.JWT_ALGORITHM

# OAuth2 scheme for extracting Bearer token
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/login")

# --- Dependency Function ---

async def get_current_user( # Made function asynchronous
    token: str = Depends(oauth2_scheme),
    db: AsyncSession = Depends(get_db), # Expecting an AsyncSession
) -> User:
    """
    Extract and return the current authenticated user based on JWT token.
    """

    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    try:
        # Decode and validate JWT
        payload = jwt.decode(token, JWT_SECRET_KEY, algorithms=[JWT_ALGORITHM])
        user_id: Optional[str] = payload.get("sub")
        if not user_id:
            raise credentials_exception
        try:
            user_uuid = UUID(user_id)
        except ValueError:
            raise credentials_exception

    except ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has expired",
            headers={"WWW-Authenticate": "Bearer"},
        )
    except JWTError:
        raise credentials_exception

    # Fetch user from DB using modern async query style
    result = await db.execute( # Use await and execute
        select(User).where(User.id == user_uuid)
    )
    user = result.scalar_one_or_none() # Use scalar_one_or_none to get the object

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )

    # Check account status
    user_status = cast(UserStatus, user.status)
    if user_status != UserStatus.ACTIVE:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"User account is {user_status.value}",
        )

    return user
