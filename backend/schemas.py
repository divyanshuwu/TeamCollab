from pydantic import BaseModel, ConfigDict, EmailStr
from datetime import datetime
from typing import Literal

class ProjectCreate(BaseModel):
    name: str
    description: str


class ProjectResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    description: str | None = None
    created_at: datetime | None = None


class UserCreate(BaseModel):
    name: str
    email: EmailStr
    password: str


class UserResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    email: EmailStr
    is_active: bool
    created_at: datetime | None = None

class UserLogin(BaseModel):
    email: EmailStr
    password: str


class ProjectMemberCreate(BaseModel):
    user_id: int
    role: str = "member"


class ProjectMemberResponse(BaseModel):
    user_id: int
    name: str
    email: EmailStr
    role: str


class TaskCreate(BaseModel):
    title: str
    description: str | None = None
    priority: Literal["low", "medium", "high"] = "medium"
    assigned_to: int | None = None
    due_date: datetime | None = None


class TaskResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    title: str
    description: str | None = None
    status: str
    priority: str
    project_id: int
    assigned_to: int | None = None
    due_date: datetime | None = None
    created_at: datetime | None = None


class TaskStatusUpdate(BaseModel):
    status: Literal["todo", "in_progress", "done"]



class TaskUpdate(BaseModel):
    title: str
    description: str | None = None
    priority: Literal["low", "medium", "high"] = "medium"
    assigned_to: int | None = None
    due_date: datetime | None = None