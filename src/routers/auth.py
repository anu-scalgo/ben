"""Authentication routes."""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from ..config.database import get_db
from ..services.auth_service import AuthService
from ..schemas.auth import LoginRequest, RegisterRequest, TokenResponse, UserResponse
from ..middleware.rate_limit import limiter
from fastapi import Request

router = APIRouter(prefix="/auth", tags=["authentication"])


@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
@limiter.limit("5/minute")
async def register(
    request: Request,
    register_data: RegisterRequest,
    db: AsyncSession = Depends(get_db),
):
    """Register a new user."""
    auth_service = AuthService(db)
    return await auth_service.register(register_data)


@router.post("/login", response_model=TokenResponse)
@limiter.limit("10/minute")
async def login(
    request: Request,
    login_data: LoginRequest,
    db: AsyncSession = Depends(get_db),
):
    """Login and get JWT access token."""
    auth_service = AuthService(db)
    return await auth_service.login(login_data)

