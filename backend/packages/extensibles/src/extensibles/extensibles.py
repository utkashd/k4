import inspect
import uuid
from importlib import util as importlib_util
from pathlib import Path
from typing import Literal

import apluggy  # type: ignore[import-untyped,unused-ignore]
from k4_logger import log
from utils import biter

hookspec = apluggy.HookspecMarker("k4")
hookimpl = apluggy.HookimplMarker("k4")
plugin_manager = apluggy.PluginManager("k4")


def replace_plugin_with_external_plugin(
    existing_plugin_name: Literal["get_complete_chat_for_llm"],
    external_module_path: Path,
) -> None:
    if not external_module_path.exists():
        raise FileNotFoundError(f"Expected module {external_module_path} not found.")

    if external_module_path.is_dir():
        paths_in_src_dir = external_module_path.joinpath("src").iterdir()
        code_directory = (
            biter(paths_in_src_dir).filter(lambda path: path.is_dir()).first_value()
        )
        external_module_path = (
            biter(code_directory.iterdir())
            .filter(
                lambda path: path.is_file()
                and str(path).endswith(existing_plugin_name + ".py")
            )
            .first_value()
        )

    module_name = str(uuid.uuid4())
    spec = importlib_util.spec_from_file_location(module_name, external_module_path)
    if not spec or not spec.loader:
        raise ImportError(
            f"Could not load module {module_name} from {external_module_path}."
        )

    module = importlib_util.module_from_spec(spec)
    spec.loader.exec_module(module)

    # TODO this logic sucks, improve it
    for _, class_object in reversed(inspect.getmembers(module, inspect.isclass)):
        if class_object.__module__ == module_name:
            log.info(
                f"Installing an extension for {existing_plugin_name=} from {external_module_path=}"
            )
            plugin_manager.unregister(name=existing_plugin_name)
            plugin_manager.register(class_object, name=existing_plugin_name)
            break
