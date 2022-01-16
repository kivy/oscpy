import os
import logging
from functools import partial
from sys import platform
from typing import Awaitable

from trio import socket, open_nursery, move_on_after
from oscpy.server import OSCBaseServer, UDP_MAX_SIZE

logging.basicConfig()
logger = logging.getLogger(__name__)


class OSCTrioServer(OSCBaseServer):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.nurseries = {}

    @staticmethod
    async def get_socket(family, addr):
        # identical to the parent method, except here socket is trio.socket
        # and bind needs to be awaited
        sock = socket.socket(family, socket.SOCK_DGRAM)
        await sock.bind(addr)
        return sock

    async def listen(
        self, address='localhost', port=0, default=False, family='inet'
    ):
        if family == 'unix':
            family_ = socket.AF_UNIX
        elif family == 'inet':
            family_ = socket.AF_INET
        else:
            raise ValueError(
                "Unknown socket family, accepted values are 'unix' and 'inet'"
            )

        if family == 'unix':
            addr = address
        else:
            addr = (address, port)
        sock = await self.get_socket(family_, addr)
        self.add_socket(sock, default)
        return sock

    async def _listen(self, sock):
        async with open_nursery() as nursery:
            self.nurseries[sock] = nursery
            try:
                while True:
                    data, addr = await sock.recvfrom(UDP_MAX_SIZE)
                    nursery.start_soon(
                        partial(
                            self.handle_message,
                            data,
                            addr,
                            drop_late=False,
                            sender_socket=sock
                        )
                    )
            finally:
                with move_on_after(1) as cleanup_scope:
                    cleanup_scope.shield = True
                    logger.info("socket %s cancelled", sock)
                    await self.stop(sock)

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
                    logger.error("Ignoring unhandled exception caught in oscpy server", exc_info=True)
                else:
                    logger.exception("Unhandled exception caught in oscpy server")
                    raise

    async def process(self):
        async with open_nursery() as nursery:
            self.nursery = nursery
            for s in self.sockets:
                nursery.start_soon(self._listen, s)

    async def stop_all(self):
        """Exit the main nursery, cancelling any in progress task
        """
        self.nursery.cancel_scope.deadline = 0

    async def stop(self, sock=None):
        if sock is None:
            if self.default_socket:
                sock = self.default_socket
            else:
                raise RuntimeError('no default socket yet and no socket provided')
        if sock in self.sockets:
            self.sockets.remove(sock)
        else:
            raise RuntimeError("Socket %s is not managed by this server" % sock)
        sock.close()
        if sock in self.nurseries:
            nursery = self.nurseries.pop(sock)
            nursery.cancel_scope.deadline = 0

        if sock is self.default_socket:
            self.default_socket = None

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
            sock.close()

    def getaddress(self, sock=None):
        """Wrap call to getsockname.

        If `sock` is None, uses the default socket for the server.

        Returns (ip, port) for an inet socket, or filename for an unix
        socket.
        """
        if not sock and self.default_socket:
            sock = self.default_socket
        elif not sock:
            raise RuntimeError('no default socket yet and no socket provided')

        return sock.getsockname()
