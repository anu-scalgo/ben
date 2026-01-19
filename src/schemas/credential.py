from typing import Optional
from pydantic import BaseModel, ConfigDict
from ..models.dumapod import StorageProvider


class CredentialBase(BaseModel):
    provider: StorageProvider
    access_key: str
    secret_key: str
    bucket_name: str
    endpoint_url: Optional[str] = None
    region: Optional[str] = None
    namespace: Optional[str] = None


class CredentialCreate(CredentialBase):
    pass


class CredentialUpdate(BaseModel):
    provider: Optional[StorageProvider] = None
    access_key: Optional[str] = None
    secret_key: Optional[str] = None
    bucket_name: Optional[str] = None
    endpoint_url: Optional[str] = None
    region: Optional[str] = None
    namespace: Optional[str] = None


class CredentialResponse(CredentialBase):
    id: int
    dumapod_id: int

    model_config = ConfigDict(from_attributes=True)
