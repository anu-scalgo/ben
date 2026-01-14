"""Authentication service for user login and registration."""

from typing import Optional
from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from ..repositories.user_repo import UserRepository
from ..core.security import verify_password, get_password_hash
from ..middleware.auth import create_access_token
from ..schemas.auth import LoginRequest, RegisterRequest, TokenResponse, UserResponse
from datetime import timedelta
from ..config import settings


class AuthService:
    """Service for authentication operations."""

    def __init__(self, db: AsyncSession):
        self.db = db
        self.user_repo = UserRepository(db)

    async def login(self, login_data: LoginRequest) -> TokenResponse:
        """
        Authenticate user and return JWT token.
        Raises HTTPException if credentials are invalid.
        """
        user = await self.user_repo.get_by_email(login_data.email)

        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Incorrect email or password",
            )

        if not verify_password(login_data.password, user.hashed_password):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Incorrect email or password",
            )

        if not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="User account is inactive",
            )

        access_token_expires = timedelta(
            minutes=settings.jwt_access_token_expire_minutes
        )
        access_token = create_access_token(
            data={"sub": str(user.id), "role": user.role.value},
            expires_delta=access_token_expires,
        )

        return TokenResponse(
            access_token=access_token,
            token_type="bearer",
            expires_in=settings.jwt_access_token_expire_minutes * 60,
        )

    async def register(self, register_data: RegisterRequest) -> UserResponse:
        """
        Register a new user.
        Raises HTTPException if email already exists.
        """
        # Check if user already exists
        existing_user = await self.user_repo.get_by_email(register_data.email)
        if existing_user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email already registered",
            )

        # Hash password and create user
        hashed_password = get_password_hash(register_data.password)
        user = await self.user_repo.create_user(
            email=register_data.email,
            hashed_password=hashed_password,
            full_name=register_data.full_name,
        )

        return user

