"""Auth API — login, register, user management."""
import socket
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Optional, Dict

from database import get_db
from auth import hash_password, verify_password, create_access_token, get_current_user, require_role
from models.db_models import User, UserRole
from license import get_licensed_features

# ── Feature list & role defaults ──
ALL_FEATURES = [
    'dashboard', 'compliance', 'hosts', 'groups', 'patches', 'snapshots',
    'compare', 'offline', 'schedules', 'cve', 'jobs', 'audit',
    'notifications', 'users', 'license', 'cicd', 'git', 'onboarding', 'settings',
    'monitoring',
]

ROLE_DEFAULTS = {
    'admin':    {f: True for f in ALL_FEATURES},
    'operator': {f: True for f in ALL_FEATURES if f not in ('audit', 'users', 'license', 'cicd', 'git')},
    'viewer':   {f: True for f in ['dashboard','compliance','hosts','groups','compare','cve','jobs','onboarding','settings']},
    'auditor':  {f: True for f in ['dashboard','compliance','hosts','groups','compare','cve','jobs','audit','onboarding','settings']},
}
# Fill missing keys as False
for role_perms in ROLE_DEFAULTS.values():
    for f in ALL_FEATURES:
        role_perms.setdefault(f, False)


def get_effective_permissions(role: str, custom: dict = None) -> dict:
    """Merge role defaults with per-user custom overrides, then intersect with license tier."""
    base = dict(ROLE_DEFAULTS.get(role, ROLE_DEFAULTS['viewer']))
    if custom:
        for k, v in custom.items():
            if k in base:
                base[k] = bool(v)
    # Intersect with license-allowed features (license tier enforcement)
    licensed = get_licensed_features()
    for f in base:
        if f not in licensed:
            base[f] = False
    return base

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
    custom_permissions: Optional[dict] = None
    effective_permissions: Optional[dict] = None
    created_at: datetime

    class Config:
        from_attributes = True

    @classmethod
    def from_user(cls, user: User) -> 'UserOut':
        return cls(
            id=user.id,
            username=user.username,
            email=user.email,
            full_name=user.full_name or '',
            role=user.role.value if hasattr(user.role, 'value') else user.role,
            is_active=user.is_active,
            custom_permissions=user.custom_permissions,
            effective_permissions=get_effective_permissions(
                user.role.value if hasattr(user.role, 'value') else user.role,
                user.custom_permissions,
            ),
            created_at=user.created_at,
        )

class UserUpdate(BaseModel):
    email: Optional[str] = None
    full_name: Optional[str] = None
    role: Optional[str] = None
    is_active: Optional[bool] = None

class CreateUserRequest(BaseModel):
    username: str
    email: str
    password: str
    full_name: str = ""
    role: str = "viewer"

class AdminResetPasswordRequest(BaseModel):
    new_password: str


@router.post("/login", response_model=LoginResponse)
async def login(req: LoginRequest, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(User).where(User.username == req.username))
    user = result.scalar_one_or_none()
    if not user or not verify_password(req.password, user.hashed_password):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid username or password")
    if not user.is_active:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Account is disabled")
    perms = get_effective_permissions(user.role.value, user.custom_permissions)
    token = create_access_token({"sub": user.username, "role": user.role.value})
    return LoginResponse(
        access_token=token,
        user={"id": user.id, "username": user.username, "role": user.role.value, "full_name": user.full_name, "permissions": perms},
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


@router.get("/me")
async def me(user: User = Depends(get_current_user)):
    return UserOut.from_user(user)


@router.get("/users")
async def list_users(
    user: User = Depends(require_role(UserRole.admin)),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(User).order_by(User.created_at))
    return [UserOut.from_user(u) for u in result.scalars().all()]


@router.get("/role-defaults")
async def role_defaults(user: User = Depends(require_role(UserRole.admin))):
    """Return default permissions for every role and the full feature list."""
    return {"features": ALL_FEATURES, "role_defaults": ROLE_DEFAULTS}


@router.put("/users/{user_id}/permissions")
async def update_user_permissions(
    user_id: int,
    body: dict,
    current: User = Depends(require_role(UserRole.admin)),
    db: AsyncSession = Depends(get_db),
):
    """Admin sets per-user custom permission overrides."""
    result = await db.execute(select(User).where(User.id == user_id))
    target = result.scalar_one_or_none()
    if not target:
        raise HTTPException(404, "User not found")
    perms = body.get("permissions", {})
    # Validate keys
    clean = {k: bool(v) for k, v in perms.items() if k in ALL_FEATURES}
    target.custom_permissions = clean if clean else None
    await db.flush()
    await db.refresh(target)
    return UserOut.from_user(target)


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


@router.post("/users", response_model=UserOut)
async def admin_create_user(
    req: CreateUserRequest,
    current: User = Depends(require_role(UserRole.admin)),
    db: AsyncSession = Depends(get_db),
):
    """Admin creates a new user with a specific role."""
    if len(req.password) < 8:
        raise HTTPException(400, "Password must be at least 8 characters")
    if req.role not in [r.value for r in UserRole]:
        raise HTTPException(400, f"Invalid role. Must be one of: {[r.value for r in UserRole]}")
    existing = await db.execute(
        select(User).where((User.username == req.username) | (User.email == req.email))
    )
    if existing.scalar_one_or_none():
        raise HTTPException(400, "Username or email already exists")
    user = User(
        username=req.username,
        email=req.email,
        hashed_password=hash_password(req.password),
        full_name=req.full_name,
        role=UserRole(req.role),
    )
    db.add(user)
    await db.flush()
    await db.refresh(user)
    return user


@router.post("/users/{user_id}/reset-password")
async def admin_reset_password(
    user_id: int,
    body: AdminResetPasswordRequest,
    current: User = Depends(require_role(UserRole.admin)),
    db: AsyncSession = Depends(get_db),
):
    """Admin resets another user's password."""
    if len(body.new_password) < 8:
        raise HTTPException(400, "Password must be at least 8 characters")
    result = await db.execute(select(User).where(User.id == user_id))
    target = result.scalar_one_or_none()
    if not target:
        raise HTTPException(404, "User not found")
    target.hashed_password = hash_password(body.new_password)
    await db.flush()
    return {"ok": True, "message": f"Password reset for user '{target.username}'"}


# ── Monitoring tools status ──

MONITORING_TOOLS = {
    "prometheus": {"name": "Prometheus", "default_port": 9090, "path": "/-/healthy"},
    "grafana":    {"name": "Grafana",    "default_port": 3001, "path": "/api/health"},
    "zabbix":     {"name": "Zabbix",     "default_port": 8080, "path": "/"},
}


def _check_port(host: str, port: int, timeout: float = 1.5) -> bool:
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return True
    except (OSError, ConnectionRefusedError, TimeoutError):
        return False


@router.get("/monitoring-status")
async def monitoring_status(user: User = Depends(get_current_user)):
    """Check which monitoring tools are reachable on localhost."""
    import os
    results = {}
    master_ip = os.getenv("MASTER_IP", "localhost")
    for key, info in MONITORING_TOOLS.items():
        port_env = os.getenv(f"{key.upper()}_PORT", str(info["default_port"]))
        port = int(port_env)
        url_env = os.getenv(f"{key.upper()}_URL", "")
        reachable = _check_port("127.0.0.1", port)
        url = url_env if url_env else (f"http://{master_ip}:{port}" if reachable else "")
        results[key] = {
            "name": info["name"],
            "port": port,
            "reachable": reachable,
            "url": url,
        }
    return results
