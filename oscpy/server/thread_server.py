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
        else:
            raise RuntimeError('{} is not one of my sockets!'.format(s))

    def stop_all(self):
        """Call stop on all the existing sockets."""
        for s in self.sockets[:]:
            self.stop(s)
        sleep(10e-9)

    def terminate_server(self):
        """Request the inner thread to finish its tasks and exit.

        May be called from an event, too.
        """
        self._must_loop = False

    def join_server(self, timeout=None):
        """Wait for the server to exit (`terminate_server()` must have been called before).

        Returns True if and only if the inner thread exited before timeout."""
        return self._termination_event.wait(timeout=timeout)

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

        while self._must_loop:
            drop_late = self.drop_late_bundles
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

                self.handle_message(data, sender, drop_late, sender_socket)
