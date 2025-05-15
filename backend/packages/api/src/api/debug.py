from api.dependencies import get_current_active_admin_user
from api.user_management import AdminUser
from fastapi import APIRouter, Depends
from k4_logger import log

debug_router = APIRouter()


@debug_router.get("/debug/test_sentry")
def intentionally_raise_exception(
    current_admin_user: AdminUser = Depends(get_current_active_admin_user),
) -> None:
    log.info("intentionally raising an exception!")
    raise Exception(f"This exception was raised intentionally by {current_admin_user=}")
