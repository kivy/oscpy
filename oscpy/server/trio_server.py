import logging
from functools import partial

from trio import socket, open_nursery
from oscpy.server import OSCBaseServer, UDP_MAX_SIZE

logging.basicConfig()
logger = logging.getLogger(__name__)


class OSCTrioServer(OSCBaseServer):
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

        sock = await self.get_socket(family_, address, port)
        self.add_socket(sock, default)
        return sock

    async def _listen(self, sock):
        async with open_nursery() as nursery:
            while True:
                data, addr = await sock.recvfrom(UDP_MAX_SIZE)
                nursery.start_soon(
                    partial(
                        self.handle_message_async,
                        data,
                        addr,
                        drop_late=False,
                        sender_socket=sock
                    )
                )

    async def handle_message_async(self, data, sender, drop_late, sender_socket):
        for callbacks, values in self.callbacks(data, sender, drop_late, sender_socket):
            await self._execute_callbacks_async(callbacks, values)

    async def _execute_callbacks_async(self, callbacks_list, values):
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

    async def process(self):
        async with open_nursery() as nursery:
            self.nursery = nursery
            for s in self.sockets:
                nursery.start_soon(self._listen, s)

    async def stop_all(self):
        """Exit the main nursery, cancelling any in progress task
        """
        self.nursery.cancel_scope.deadline = 0
