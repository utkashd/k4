from dataclasses import dataclass

from api.user_management import AdminUser, NonAdminUser
from fastapi import APIRouter, Depends
from k4.llm_provider_management import K4LlmProvider, LlmProviderConfig, LlmProviderInfo

from ._dependencies import get_current_active_admin_user, get_current_active_user, k4

providers_router = APIRouter()


@dataclass
class ConfigureProviderDetails:
    llm_provider: K4LlmProvider
    llm_provider_config: LlmProviderConfig


@providers_router.get("/provider")
def get_providers(
    current_admin_user: AdminUser = Depends(get_current_active_admin_user),
) -> dict[K4LlmProvider, LlmProviderInfo]:
    return k4.llm_provider_manager.providers


@providers_router.post("/provider")
async def configure_provider(
    configure_provider_details: ConfigureProviderDetails,
    current_admin_user: AdminUser = Depends(get_current_active_admin_user),
) -> None:
    await k4.llm_provider_manager.add_or_update_provider_and_save_to_disk(
        llm_provider=configure_provider_details.llm_provider,
        llm_provider_config=configure_provider_details.llm_provider_config,
    )


@providers_router.delete("/provider")
async def remove_provider(
    llm_provider_to_remove: K4LlmProvider,
    current_admin_user: AdminUser = Depends(get_current_active_admin_user),
) -> None:
    await k4.llm_provider_manager.remove_provider_and_save_to_disk(
        llm_provider=llm_provider_to_remove
    )


@providers_router.get("/models")
def get_available_models(
    current_user: AdminUser | NonAdminUser = Depends(get_current_active_user),
) -> dict[str, list[str]]:
    return k4.llm_provider_manager.get_available_models()
