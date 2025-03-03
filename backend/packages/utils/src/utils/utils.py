import os
import time
from abc import ABC, abstractmethod
from enum import Enum
from functools import cache, lru_cache, wraps
from typing import Any, Callable, Generator, Generic, Iterable, Iterator, TypeVar


class AsyncObject(ABC):
    """
    Taken from
    https://stackoverflow.com/questions/33128325/how-to-set-class-attribute-with-await-in-init

    Inheriting this class allows you to define an object with an async __init__.

    So you can create objects with `await MyClass(params)`
    """

    async def __new__(cls, *args, **kwargs):  # type: ignore[no-untyped-def]
        instance = super().__new__(cls)
        await instance.__init__(*args, **kwargs)  # type: ignore[misc]
        return instance

    @abstractmethod
    async def __init__(self):  # type: ignore[no-untyped-def]
        ...


class CyrisEnvironment(Enum):
    DEVELOPMENT = 1
    PRODUCTION = 2


_T = TypeVar("_T")
_ReturnType = TypeVar("_ReturnType")


class biter(Generic[_T]):
    """
    Intentionally terrible name. "Better Iterable" except it's short

    You can wrap an iterable with `biter` and then method-chain `.filter()` and `.map()`

    And there's `.reduce()` as well.
    """

    def __init__(self, generic_iterable: Iterable[_T]):
        self.generic_iterable = generic_iterable

    def __iter__(self) -> Iterator[_T]:
        return iter(self.generic_iterable)

    def __next__(self) -> _T:
        for value in self.generic_iterable:
            return value
        raise ValueError("No next value; it's empty")

    def next(self) -> _T:
        # note that this `next` is NOT self.next. This calls the `self.__next__` method.
        return next(self)

    def filter(self, func: Callable[[_T], bool]) -> "biter[_T]":
        """
        Example:

        ```
        from utils import biter

        my_list = [1, 2, 3]
        filtered = biter(my_list).filter(lambda value: value > 1)
        for value in filtered:
            print(value)
        # 2
        # 3
        ```
        """

        def filter_values_generator() -> Generator[_T, Any, None]:
            for value in self:
                if func(value):
                    yield value

        return biter(filter_values_generator())

    def map(self, func: Callable[[_T], _ReturnType]) -> "biter[_ReturnType]":
        def map_values_generator() -> Generator[_ReturnType, Any, None]:
            for value in self:
                yield func(value)

        return biter(map_values_generator())

    def reduce(
        self, func: Callable[[_T, _ReturnType], _ReturnType], initial_value: _ReturnType
    ) -> _ReturnType:
        accumulated_value = initial_value
        for value in self:
            accumulated_value = func(value, accumulated_value)

        return accumulated_value


@cache
def get_environment() -> CyrisEnvironment:
    if os.environ.get("CYRIS_ENVIRONMENT") == "development":
        return CyrisEnvironment.DEVELOPMENT
    return CyrisEnvironment.PRODUCTION


def is_development_environment() -> bool:
    return get_environment() == CyrisEnvironment.DEVELOPMENT


def is_production_environment() -> bool:
    return get_environment() == CyrisEnvironment.PRODUCTION


def time_expiring_lru_cache(max_age_seconds: int, max_size: int = 5, **kwargs):  # type: ignore[no-untyped-def]
    """
    A decorator to cache function call return values, except they expire after `max_age_seconds`
    """

    def decorator(fxn):  # type: ignore[no-untyped-def]
        @lru_cache(maxsize=max_size, **kwargs)
        def _new(*args, time_salt: int, **kwargs):  # type: ignore[no-untyped-def]
            return fxn(*args, **kwargs)

        @wraps(fxn)
        def _wrapped(*args, **kwargs):  # type: ignore[no-untyped-def]
            return _new(*args, **kwargs, time_salt=int(time.time() / max_age_seconds))

        return _wrapped

    return decorator
