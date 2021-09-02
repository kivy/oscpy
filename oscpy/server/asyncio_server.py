import asyncio
import socket
from functools import partial

from oscpy.server import OSCBaseServer


class OSCAsyncioServer(OSCBaseServer):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.listeners = {}
        self._termination_event = asyncio.Event()

    def listen(self, address='localhost', port=0, default=False, family='inet', **kwargs):
        loop = asyncio.get_event_loop()
        addr = (address, port)
        sock = self.get_socket(
            family=socket.AF_UNIX if family == 'unix' else socket.AF_INET,
            addr=addr,
        )
        self.listeners[addr] = awaitable = loop.create_datagram_endpoint(
            partial(OSCProtocol, self.handle_message, sock),
            sock=sock,
        )
        self.add_socket(sock, default)
        return awaitable

    async def process(self):
        return await asyncio.gather(
            *self.listeners.values(),
            return_exceptions=True,
        )

    async def handle_message(self, data, sender, sender_socket):
        for callbacks, values, address in self.callbacks(data, sender, sender_socket):
            await self._execute_callbacks(callbacks, address, values)

    async def _execute_callbacks(self, callbacks_list, address, values):
        print(locals())
        for cb, get_address in callbacks_list:
            try:
                if get_address:
                    await cb(address, *values)
                else:
                    await cb(*values)
            except Exception:
                if self.intercept_errors:
                    logger.error("Unhandled exception caught in oscpy server", exc_info=True)
                else:
                    raise

    async def join_server(self, timeout=None):
        """Wait for the server to exit (`terminate_server()` must have been called before).

        Returns True if and only if the inner thread exited before timeout."""
        return await self._termination_event.wait()


class OSCProtocol(asyncio.DatagramProtocol):
    def __init__(self, message_handler, sock, **kwargs):
        super().__init__(**kwargs)
        self.message_handler = message_handler
        self._socket = sock
        self.loop = asyncio.get_event_loop()

    def connection_made(self, transport):
        self.transport = transport

    def datagram_received(self, data, addr):
        self.loop.call_soon(
            lambda: asyncio.ensure_future(self.message_handler(data, addr, self._socket))
        )
