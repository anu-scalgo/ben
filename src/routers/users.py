"""User management router."""

from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from ..config.database import get_db
from ..services.user_service import UserService
from ..schemas.user import UserCreate, UserUpdate, UserWithUsageResponse
from ..schemas.auth import UserResponse
from ..middleware.auth import get_current_user, check_admin_privileges, check_superadmin_privileges
from ..models.user import User, UserRole
from ..middleware.rate_limit import limiter
from fastapi import Request

router = APIRouter(prefix="/users", tags=["users"])


@router.get("", response_model=List[UserResponse])
async def list_users(
    request: Request,
    skip: int = 0,
    limit: int = 100,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List all users (Admin only)."""
    check_admin_privileges(current_user)
    user_service = UserService(db)
    return await user_service.get_users(skip=skip, limit=limit)


@router.get("/usage", response_model=List[UserWithUsageResponse])
async def list_users_usage(
    request: Request,
    skip: int = 0,
    limit: int = 100,
    user_id: Optional[int] = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    List all users with their DumaPod usage details (Admin only).
    Includes pod capacity, used storage, balance, and file count.
    Optional: Filter by user_id.
    """
    check_admin_privileges(current_user)
    user_service = UserService(db)
    return await user_service.get_users_with_usage(skip=skip, limit=limit, user_id=user_id)


@router.post("", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def create_user(
    request: Request,
    user_data: UserCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Create a new user (Admin only)."""
    check_admin_privileges(current_user)
    
    # Only superadmin can create admins/superadmins
    if user_data.role in [UserRole.ADMIN, UserRole.SUPERADMIN]:
        check_superadmin_privileges(current_user)
        
    user_service = UserService(db)
    return await user_service.create_user(user_data)


@router.get("/me", response_model=UserResponse)
async def read_users_me(
    current_user: User = Depends(get_current_user),
):
    """Get current user."""
    return current_user


@router.get("/{user_id}", response_model=UserResponse)
async def read_user(
    user_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get specific user."""
    check_admin_privileges(current_user)
    user_service = UserService(db)
    return await user_service.get_user(user_id)


@router.patch("/{user_id}", response_model=UserResponse)
async def update_user(
    user_id: int,
    user_data: UserUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Update user."""
    # User can update self, Admin can update others
    if current_user.id != user_id:
        check_admin_privileges(current_user)
        
    # Only superadmin can change roles
    if user_data.role is not None:
        check_superadmin_privileges(current_user)
        
    user_service = UserService(db)
    return await user_service.update_user(user_id, user_data)
