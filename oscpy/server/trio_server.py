import logging
from functools import partial

from trio import socket, open_nursery
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

        sock = await self.get_socket(family_, (address, port))
        self.add_socket(sock, default)
        return sock

    async def _listen(self, sock):
        async with open_nursery() as nursery:
            self.nurseries[sock] = nursery
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

    async def handle_message(self, data, sender, drop_late, sender_socket):
        for callbacks, values, address in self.callbacks(data, sender, sender_socket):
            await self._execute_callbacks(callbacks, address, values)

    async def _execute_callbacks(self, callbacks_list, address, values):
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

    async def stop(self, sock):
        nursery = self.nurseries.pop(sock)
        nursery.cancel_scope.deadline = 0

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
