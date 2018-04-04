from threading import Thread
from select import select
import socket
import inspect
from time import sleep

from oscpy.parser import read_packet
from oscpy.client import send_bundle, send_message


class OSCThreadServer(object):
    def __init__(self, drop_late_bundles=False):
        self.addresses = {}
        self.sockets = []
        self.timeout = 0.01
        self.default_socket = None
        self.drop_late_bundles = drop_late_bundles
        t = Thread(target=self._listen)
        t.daemon = True
        t.start()

    def bind(self, address, callback, socket=None):
        if not socket and self.default_socket:
            socket = self.default_socket
        elif not socket:
            raise RuntimeError('no default socket yet and no socket provided')

        callbacks = self.addresses.get((socket, address), [])
        if callback not in callbacks:
            callbacks.append(callback)
        self.addresses[(socket, address)] = callbacks

    def listen(self, address='localhost', port=0, default=False):
        '''starts listening on an (address, port)
        - if port is 0, the system will allocate a free port
        - if default is True, the instance will save this socket as the
          default one for subsequent calls to methods with an optional socket
        '''
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.bind((address, port))
        # sock.setblocking(0)
        self.sockets.append(sock)
        if default and not self.default_socket:
            self.default_socket = sock
        elif default:
            raise RuntimeError(
                'Only one default socket authorized! Please set '
                'default=False to other calls to listen()'
            )
        return sock

    def getaddress(self, sock=None):
        '''wraps call to getsockname
        '''
        if not sock and self.default_socket:
            sock = self.default_socket
        elif not sock:
            raise RuntimeError('no default socket yet and no socket provided')

        return sock.getsockname()

    def stop(self, s):
        if s in self.sockets:
            s.close()
            self.sockets.remove(s)

    def stop_all(self):
        for s in self.sockets[:]:
            self.stop(s)

    def _listen(self):
        while True:
            drop_late = self.drop_late_bundles
            if not self.sockets:
                sleep(.01)
                continue
            elif len(self.sockets) < 5:
                read = self.sockets
            else:
                read, write, error = select(self.sockets, [], [], self.timeout)

            for sender_socket in read:
                data, sender = sender_socket.recvfrom(65535)
                for address, types, values, offset in read_packet(
                    data, drop_late=drop_late
                ):
                    for cb in self.addresses.get((sender_socket, address), []):
                        cb(*values)

    def send_message(self, osc_address, values, ip_address, port, sock=None):
        '''Send a message or bundle to another server
        '''
        if not sock and self.default_socket:
            sock = self.default_socket
        elif not sock:
            raise RuntimeError('no default socket yet and no socket provided')

        send_message(osc_address, values, ip_address, port, sock=sock)

    def send_bundle(self, messages, ip_address, port, timetag=None, sock=None):
        '''Send a bundle of messages to another server
        messages should be an iterable of items of the form (address, values)
        '''
        if not sock and self.default_socket:
            sock = self.default_socket
        elif not sock:
            raise RuntimeError('no default socket yet and no socket provided')

        send_bundle(messages, ip_address, port, sock=sock)

    def answer(self, address=None, values=None, bundle=None, timetag=None):
        '''Answers a message or bundle to a client
        this method can only be called from a callback, it will lookup
        the sender of the packet that triggered the callback, and send
        the given message or bundle to it.

        `timetag` is only used if `bundle` is True.
        '''
        if not values:
            values = []
        frames = inspect.getouterframes(inspect.currentframe())
        for frame, filename, line, function, lines, index in frames:
            if function == '_listen' and __file__.startswith(filename):
                break
        else:
            raise RuntimeError('answer() not called from a callback')

        ip_address, port = frame.f_locals.get('sender')
        sock = frame.f_locals.get('sender_socket')

        if bundle:
            self.send_bundle(
                bundle, ip_address, port, timetag=timetag, sock=sock)
        else:
            self.send_message(address, values, ip_address, port, sock=sock)

    def address(self, address, sock=None):
        if not sock and self.default_socket:
            sock = self.default_socket
        elif not sock:
            raise RuntimeError('no default socket yet and no socket provided')

        def decorator(callback):
            self.bind(address, callback, sock)
            return callback
        return decorator
