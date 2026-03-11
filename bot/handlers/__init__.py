from aiogram import Router

from .auth import router as auth_router
from .common import router as common_router
from .stats import router as stats_router
from .admin import router as admin_router


def setup_routers() -> Router:
    """Create and wire all routers into a single root router."""
    root = Router(name="root")
    root.include_router(auth_router)   # auth first — catches unauthenticated users
    root.include_router(common_router)
    root.include_router(stats_router)
    root.include_router(admin_router)
    return root
