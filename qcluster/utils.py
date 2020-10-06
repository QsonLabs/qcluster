import inspect


async def call_callback(callback, *args):
    """
    Helper method to execute a callback and await if the callback is async.
    https://stackoverflow.com/a/36077430/6291036

    Args:
        callback: The function to execute.
        *args: Additional arguments to be passed as arguments to the callback.

    Returns:
        The value of the callback after execution.

    Raises:
        ValueError: When the callback is not a callable object.
    """

    if callable(callback):
        call = callback(*args)
        if inspect.isawaitable(call):
            call = await call
        return call
    else:
        raise ValueError("The provided callback cannot be called!")
