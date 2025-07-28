import time
from functools import lru_cache, wraps
from pathlib import Path
from typing import Any, Callable, Generator, Iterable, Iterator, TypeVar

import diskcache

_ReturnType = TypeVar("_ReturnType")


class biter[_T]:
    """
    Intentionally terrible name. "Better Iterable" except it's short

    You can wrap an iterable with `biter` and then method-chain `.filter()` and `.map()`

    And there's `.reduce()` as well
    """

    def __init__(self, generic_iterable: Iterable[_T]):
        self.generic_iterable = generic_iterable

    def __iter__(self) -> Iterator[_T]:
        return iter(self.generic_iterable)

    def first_value(self) -> _T:
        for value in self.generic_iterable:
            return value
        raise ValueError("No first value; it's empty")

    def filter(self, include_if_true: Callable[[_T], bool]) -> "biter[_T]":
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
                if include_if_true(value):
                    yield value

        return biter(filter_values_generator())

    def map(self, transform: Callable[[_T], _ReturnType]) -> "biter[_ReturnType]":
        def map_values_generator() -> Generator[_ReturnType, Any, None]:
            for value in self:
                yield transform(value)

        return biter(map_values_generator())

    def reduce(
        self, func: Callable[[_T, _ReturnType], _ReturnType], initial_value: _ReturnType
    ) -> _ReturnType:
        accumulated_value = initial_value
        for value in self:
            accumulated_value = func(value, accumulated_value)

        return accumulated_value


class TypedDiskCache[_KeyType, _ValueType](diskcache.Cache):
    """
    A wrapper around `diskcache.Cache` to facilitate some type-safety, IDE suggestions, etc.
    """

    # it doesn't like that **settings isn't typed. Can't blame mypy tbh
    def __init__(  # type: ignore[no-untyped-def]
        self,
        directory: Path,
        timeout: int = 60,
        disk: type[diskcache.Disk] = diskcache.Disk,
        **settings,
    ) -> None:
        """
        Initialize (a typed) cache instance.

        Parameters
        ----------
        directory : Path
            The directory in which the cache (sqlite db) will be written. This should be
            a unique identifier for this cache, i.e., when the application is restarted,
            the directory name will be what enables persistence.

            To lessen the probability of committing an API key to a public repository,
            the cache is saved to `{directory}/.typed_diskcache/`, and
            `.typed_diskcache/*` is part of this repo's `.gitignore`.
        timeout : int, optional
            SQLite connection timeout, by default 60
        disk : type[diskcache.Disk], optional
            Disk type or subclass for serialization, by default Disk
        **settings : any of:

            DEFAULT_SETTINGS = {
                'statistics': 0,  # False
                'tag_index': 0,  # False
                'eviction_policy': 'least-recently-stored',
                'size_limit': 2**30,  # 1gb
                'cull_limit': 10,
                'sqlite_auto_vacuum': 1,  # FULL
                'sqlite_cache_size': 2**13,  # 8,192 pages
                'sqlite_journal_mode': 'wal',
                'sqlite_mmap_size': 2**26,  # 64mb
                'sqlite_synchronous': 1,  # NORMAL
                'disk_min_file_size': 2**15,  # 32kb
                'disk_pickle_protocol': pickle.HIGHEST_PROTOCOL,
            }

        """
        super().__init__(
            directory=str(directory.joinpath(".typed_diskcache")),
            timeout=timeout,
            disk=disk,
            **settings,
        )

    def __getitem__(self, key: _KeyType) -> _ValueType:
        return super().__getitem__(key)  # type: ignore[no-any-return]

    def __setitem__(self, key: _KeyType, value: _ValueType) -> None:
        return super().__setitem__(key, value)

    def keys(self) -> Generator[_KeyType, None, None]:
        return self.iterkeys()

    def items(self) -> Generator[tuple[_KeyType, _ValueType], None, None]:
        """
        For some reason the interface of diskcache.Cache is different than `dict`'s...
        so gotta implement these myself lol
        """
        for key in self.keys():
            yield key, self[key]

    def values(self) -> Generator[_ValueType, None, None]:
        for _, value in self.items():
            yield value

    def create_dict(self) -> dict[_KeyType, _ValueType]:
        return {key: value for key, value in self.items()}

    def __str__(self) -> str:
        """
        _summary_

        Returns
        -------
        _type_
            _description_
        """
        if len(self) == 0:
            return f"{type(self).__name__}(<empty>)"

        key_to_values_str = "\n\t".join(
            f"{key} => {value}" for key, value in self.items()
        )
        return f"{type(self).__name__}(\n\t{key_to_values_str}\n)"  # lmao

    def __repr__(self) -> str:
        """
        Just returns str(self). I'm ignoring that eval(repr(self)) should work.
        """
        return str(self)


def time_expiring_lru_cache(max_age_seconds: int, max_size: int = 5, **kwargs):  # type: ignore[no-untyped-def]
    """
    A decorator to cache function call return values, except they expire after `max_age_seconds`
    """

    # TODO type-hint everything here, otherwise mypy doesn't like to deal with this :)

    def decorator(fxn):  # type: ignore[no-untyped-def]
        @lru_cache(maxsize=max_size, **kwargs)
        def _new(*args, time_salt: int, **kwargs):  # type: ignore[no-untyped-def]
            return fxn(*args, **kwargs)

        @wraps(fxn)
        def _wrapped(*args, **kwargs):  # type: ignore[no-untyped-def]
            return _new(*args, **kwargs, time_salt=int(time.time() / max_age_seconds))

        return _wrapped

    return decorator
