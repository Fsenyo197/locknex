from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from fastapi import HTTPException, status
from app.models.user_model import User, UserStatus
from app.schemas.user_schema import UserCreate, UserUpdate
from app.utils.activity_logger import log_activity
from passlib.context import CryptContext
from typing import Optional, cast, List
from uuid import UUID


pwd_context = CryptContext(
    schemes=["argon2"],
    deprecated="auto",
    argon2__type="ID",
    argon2__memory_cost=32768,  # 32 MB
    argon2__parallelism=4,
    argon2__time_cost=2,
)

pwd_context = CryptContext(
    schemes=["argon2"],
    deprecated="auto"
)

def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)


class UserService:
    # -------------------------
    # Authentication
    # -------------------------
    @staticmethod
    async def authenticate_user(db: AsyncSession, email: str, password: str, request=None) -> User:
        result = await db.execute(select(User).where(User.email == email))
        user = result.scalar_one_or_none()

        if not user or not verify_password(password, cast(str, user.hashed_password)):
            await log_activity(db, None, "login_failed", request=request, description=f"Failed login for {email}")
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")

        if cast(UserStatus, user.status) == UserStatus.SUSPENDED:
            await log_activity(db, user, "login_blocked", request=request, description="Account suspended")
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Account suspended")

        await log_activity(db, user, "login_success", request=request, description=f"User {email} logged in")
        return user

    # -------------------------
    # Create
    # -------------------------
    @staticmethod
    async def create_user(db: AsyncSession, user_in: UserCreate, current_user: Optional[User] = None, request=None) -> User:
        try:
            if getattr(user_in, "is_superuser", False):
                await log_activity(db, current_user, "create_user_denied", request=request, description="Attempt to create superuser")
                raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Cannot create another superuser")

            # Username check
            result = await db.execute(select(User).where(User.username == user_in.username))
            if result.scalar_one_or_none():
                await log_activity(db, current_user, "create_user_failed", request=request, description=f"Username {user_in.username} taken")
                raise HTTPException(status_code=400, detail="Username already taken")

            # Email check
            result = await db.execute(select(User).where(User.email == user_in.email))
            if result.scalar_one_or_none():
                await log_activity(db, current_user, "create_user_failed", request=request, description=f"Email {user_in.email} registered")
                raise HTTPException(status_code=400, detail="Email already registered")

            user = User(
                username=user_in.username,
                email=user_in.email,
                phone_number=user_in.phone_number,
                hashed_password=hash_password(user_in.password),
            )
            db.add(user)
            await db.commit()
            await db.refresh(user)

            await log_activity(db, user, "create_user_success", request=request,
                               description=f"User {user.username} created by {current_user.username if current_user else 'system'}")
            return user
        except HTTPException:
            raise
        except Exception as e:
            await db.rollback()
            await log_activity(db, current_user, "create_user_error", request=request, description=str(e))
            raise HTTPException(status_code=500, detail="Error creating user")

    # -------------------------
    # Update
    # -------------------------
    @staticmethod
    async def update_user(db: AsyncSession, user: User, user_in: UserUpdate, current_user: User, request=None) -> User:
        try:
            if user.is_superuser and user.id != current_user.id:
                await log_activity(db, current_user, "update_user_denied", request=request, description="Attempt to edit superuser")
                raise HTTPException(status_code=403, detail="Only the superuser can edit their own account")

            # Uniqueness checks
            if user_in.username and user_in.username != user.username:
                result = await db.execute(select(User).where(User.username == user_in.username))
                if result.scalar_one_or_none():
                    raise HTTPException(status_code=400, detail="Username already taken")

            if user_in.email and user_in.email != user.email:
                result = await db.execute(select(User).where(User.email == user_in.email))
                if result.scalar_one_or_none():
                    raise HTTPException(status_code=400, detail="Email already registered")

            if user_in.phone_number and user_in.phone_number != user.phone_number:
                result = await db.execute(select(User).where(User.phone_number == user_in.phone_number))
                if result.scalar_one_or_none():
                    raise HTTPException(status_code=400, detail="Phone number already registered")

            # Apply updates
            if user_in.password:
                setattr(user, "hashed_password", hash_password(user_in.password))
            if user_in.is_verified is not None:
                setattr(user, "is_verified", user_in.is_verified)
            if user_in.status is not None:
                setattr(user, "status", user_in.status)
            if user_in.twofa_secret is not None:
                setattr(user, "twofa_secret", user_in.twofa_secret)

            await db.commit()
            await db.refresh(user)

            await log_activity(db, current_user, "update_user_success", request=request,
                               description=f"User {user.username} updated by {current_user.username}")
            return user
        except HTTPException:
            raise
        except Exception as e:
            await db.rollback()
            await log_activity(db, current_user, "update_user_error", request=request, description=str(e))
            raise HTTPException(status_code=500, detail="Error updating user")

    # -------------------------
    # Read (Get / List)
    # -------------------------
    @staticmethod
    async def get_user_by_id(db: AsyncSession, user_id: UUID, current_user: User, request=None) -> User:
        try:
            result = await db.execute(select(User).where(User.id == user_id))
            user = result.scalar_one_or_none()
            if not user:
                await log_activity(db, current_user, "get_user_failed", request=request, description=f"User {user_id} not found")
                raise HTTPException(status_code=404, detail="User not found")

            if user.is_superuser and user.id != current_user.id:
                await log_activity(db, current_user, "get_user_denied", request=request, description=f"Attempt to view superuser {user_id}")
                raise HTTPException(status_code=403, detail="Cannot view superuser")

            await log_activity(db, current_user, "get_user_success", request=request,
                               description=f"User {user.username} retrieved by {current_user.username}")
            return user
        except Exception as e:
            await db.rollback()
            await log_activity(db, current_user, "get_user_error", request=request, description=str(e))
            raise HTTPException(status_code=500, detail="Error retrieving user")

    @staticmethod
    async def list_users(db: AsyncSession, current_user: Optional[User] = None, skip: int = 0, limit: int = 100, request=None) -> List[User]:
        try:
            result = await db.execute(
                select(User).where(User.is_superuser == False).offset(skip).limit(limit)
            )
            users = list(result.scalars().all())
            await log_activity(db, current_user, "list_users_success", request=request,
                               description=f"{len(users)} users retrieved by {current_user.username if current_user else 'system'}")
            return users
        except Exception as e:
            await db.rollback()
            await log_activity(db, current_user, "list_users_error", request=request, description=str(e))
            raise HTTPException(status_code=500, detail="Error retrieving users")

    # -------------------------
    # Delete
    # -------------------------
    @staticmethod
    async def delete_user(db: AsyncSession, user: User, current_user: User, request=None) -> None:
        try:
            if user.is_superuser and user.id != current_user.id:
                raise HTTPException(status_code=403, detail="Superuser cannot be deleted by others")

            await db.delete(user)
            await db.commit()

            await log_activity(db, user, "delete_user_success", request=request,
                               description=f"User {user.username} deleted by {current_user.username}")
        except HTTPException:
            raise
        except Exception as e:
            await db.rollback()
            await log_activity(db, current_user, "delete_user_error", request=request, description=str(e))
            raise HTTPException(status_code=500, detail="Error deleting user")
