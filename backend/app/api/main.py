from fastapi import APIRouter

from app.api.routes import items, login, private, users, utils, directsend_mail, directsend_sms
from app.core.config import settings

api_router = APIRouter()
api_router.include_router(login.router)
api_router.include_router(users.router)
api_router.include_router(utils.router)
api_router.include_router(items.router)
api_router.include_router(directsend_mail.router)
api_router.include_router(directsend_sms.router)


if settings.ENVIRONMENT == "local":
    api_router.include_router(private.router)
