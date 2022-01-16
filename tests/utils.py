from sys import version_info
from time import sleep

if version_info > (3, 5, 0):
    from tests.utils_async import _await, runner, _callback
else:
    def runner(osc, timeout=5, socket=None):
        sleep(timeout)
        if socket:
            osc.stop(socket)
        else:
            osc.stop_all()

    def _await(something, osc, args=None, kwargs=None):
        args = args or []
        kwargs = kwargs or {}
        return something(*args, **kwargs)

    def _callback(osc, function):
        return function
