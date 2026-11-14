# app/routers/auth.py
# Job of this file: sign-up, login, "who am I", and admin user management.

from fastapi import APIRouter,Request
from app.core.limiter import limiter
from app.core.deps import CurrentUser, DbSession
from app.routers.helpers import AdminUser, Pagination, make_page
from app.schemas.pagination import Page
from app.schemas.user import (
    LoginRequest,
    Token,
    UserCreate,
    UserCreateByAdmin,
    UserRead,
    UserUpdate,
)
from app.services.auth_service import AuthService

router = APIRouter(tags=["Auth & Users"])


@router.post("/auth/register", response_model=UserRead, status_code=201)
@limiter.limit("10/minute")
def register(request: Request, data: UserCreate, db: DbSession):
    """Public sign-up. The role is always 'user'."""
    return AuthService(db).register(data)


@router.post("/auth/login", response_model=Token)
@limiter.limit("5/minute")
def login(request: Request, data: LoginRequest, db: DbSession):
    """Email + password in, JWT out.Only 5 tries per minute, to slow down brute-force attacks."""
    return AuthService(db).login(data)


@router.get("/auth/me", response_model=UserRead)
def me(current_user: CurrentUser):
    """Who am I? (the user behind the token)."""
    return current_user


@router.get("/users", response_model=Page[UserRead])
def list_users(params: Pagination, db: DbSession, admin: AdminUser):
    rows, total = AuthService(db).list_users(params.offset, params.page_size)
    return make_page(rows, total, params, UserRead)


@router.post("/users", response_model=UserRead, status_code=201)
def create_user(data: UserCreateByAdmin, db: DbSession, admin: AdminUser):
    """Admin creates a staff/admin/user account."""
    return AuthService(db).create_by_admin(data)


@router.get("/users/{user_id}", response_model=UserRead)
def get_user(user_id: int, db: DbSession, admin: AdminUser):
    return AuthService(db).get_user(user_id)


@router.patch("/users/{user_id}", response_model=UserRead)
def update_user(user_id: int, data: UserUpdate, db: DbSession, admin: AdminUser):
    return AuthService(db).update_user(user_id, data, acting_user_id=admin.id)