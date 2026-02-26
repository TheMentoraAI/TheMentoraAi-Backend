# Router package initialization
from .auth_router import router as auth_router
from .users_router import router as users_router
from .tracks_router import router as tracks_router

__all__ = ["auth_router", "users_router", "tracks_router"]
