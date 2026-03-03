"""Auth API — login, register, user management."""
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Optional

from database import get_db
from auth import hash_password, verify_password, create_access_token, get_current_user, require_role
from models.db_models import User, UserRole

router = APIRouter(prefix="/api/auth", tags=["auth"])


class LoginRequest(BaseModel):
    username: str
    password: str

class LoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: dict

class RegisterRequest(BaseModel):
    username: str
    email: str
    password: str
    full_name: str = ""

class UserOut(BaseModel):
    id: int
    username: str
    email: str
    full_name: str
    role: str
    is_active: bool
    created_at: datetime

    class Config:
        from_attributes = True

class UserUpdate(BaseModel):
    email: Optional[str] = None
    full_name: Optional[str] = None
    role: Optional[str] = None
    is_active: Optional[bool] = None


@router.post("/login", response_model=LoginResponse)
async def login(req: LoginRequest, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(User).where(User.username == req.username))
    user = result.scalar_one_or_none()
    if not user or not verify_password(req.password, user.hashed_password):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid username or password")
    if not user.is_active:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Account is disabled")
    token = create_access_token({"sub": user.username, "role": user.role.value})
    return LoginResponse(
        access_token=token,
        user={"id": user.id, "username": user.username, "role": user.role.value, "full_name": user.full_name},
    )


@router.post("/register", response_model=UserOut)
async def register_user(req: RegisterRequest, db: AsyncSession = Depends(get_db)):
    # First user becomes admin, rest need admin to create
    count = await db.scalar(select(func.count(User.id)))
    if count > 0:
        # After first user, only admins can create new users (checked below)
        pass

    existing = await db.execute(select(User).where((User.username == req.username) | (User.email == req.email)))
    if existing.scalar_one_or_none():
        raise HTTPException(400, "Username or email already exists")

    role = UserRole.admin if count == 0 else UserRole.viewer
    user = User(
        username=req.username,
        email=req.email,
        hashed_password=hash_password(req.password),
        full_name=req.full_name,
        role=role,
    )
    db.add(user)
    await db.flush()
    await db.refresh(user)
    return user


@router.get("/me", response_model=UserOut)
async def me(user: User = Depends(get_current_user)):
    return user


@router.get("/users", response_model=List[UserOut])
async def list_users(
    user: User = Depends(require_role(UserRole.admin)),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(User).order_by(User.created_at))
    return result.scalars().all()


@router.put("/users/{user_id}", response_model=UserOut)
async def update_user(
    user_id: int,
    body: UserUpdate,
    current: User = Depends(require_role(UserRole.admin)),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(User).where(User.id == user_id))
    target = result.scalar_one_or_none()
    if not target:
        raise HTTPException(404, "User not found")
    if body.email is not None:
        target.email = body.email
    if body.full_name is not None:
        target.full_name = body.full_name
    if body.role is not None:
        target.role = UserRole(body.role)
    if body.is_active is not None:
        target.is_active = body.is_active
    await db.flush()
    await db.refresh(target)
    return target


@router.delete("/users/{user_id}")
async def delete_user(
    user_id: int,
    current: User = Depends(require_role(UserRole.admin)),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(User).where(User.id == user_id))
    target = result.scalar_one_or_none()
    if not target:
        raise HTTPException(404, "User not found")
    if target.id == current.id:
        raise HTTPException(400, "Cannot delete yourself")
    await db.delete(target)
    return {"ok": True}


@router.post("/change-password")
async def change_password(
    body: dict,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    if not verify_password(body.get("old_password", ""), user.hashed_password):
        raise HTTPException(400, "Current password is incorrect")
    new_pw = body.get("new_password", "")
    if len(new_pw) < 8:
        raise HTTPException(400, "Password must be at least 8 characters")
    user.hashed_password = hash_password(new_pw)
    await db.flush()
    return {"ok": True}
