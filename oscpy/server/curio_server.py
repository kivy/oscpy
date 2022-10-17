import logging
from typing import Awaitable
from sys import platform
import os

from curio import TaskGroup, socket
from oscpy.server import OSCBaseServer, UDP_MAX_SIZE
from oscpy.client import async_send_bundle, async_send_message

logging.basicConfig()
logger = logging.getLogger(__name__)


class OSCCurioServer(OSCBaseServer):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.task_groups = {}

    @staticmethod
    def get_socket(family, addr):
        # identical to the parent method, except here socket is curio.socket
        sock = socket.socket(family, socket.SOCK_DGRAM)
        sock.bind(addr)
        return sock

    async def send_message(self,
        osc_address, values, ip_address, port, sock=None, safer=False,
        encoding='', encoding_errors='strict'
    ):
        if not sock and self.default_socket:
            sock = self.default_socket
        elif not sock:
            raise RuntimeError('no default socket yet and no socket provided')
        stats = await async_send_message(
            osc_address,
            values,
            ip_address,
            port,
            sock=sock,
            safer=safer,
            encoding=self.encoding,
            encoding_errors=self.encoding_errors
        )
        self.stats_sent += stats
        return stats

    async def send_bundle(
        self, messages, ip_address, port, timetag=None, sock=None, safer=False
    ):
        """Shortcut to the client's `send_bundle` method.

        Use the `default_socket` of the server by default.
        See `client.send_bundle` for more info about the parameters.
        """
        if not sock and self.default_socket:
            sock = self.default_socket
        elif not sock:
            raise RuntimeError('no default socket yet and no socket provided')

        stats = await async_send_bundle(
            messages,
            ip_address,
            port,
            sock=sock,
            safer=safer,
            encoding=self.encoding,
            encoding_errors=self.encoding_errors
        )
        self.stats_sent += stats
        return stats

    async def _listen(self, sock):
        async with TaskGroup(wait=all) as g:
            self.task_groups[sock] = g
            while not self._termination_event.is_set():
                data, addr = await sock.recvfrom(UDP_MAX_SIZE)
                await g.spawn(
                    self.handle_message(
                        data,
                        addr,
                        drop_late=False,
                        sender_socket=sock
                    )
                )
            await g.join()

    async def handle_message(self, data, sender, drop_late, sender_socket):
        for callbacks, values, address in self.callbacks(data, sender, sender_socket):
            await self._execute_callbacks(callbacks, address, values)

    async def _execute_callbacks(self, callbacks_list, address, values):
        for cb, get_address in callbacks_list:
            try:
                if get_address:
                    result = cb(address, *values)
                else:
                    result = cb(*values)
                if isinstance(result, Awaitable):
                    await result
            except Exception:
                if self.intercept_errors:
                    logger.exception("Ignoring unhandled exception caught in oscpy server")
                else:
                    raise

    async def process(self):
        async with TaskGroup(wait=all) as g:
            self.tasks_group = g
            for s in self.sockets:
                await g.spawn(self._listen, s)

    async def close(self, sock=None):
        """Close a socket opened by the server."""
        if not sock and self.default_socket:
            sock = self.default_socket
        elif not sock:
            raise RuntimeError('no default socket yet and no socket provided')

        if sock not in self.sockets:
            logger.warning("Ignoring requested to close an unknown socket %s" % sock)

        if sock == self.default_socket:
            self.default_socket = None

        if platform != 'win32' and sock.family == socket.AF_UNIX:
            os.unlink(sock.getsockname())
        else:
            await sock.close()

    async def stop_all(self):
        await self.tasks_group.cancel_remaining()

    async def stop(self, sock=None):
        if not sock and self.default_socket:
            sock = self.default_socket

        if sock in self.sockets:
            g = self.task_groups.pop(sock)
            await g.cancel_remaining()
        else:
            raise RuntimeError('{} is not one of my sockets!'.format(sock))
