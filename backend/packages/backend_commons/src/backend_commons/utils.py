class AsyncObject:
    """
    Taken from
    https://stackoverflow.com/questions/33128325/how-to-set-class-attribute-with-await-in-init

    Inheriting this class allows you to define an object with an async __init__.

    So you can create objects with `await MyClass(params)`
    """

    async def __new__(cls, *a, **kw):  # type: ignore[no-untyped-def]
        instance = super().__new__(cls)
        await instance.__init__(*a, **kw)  # type: ignore[misc]
        return instance

    async def __init__(self):  # type: ignore[no-untyped-def]
        pass
