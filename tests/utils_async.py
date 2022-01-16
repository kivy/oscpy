from functools import partial
from typing import Awaitable
from time import sleep
import asyncio

import curio
import trio
from oscpy.server.curio_server import OSCCurioServer
from oscpy.server.trio_server import OSCTrioServer
from oscpy.server.asyncio_server import OSCAsyncioServer
from oscpy.server.thread_server import OSCThreadServer

def _await(something, osc, args=None, kwargs=None, timeout=1):
    args = args or []
    kwargs = kwargs or {}
    if isinstance(osc, OSCTrioServer):
        return trio.run(partial(something, *args, **kwargs))
    if isinstance(osc, OSCCurioServer):
        async def wrapper():
            result = something(*args, **kwargs)
            if isinstance(result, Awaitable):
                result = await result
            return result
        return curio.run(wrapper)
    else:
        return something(*args, **kwargs)

async def _trio_with_timout(process, timeout):
    with trio.move_on_after(timeout):
        await process()

def runner(osc, timeout=1, socket=None):
    if isinstance(osc, OSCThreadServer):
        sleep(timeout)
        if socket:
            osc.stop(socket)
        else:
            osc.stop_all()
    elif isinstance(osc, OSCCurioServer):
        try:
            curio.run(curio.timeout_after(timeout, osc.process))
        except curio.TaskTimeout:
            ...
    elif isinstance(osc, OSCTrioServer):
        trio.run(lambda: _trio_with_timout(osc.process, timeout))
    elif isinstance(osc, OSCAsyncioServer):
        loop = asyncio.get_event_loop()
        loop.run_until_complete(osc.process())

def _callback(osc, function):
    if isinstance(osc, OSCAsyncioServer):
        async def _(*args, **kwargs):
            return function(*args, **kwargs)
        return _
    return function
