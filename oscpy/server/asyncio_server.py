import asyncio
import socket
from functools import partial
from logging import getLogger
from typing import Awaitable

from oscpy.server import OSCBaseServer


logger = getLogger(__name__)


class OSCAsyncioServer(OSCBaseServer):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.listeners = {}
        self._termination_event = asyncio.Event()

    def listen(self, address='localhost', port=0, default=False, family='inet', **kwargs):
        loop = asyncio.get_event_loop()
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

        sock = self.get_socket(
            family=family_,
            addr=addr,
        )
        self.listeners[(address, port or sock.getsockname()[1])] = loop.create_datagram_endpoint(
            partial(OSCProtocol, self.handle_message, sock),
            sock=sock,
        )
        self.add_socket(sock, default)
        return sock

    async def process(self):
        return await asyncio.gather(
            *self.listeners.values(),
            return_exceptions=True,
        )

    async def handle_message(self, data, sender, sender_socket):
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
            except asyncio.CancelledError:
                ...
            except Exception:
                if self.intercept_errors:
                    logger.exception("Ignoring unhandled exception caught in oscpy server")
                else:
                    raise

    def stop(self, sock=None):
        """Close and remove a socket from the server's sockets.

        If `sock` is None, uses the default socket for the server.

        """
        if not sock and self.default_socket:
            sock = self.default_socket

        if sock in self.sockets:
            sock.close()
            self.sockets.remove(sock)
        else:
            raise RuntimeError('{} is not one of my sockets!'.format(sock))

    def stop_all(self):
        for sock in self.sockets[:]:
            self.stop(sock)

    async def join_server(self, timeout=None):
        """Wait for the server to exit (`terminate_server()` must have been called before).

        Returns True if and only if the inner thread exited before timeout."""
        return await self._termination_event.wait()


class OSCProtocol(asyncio.DatagramProtocol):
    def __init__(self, message_handler, sock, **kwargs):
        super().__init__(**kwargs)
        self.message_handler = message_handler
        self.socket = sock
        self.loop = asyncio.get_event_loop()

    def connection_made(self, transport):
        self.transport = transport

    def datagram_received(self, data, addr):
        self.loop.call_soon(
            lambda: asyncio.ensure_future(self.message_handler(data, addr, self.socket))
        )

    def getsockname(self):
        return self.socket.getsockname()
