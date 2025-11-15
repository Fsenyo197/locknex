from fastapi import FastAPI
from app.routes.api_key_route import api_key_router
from app.routes.auth_route import auth_router
from app.routes.kyc_routes import kyc_router
from app.routes.staff_route import staff_router
from app.routes.user_routes import user_router


def register_routers(app: FastAPI):
    """Register all API routers here."""
    app.include_router(api_key_router)
    app.include_router(kyc_router)
    app.include_router(auth_router)
    app.include_router(staff_router)
    app.include_router(user_router)
