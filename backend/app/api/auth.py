from fastapi import APIRouter, Depends, Header, HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.core.config import Settings, get_settings
from app.db.session import SessionLocal, get_db
from app.models import User
from app.schemas.auth import LoginRequest, TokenResponse, UserRead
from app.services.security import create_access_token, hash_password, parse_access_token, verify_password

router = APIRouter(prefix="/auth", tags=["auth"])


def ensure_initial_admin() -> None:
    settings = get_settings()
    try:
        with SessionLocal() as db:
            user_count = db.scalar(select(func.count()).select_from(User))
            if user_count:
                return
            admin = User(
                username=settings.initial_admin_username.strip(),
                password_hash=hash_password(settings.initial_admin_password),
                full_name=settings.initial_admin_full_name.strip() or None,
                is_admin=True,
                is_active=True,
            )
            db.add(admin)
            db.commit()
    except SQLAlchemyError:
        return


def get_current_user(
    authorization: str | None = Header(default=None),
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> User:
    if not authorization or not authorization.lower().startswith("bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="No autenticado.",
        )

    token = authorization.split(" ", 1)[1].strip()
    user_id = parse_access_token(token, settings.auth_secret)
    if user_id is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Sesión no válida o caducada.",
        )

    user = db.get(User, user_id)
    if user is None or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Usuario no disponible.",
        )
    return user


def require_active_user(current_user: User = Depends(get_current_user)) -> User:
    return current_user


def require_admin(current_user: User = Depends(get_current_user)) -> User:
    if not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Se requiere usuario administrador.",
        )
    return current_user


@router.post("/login", response_model=TokenResponse)
def login(
    payload: LoginRequest,
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> TokenResponse:
    username = payload.username.strip()
    user = db.scalar(select(User).where(User.username == username))
    if user is None or not user.is_active or not verify_password(payload.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Usuario o contraseña incorrectos.",
        )

    token = create_access_token(user.id, settings.auth_secret, settings.auth_token_expire_minutes)
    return TokenResponse(access_token=token, user=UserRead.model_validate(user))


@router.get("/me", response_model=UserRead)
def read_current_user(current_user: User = Depends(get_current_user)) -> User:
    return current_user
