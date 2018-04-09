from threading import Thread

from select import select
import socket
import inspect
from time import sleep
import os

from oscpy.parser import read_packet
from oscpy.client import send_bundle, send_message


class OSCThreadServer(object):
    '''Listen for osc messages in a thread, and dispatches the messages
    values to callbacks from there.
    '''
    def __init__(self, drop_late_bundles=False, timeout=0.01):
        '''
        - `timeout` is a number of seconds used as a time limit for
          select() calls in the listening thread, optiomal, defaults to
          0.01.
        - `drop_late_bundles` instruct the server not to dispatch calls
          from bundles that arrived after their timetag value.
          (optional, defaults to False)
        '''
        self.addresses = {}
        self.sockets = []
        self.timeout = timeout
        self.default_socket = None
        self.drop_late_bundles = drop_late_bundles
        t = Thread(target=self._listen)
        t.daemon = True
        t.start()

    def bind(self, address, callback, sock=None):
        '''Bind a callback to an osc address, a socket in the list of
        existing sockets of the server can be given. If no socket is
        provided, the default socket of the server is used, if no
        default socket has been defined, a RuntimeError is raised.

        multiple callbacks can be bound to the same address.
        '''
        if not sock and self.default_socket:
            sock = self.default_socket
        elif not sock:
            raise RuntimeError('no default socket yet and no socket provided')

        callbacks = self.addresses.get((sock, address), [])
        if callback not in callbacks:
            callbacks.append(callback)
        self.addresses[(sock, address)] = callbacks

    def unbind(self, address, callback, sock=None):
        '''Un bind a callback from an address.
        See `bind` for `sock` documentation.
        '''
        if not sock and self.default_socket:
            sock = self.default_socket
        elif not sock:
            raise RuntimeError('no default socket yet and no socket provided')

        callbacks = self.addresses.get((sock, address), [])
        while callback in callbacks:
            callbacks.remove(callback)
        self.addresses[(sock, address)] = callbacks

    def listen(self, address='localhost', port=0, default=False, family='inet'):
        '''starts listening on an (address, port)
        - if port is 0, the system will allocate a free port
        - if default is True, the instance will save this socket as the
          default one for subsequent calls to methods with an optional socket
        - `family` accept the 'unix' and 'inet' values, a socket of the
          corresponding type will be created.
          If family is 'unix', then the address must be a filename, the
          'port' value won't be used.

        The socket created to listen is returned, and can be used later
        with methods accepting the `sock` parameter.
        '''
        if family == 'unix':
            family_ = socket.AF_UNIX
        elif family == 'inet':
            family_ = socket.AF_INET
        else:
            raise ValueError(
                "Unknown socket family, accepted values are 'unix' and 'inet'"
            )

        sock = socket.socket(family_, socket.SOCK_DGRAM)
        if family == 'unix':
            addr = address
        else:
            addr = (address, port)
        sock.bind(addr)
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

    def close(self, sock):
        '''close a socket opened by the server.
        '''
        if socket.family == 'unix':
            os.path.unlink(sock.address)
        else:
            sock.close()

        if sock == self.default_socket:
            self.default_socket = None

    def getaddress(self, sock=None):
        '''wraps call to getsockname, on the provided socket, or the
        default socket for the server.

        returns (ip, port) for an inet socket, or filename for an unix
        socket.
        '''
        if not sock and self.default_socket:
            sock = self.default_socket
        elif not sock:
            raise RuntimeError('no default socket yet and no socket provided')

        return sock.getsockname()

    def stop(self, s):
        '''close and remove a socket from the server's sockets
        '''
        if s in self.sockets:
            s.close()
            self.sockets.remove(s)

    def stop_all(self):
        '''call stop on all the existing sockets
        '''
        for s in self.sockets[:]:
            self.stop(s)

    def _listen(self):
        '''(internal) this is method is called in a thread by the
        `listen` method, and will be the one actually listening for
        messages on the server's sockets, and calling the callbacks when
        messages are received.
        '''
        while True:
            drop_late = self.drop_late_bundles
            if not self.sockets:
                sleep(.01)
                continue
            elif len(self.sockets) < 2:
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

    def send_message(
        self, osc_address, values, ip_address, port, sock=None, safer=False
    ):
        '''Shortcut to the client's send_message method, using the
        default_socket of the server by default. see
        `client.send_message` for more info about the parameters.
        '''
        if not sock and self.default_socket:
            sock = self.default_socket
        elif not sock:
            raise RuntimeError('no default socket yet and no socket provided')

        send_message(
            osc_address, values, ip_address, port, sock=sock, safer=safer)

    def send_bundle(
        self, messages, ip_address, port, timetag=None, sock=None, safer=False
    ):
        '''Shortcut to the client's send_bundle method, using the
        default_socket of the server by default. see
        `client.send_bundle` for more info about the parameters.
        '''
        if not sock and self.default_socket:
            sock = self.default_socket
        elif not sock:
            raise RuntimeError('no default socket yet and no socket provided')

        send_bundle(messages, ip_address, port, sock=sock, safer=safer)

    def answer(
        self, address=None, values=None, bundle=None, timetag=None, safer=False
    ):
        '''Answers a message or bundle to a client
        this method can only be called from a callback, it will lookup
        the sender of the packet that triggered the callback, and send
        the given message or bundle to it.

        `timetag` is only used if `bundle` is True.
        see `send_message` and `send_bundle` for info about the parameters.

        Only one of `values` or `bundle` should be defined, if `values`
        is defined, `send_message` is used with it, if `bundle` is
        defined, `send_bundle` is used with its value.
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
                bundle, ip_address, port, timetag=timetag, sock=sock,
                safer=safer
            )
        else:
            self.send_message(address, values, ip_address, port, sock=sock)

    def address(self, address, sock=None):
        '''Decorator method to allow binding functions/methods from their definition

        address is the osc address to bind to the callback

        example:
            server = OSCThreadServer()
            server.listen('localhost', 8000, default=True)

            @server.address(b'/printer')
            def printer(values):
                print(values)

            send_message(b'/printer', [b'hello world'])
        '''
        if not sock and self.default_socket:
            sock = self.default_socket
        elif not sock:
            raise RuntimeError('no default socket yet and no socket provided')

        def decorator(callback):
            self.bind(address, callback, sock)
            return callback
        return decorator
