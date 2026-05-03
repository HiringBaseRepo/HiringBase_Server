"""User management schemas."""
from pydantic import BaseModel, ConfigDict, EmailStr, Field

from app.shared.enums.user_roles import UserRole


class CreateHRAccountRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
    full_name: str = Field(min_length=2, max_length=255)
    company_id: int


class UserListItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    email: str
    full_name: str
    role: UserRole
    company_id: int | None
    is_active: bool


class UserCreatedResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    email: str
    full_name: str
    role: UserRole
    company_id: int | None
