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
        return interpret_callback_result(call)
    else:
        raise ValueError("The provided callback cannot be called!")


def interpret_callback_result(result):
    """
    All callback results will be formatted as a tuple in the following form:
    - Boolean status of the callback
    - Any returning data from the callback
    """

    if type(result) == bool:
        return result, None
    elif type(result) == tuple:
        if type(result[0]) == bool:
            return result[0], result[1]
        else:
            return True, result[1]
    elif result is None:
        return False, None
    else:
        return True, result
