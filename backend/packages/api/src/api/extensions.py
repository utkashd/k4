from fastapi import APIRouter, Depends
from k4_logger import log

from .dependencies import (
    extensions_manager,
    get_current_active_admin_user,
    get_current_active_non_admin_user,
)
from .extension_management import ExtensionInDb, GitUrl
from .user_management import AdminUser, NonAdminUser

extensions_router = APIRouter()


@extensions_router.get("/extension")
async def get_extensions(
    current_admin_user: AdminUser = Depends(get_current_active_admin_user),
) -> list[ExtensionInDb]:
    return await extensions_manager.get_installed_extensions()


@extensions_router.post("/extension")
async def add_extension(
    git_repo_url: GitUrl,
    current_user: NonAdminUser = Depends(get_current_active_non_admin_user),
) -> ExtensionInDb:
    log.info(f"{current_user=} is adding an extension {git_repo_url=}")
    return await extensions_manager.add_extension(git_repo_url)


@extensions_router.delete("/extension")
async def uninstall_extension(
    extension_id: int,
    current_admin_user: AdminUser = Depends(get_current_active_admin_user),
) -> None:
    log.info(f"{current_admin_user=} is uninstalling an extension {extension_id=}")
    await extensions_manager.remove_extension(extension_id=extension_id)
