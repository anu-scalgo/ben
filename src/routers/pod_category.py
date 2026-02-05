"""Pod Category router."""

from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from ..config.database import get_db
from ..repositories.pod_category_repo import PodCategoryRepository
from ..schemas.pod_category import (
    PodCategoryCreate,
    PodCategoryUpdate,
    PodCategoryResponse,
)
from ..middleware.auth import get_current_user, check_admin_privileges
from ..models.user import User


router = APIRouter(prefix="/pod-categories", tags=["pod-categories"])


@router.post("", response_model=PodCategoryResponse, status_code=status.HTTP_201_CREATED)
async def create_category(
    category_data: PodCategoryCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Create a new pod category (Admin only)."""
    check_admin_privileges(current_user)
    repo = PodCategoryRepository(db)
    
    existing = await repo.get_by_name(category_data.name)
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Category with this name already exists",
        )
        
    return await repo.create(**category_data.model_dump())


@router.get("", response_model=List[PodCategoryResponse])
async def list_categories(
    skip: int = 0,
    limit: int = 100,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List all pod categories."""
    repo = PodCategoryRepository(db)
    # The base repository's get_all returns dicts, but Pydantic can handle it.
    # However, let's check if we need to convert or if get_all returns scalars.
    # BaseRepository returns [self._to_dict(e) for e in entities]
    return await repo.get_all(skip=skip, limit=limit)


@router.get("/{category_id}", response_model=PodCategoryResponse)
async def get_category(
    category_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get a pod category by ID."""
    repo = PodCategoryRepository(db)
    category = await repo.get_by_id(category_id)
    if not category:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Category not found",
        )
    return category


@router.patch("/{category_id}", response_model=PodCategoryResponse)
async def update_category(
    category_id: int,
    category_data: PodCategoryUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Update a pod category (Admin only)."""
    check_admin_privileges(current_user)
    repo = PodCategoryRepository(db)
    
    current_category = await repo.get_by_id(category_id)
    if not current_category:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Category not found",
        )
        
    if category_data.name:
        existing = await repo.get_by_name(category_data.name)
        if existing and existing.id != category_id:
             raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Category with this name already exists",
            )
            
    updated = await repo.update(category_id, **category_data.model_dump(exclude_unset=True))
    return updated


@router.delete("/{category_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_category(
    category_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Delete a pod category (Admin only)."""
    check_admin_privileges(current_user)
    repo = PodCategoryRepository(db)
    
    current_category = await repo.get_by_id(category_id)
    if not current_category:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Category not found",
        )
        
    await repo.delete(category_id)
