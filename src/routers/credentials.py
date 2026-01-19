from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from ..config.database import get_db
from ..models.user import User, UserRole
from ..schemas.credential import CredentialCreate, CredentialResponse, CredentialUpdate
from ..services.credential_service import CredentialService
from ..middleware.auth import get_current_user, check_admin_privileges

router = APIRouter(
    prefix="/dumapods/{dumapod_id}/credentials",
    tags=["Storage Credentials"],
    responses={404: {"description": "Not found"}},
)


@router.post("", response_model=CredentialResponse, status_code=status.HTTP_201_CREATED)
async def create_credential(
    dumapod_id: int,
    credential_data: CredentialCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Create a new storage credential for a DumaPod.
    Only Admins and Superadmins can create credentials.
    """
    check_admin_privileges(current_user)
    service = CredentialService(db)
    return await service.create_credential(dumapod_id, credential_data)


@router.get("", response_model=List[CredentialResponse])
async def get_credentials(
    dumapod_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    List all credentials for a DumaPod.
    """
    check_admin_privileges(current_user)
    service = CredentialService(db)
    return await service.get_credentials(dumapod_id)


# Note: Update and Delete usually reference credential ID directly,
# but our router prefix includes dumapod_id. 
# We can make a separate router for /credentials/{id} or nest it here.
# For simplicity with the prefix, we'll use /dumapods/{dumapod_id}/credentials/{credential_id}

@router.put("/{credential_id}", response_model=CredentialResponse)
async def update_credential(
    dumapod_id: int,
    credential_id: int,
    credential_data: CredentialUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Update a storage credential.
    """
    check_admin_privileges(current_user)
    service = CredentialService(db)
    # verify credential belongs to dumapod logic could be added here
    return await service.update_credential(credential_id, credential_data)


@router.delete("/{credential_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_credential(
    dumapod_id: int,
    credential_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Delete a storage credential.
    """
    check_admin_privileges(current_user)
    service = CredentialService(db)
    await service.delete_credential(credential_id)
