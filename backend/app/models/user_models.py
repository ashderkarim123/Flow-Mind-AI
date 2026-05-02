from pydantic import BaseModel, EmailStr
from typing import Optional, List, Dict, Any
from datetime import datetime


class UserProfile(BaseModel):
    """Full user profile model"""
    uid: str
    email: str
    display_name: Optional[str] = None
    email_verified: bool = False
    disabled: bool = False
    role: str = "user"           # "user" | "admin" | "manager"
    created_at: Optional[datetime] = None
    last_sign_in: Optional[datetime] = None
    photo_url: Optional[str] = None
    workflow_count: Optional[int] = 0

    class Config:
        from_attributes = True


class UserListResponse(BaseModel):
    success: bool = True
    users: List[UserProfile]
    total: int
    page: int = 1
    page_size: int = 20


class UpdateRoleRequest(BaseModel):
    role: str  # "user" | "admin" | "manager"

    class Config:
        json_schema_extra = {
            "example": {"role": "manager"}
        }


class UpdateStatusRequest(BaseModel):
    disabled: bool

    class Config:
        json_schema_extra = {
            "example": {"disabled": True}
        }


class UserStatsResponse(BaseModel):
    success: bool = True
    total_users: int
    active_users: int
    admin_users: int
    disabled_users: int
    new_users_today: int
    new_users_this_week: int


class UserWorkflowsResponse(BaseModel):
    success: bool = True
    uid: str
    workflows: List[Dict[str, Any]]
    total: int


class CreateUserRequest(BaseModel):
    email: EmailStr
    password: str
    display_name: Optional[str] = None
    role: str = "user"

    class Config:
        json_schema_extra = {
            "example": {
                "email": "newuser@example.com",
                "password": "securepassword123",
                "display_name": "New User",
                "role": "user"
            }
        }
