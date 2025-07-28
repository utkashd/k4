import time
from functools import lru_cache, wraps


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
