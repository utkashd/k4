__version__ = "0.0.1"
from .extensibles import (
    hookimpl,
    hookspec,
    plugin_manager,
    replace_plugin_with_external_plugin,
)
from .get_complete_chat_for_llm import (
    GetCompleteChatDefaultImplementation,
    GetCompleteChatSpec,
    ParamsForAlreadyExistingChat,
    get_complete_chat_for_llm,
)

plugin_manager.add_hookspecs(GetCompleteChatSpec)


__all__ = [
    "hookimpl",
    "hookspec",
    "plugin_manager",
    "replace_plugin_with_external_plugin",
    "get_complete_chat_for_llm",
    "ParamsForAlreadyExistingChat",
    "GetCompleteChatDefaultImplementation",
]
