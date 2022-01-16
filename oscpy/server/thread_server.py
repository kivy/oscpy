import logging
from threading import Thread

from time import sleep
from select import select
import socket

from oscpy.server import OSCBaseServer, UDP_MAX_SIZE

logger = logging.getLogger(__name__)


class OSCThreadServer(OSCBaseServer):
    """A thread-based OSC server.

    Listens for osc messages in a thread, and dispatches the messages
    values to callbacks from there.

    The '/_oscpy/' namespace is reserved for metadata about the OSCPy
    internals, please see package documentation for further details.
    """

    def __init__(self, *args, **kwargs):
        super(OSCThreadServer, self).__init__(*args, **kwargs)
        t = Thread(target=self._run_listener)
        t.daemon = True
        t.start()
        self._thread = t

    def stop(self, s=None):
        """Close and remove a socket from the server's sockets.

        If `sock` is None, uses the default socket for the server.

        """
        if not s and self.default_socket:
            s = self.default_socket

        if s in self.sockets:
            read = select([s], [], [], 0)
            s.close()
            if s in read:
                s.recvfrom(UDP_MAX_SIZE)
            self.sockets.remove(s)
            if s is self.default_socket:
                self.default_socket = None
        else:
            raise RuntimeError('{} is not one of my sockets!'.format(s))

    def stop_all(self):
        """Call stop on all the existing sockets."""
        for s in self.sockets[:]:
            self.stop(s)
        sleep(10e-9)

    def _run_listener(self):
        """Wrapper just ensuring that the handler thread cleans up on exit."""
        try:
            self._listen()
        finally:
            self._termination_event.set()

    def _listen(self):
        """(internal) Busy loop to listen for events.

        This method is called in a thread by the `listen` method, and
        will be the one actually listening for messages on the server's
        sockets, and calling the callbacks when messages are received.
        """

        while not self._termination_event.is_set():
            if not self.sockets:
                sleep(.01)
                continue
            else:
                try:
                    read, write, error = select(self.sockets, [], [], self.timeout)
                except (ValueError, socket.error):
                    continue

            for sender_socket in read:
                try:
                    data, sender = sender_socket.recvfrom(UDP_MAX_SIZE)
                except ConnectionResetError:
                    continue

                self.handle_message(data, sender, sender_socket)

    def join_server(self, timeout=None):
        result = super(OSCThreadServer, self).join_server(timeout=timeout)
        self._thread.join(timeout=timeout)
        return result
