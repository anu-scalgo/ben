"""DumaPod management router."""

from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from ..config.database import get_db
from ..services.dumapod_service import DumaPodService
from ..schemas.dumapod import DumaPodCreate, DumaPodUpdate, DumaPodResponse
from ..middleware.auth import get_current_user, check_admin_privileges
from ..models.user import User
from fastapi import Request

router = APIRouter(prefix="/dumapods", tags=["dumapods"])


@router.post("", response_model=DumaPodResponse, status_code=status.HTTP_201_CREATED)
async def create_dumapod(
    request: Request,
    pod_data: DumaPodCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Create a new DumaPod (Admin only)."""
    check_admin_privileges(current_user)
    service = DumaPodService(db)
    return await service.create_dumapod(pod_data, user_id=current_user.id)


@router.get("", response_model=List[DumaPodResponse])
async def list_dumapods(
    request: Request,
    skip: int = 0,
    limit: int = 100,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List all DumaPods (Admin only)."""
    check_admin_privileges(current_user)
    service = DumaPodService(db)
    return await service.get_all_dumapods(skip=skip, limit=limit)


@router.get("/{pod_id}", response_model=DumaPodResponse)
async def get_dumapod(
    pod_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get DumaPod details (Admin only)."""
    check_admin_privileges(current_user)
    service = DumaPodService(db)
    return await service.get_dumapod(pod_id)


@router.patch("/{pod_id}", response_model=DumaPodResponse)
async def update_dumapod(
    pod_id: int,
    pod_data: DumaPodUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Update DumaPod (Admin only)."""
    check_admin_privileges(current_user)
    service = DumaPodService(db)
    return await service.update_dumapod(pod_id, pod_data)


@router.delete("/{pod_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_dumapod(
    pod_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Delete (soft) DumaPod (Admin only)."""
    check_admin_privileges(current_user)
    service = DumaPodService(db)
    await service.delete_dumapod(pod_id)
