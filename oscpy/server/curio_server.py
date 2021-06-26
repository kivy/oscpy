import logging

from curio import TaskGroup, socket
from oscpy.server import OSCBaseServer, UDP_MAX_SIZE

logging.basicConfig()
logger = logging.getLogger(__name__)


class OSCCurioServer(OSCBaseServer):

    @staticmethod
    def get_socket(family, addr):
        # identical to the parent method, except here socket is curio.socket
        sock = socket.socket(family, socket.SOCK_DGRAM)
        sock.bind(addr)
        return sock

    async def _listen(self, sock):
        async with TaskGroup(wait=all) as g:
            while self._must_loop:
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
        async with TaskGroup(wait=all) as g:
            self.tasks_group = g
            for s in self.sockets:
                await g.spawn(self._listen, s)

    async def stop_all(self):
        await self.tasks_group.cancel_remaining()
