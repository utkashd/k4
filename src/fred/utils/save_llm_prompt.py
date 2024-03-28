from contextlib import contextmanager
from datetime import datetime
from functools import wraps
from typing import Any, Callable, Generator, MutableMapping


@contextmanager
def _monkeypatch_instance_method(
    obj: Any, method_name: str, new_method: Callable[[Any], Any]
) -> Generator[None, Any, None]:
    original_method = getattr(obj, method_name)
    # Need to use __get__ when patching instance methods
    # https://stackoverflow.com/a/28127947/18758987
    try:
        setattr(obj, method_name, new_method.__get__(obj, obj.__class__))
        yield
    finally:
        setattr(obj, method_name, original_method.__get__(obj, obj.__class__))


@contextmanager
def _save_method_inputs_as_dict(
    obj: Any,
    method_name: str,
    existing_store: MutableMapping | None = None,  # type: ignore[type-arg]
) -> Generator[dict[str, dict[str, Any]], Any, None]:
    if existing_store is None:
        timestamp_to_kwargs: dict[str, dict[str, Any]] = dict()
    else:
        timestamp_to_kwargs = existing_store  # type: ignore[assignment]

    # TODO: break if the method takes unnamed args. Use inspect.signature
    original_method = getattr(obj, method_name)

    @wraps(original_method)
    def new_method(
        self: Any, **kwargs: dict[str, Any]
    ) -> Any:  # create takes only named args
        current_time = datetime.now().strftime("%Y-%m-%d_%H-%M-%S-%f")
        timestamp_to_kwargs[current_time] = kwargs
        return original_method(**kwargs)

    with _monkeypatch_instance_method(obj, method_name, new_method):
        yield timestamp_to_kwargs


@contextmanager
def save_chat_create_inputs_as_dict(
    client_with_create_method: Any,
    existing_store: MutableMapping | None = None,  # type: ignore[type-arg]
) -> Generator[dict[str, dict[str, Any]], Any, None]:
    """
    In this context, save the inputs sent to some API through
    `client_with_create_method.create` in a dictionary.

    Parameters
    ----------
    client_with_create_method : Any
        some object with a `create` method, e.g.,
        `langchain_openai.ChatOpenAI().client`. Its inputs will be saved in a dictionary
        whenever this method is called
    existing_store : MutableMapping, optional
        an existing dictionary which you'd like to add to. By default, a new dictionary
        will be created

    Example
    -------
    ::

        from langchain_openai import ChatOpenAI

        llm = ChatOpenAI()

        with save_chat_create_inputs_as_dict(llm.client) as timestamp_to_kwargs:
            # Note that the llm.client object is modified in this context, so any code
            # that uses the llm will end up saving its inputs in timestamp_to_kwargs.
            response = llm.invoke("how can langsmith help with testing?")

        print(timestamp_to_kwargs)

    Note
    ----
    You probably only need the last key-value that's saved in `timestamp_to_kwargs` b/c
    it'll contain the chat history.
    """
    with _save_method_inputs_as_dict(
        client_with_create_method, "create", existing_store=existing_store
    ) as timestamp_to_kwargs:
        yield timestamp_to_kwargs
