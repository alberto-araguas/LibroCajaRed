from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.accounts import router as accounts_router
from app.api.auth import ensure_initial_admin, require_active_user
from app.api.auth import router as auth_router
from app.api.concepts import router as concepts_router
from app.api.counterparties import router as counterparties_router
from app.api.reports import router as reports_router
from app.api.transactions import router as transactions_router
from app.api.users import router as users_router
from app.core.config import get_settings

settings = get_settings()

app = FastAPI(title=settings.app_name)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health", tags=["system"])
def health_check() -> dict[str, str]:
    return {"status": "ok", "service": settings.app_name}


@app.on_event("startup")
def seed_initial_admin() -> None:
    ensure_initial_admin()


protected_dependencies = [Depends(require_active_user)]

app.include_router(auth_router)
app.include_router(accounts_router, dependencies=protected_dependencies)
app.include_router(counterparties_router, dependencies=protected_dependencies)
app.include_router(concepts_router, dependencies=protected_dependencies)
app.include_router(transactions_router, dependencies=protected_dependencies)
app.include_router(reports_router, dependencies=protected_dependencies)
app.include_router(users_router)
