import inspect
import os
import uuid
from importlib import util as importlib_util

import apluggy  # type: ignore[import-untyped,unused-ignore]

hookspec = apluggy.HookspecMarker("cyris")
hookimpl = apluggy.HookimplMarker("cyris")
plugin_manager = apluggy.PluginManager("cyris")


def replace_plugin_with_external_plugin(
    existing_plugin_name: str,
    external_module_path: str,
) -> None:
    module_name = str(uuid.uuid4())

    if not os.path.exists(external_module_path):
        raise FileNotFoundError(f"Expected module {external_module_path} not found.")

    spec = importlib_util.spec_from_file_location(module_name, external_module_path)
    if not spec or not spec.loader:
        raise ImportError(
            f"Could not load module {module_name} from {external_module_path}."
        )

    module = importlib_util.module_from_spec(spec)
    spec.loader.exec_module(module)

    for _, class_object in reversed(inspect.getmembers(module, inspect.isclass)):
        if class_object.__module__ == module_name:
            plugin_manager.unregister(name=existing_plugin_name)
            plugin_manager.register(class_object, name=existing_plugin_name)
            break
