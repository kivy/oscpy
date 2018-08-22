"""Server API.

This module currently only implements `OSCThreadServer`, a thread based server.
"""

from threading import Thread

from select import select
import socket
import inspect
from time import sleep
import os
import re
from sys import platform

from oscpy.parser import read_packet, UNICODE
from oscpy.client import send_bundle, send_message


def ServerClass(cls):
    """Decorate classes with for methods implementing OSC endpoints.

    This decorator is necessary on your class if you want to use the
    `address_method` decorator on its methods, see
    `:meth:OSCThreadServer.address_method`'s documentation.
    """
    cls_init = cls.__init__

    def __init__(self, *args, **kwargs):
        cls_init(self, *args, **kwargs)

        for m in dir(self):
            meth = getattr(self, m)
            if hasattr(meth, '_address'):
                server, address, sock = meth._address
                server.bind(address, meth, sock)

    cls.__init__ = __init__
    return cls


class OSCThreadServer(object):
    """A thread-based OSC server.

    Listens for osc messages in a thread, and dispatches the messages
    values to callbacks from there.
    """

    def __init__(
        self, drop_late_bundles=False, timeout=0.01, advanced_matching=False,
        encoding='', encoding_errors='strict'
    ):
        """Create an OSCThreadServer.

        - `timeout` is a number of seconds used as a time limit for
          select() calls in the listening thread, optiomal, defaults to
          0.01.
        - `drop_late_bundles` instruct the server not to dispatch calls
          from bundles that arrived after their timetag value.
          (optional, defaults to False)
        - `advanced_matching` (defaults to False), setting this to True
          activates the pattern matching part of the specification, let
          this to False if you don't need it, as it triggers a lot more
          computation for each received message.
        - `encoding` if defined, will be used to encode/decode all
          strings sent/received to/from unicode/string objects, if left
          empty, the interface will only accept bytes and return bytes
          to callback functions.
        - `encoding_errors` if `encoding` is set, this value will be
          used as `errors` parameter in encode/decode calls.
        """
        self.addresses = {}
        self.sockets = []
        self.timeout = timeout
        self.default_socket = None
        self.drop_late_bundles = drop_late_bundles
        self.advanced_matching = advanced_matching
        self.encoding = encoding
        self.encoding_errors = encoding_errors
        t = Thread(target=self._listen)
        t.daemon = True
        t.start()

        self._smart_address_cache = {}
        self._smart_part_cache = {}

    def bind(self, address, callback, sock=None):
        """Bind a callback to an osc address.

        A socket in the list of existing sockets of the server can be
        given. If no socket is provided, the default socket of the
        server is used, if no default socket has been defined, a
        RuntimeError is raised.

        Multiple callbacks can be bound to the same address.
        """
        if not sock and self.default_socket:
            sock = self.default_socket
        elif not sock:
            raise RuntimeError('no default socket yet and no socket provided')

        if isinstance(address, UNICODE) and self.encoding:
            address = address.encode(
                self.encoding, errors=self.encoding_errors)

        if self.advanced_matching:
            address = self.create_smart_address(address)

        callbacks = self.addresses.get((sock, address), [])
        if callback not in callbacks:
            callbacks.append(callback)
        self.addresses[(sock, address)] = callbacks

    def create_smart_address(self, address):
        """Create an advanced matching address from a string.

        The address will be split by '/' and each part will be converted
        into a regexp, using the rules defined in the OSC specification.
        """
        cache = self._smart_address_cache

        if address in cache:
            return cache[address]

        else:
            parts = address.split(b'/')
            smart_parts = tuple(
                re.compile(self._convert_part_to_regex(part)) for part in parts
            )
            cache[address] = smart_parts
            return smart_parts

    def _convert_part_to_regex(self, part):
        cache = self._smart_part_cache

        if part in cache:
            return cache[part]

        else:
            r = [b'^']
            for i, _ in enumerate(part):
                # getting a 1 char byte string instead of an int in
                # python3
                c = part[i:i + 1]
                if c == b'?':
                    r.append(b'.')
                elif c == b'*':
                    r.append(b'.*')
                elif c == b'[':
                    r.append(b'[')
                elif c == b'!' and r and r[-1] == b'[':
                    r.append(b'^')
                elif c == b']':
                    r.append(b']')
                elif c == b'{':
                    r.append(b'(')
                elif c == b',':
                    r.append(b'|')
                elif c == b'}':
                    r.append(b')')
                else:
                    r.append(c)

            r.append(b'$')

            smart_part = re.compile(b''.join(r))

            cache[part] = smart_part
            return smart_part

    def unbind(self, address, callback, sock=None):
        """Unbind a callback from an OSC address.

        See `bind` for `sock` documentation.
        """
        if not sock and self.default_socket:
            sock = self.default_socket
        elif not sock:
            raise RuntimeError('no default socket yet and no socket provided')

        callbacks = self.addresses.get((sock, address), [])
        while callback in callbacks:
            callbacks.remove(callback)
        self.addresses[(sock, address)] = callbacks

    def listen(
        self, address='localhost', port=0, default=False, family='inet'
    ):
        """Start listening on an (address, port).

        - if `port` is 0, the system will allocate a free port
        - if `default` is True, the instance will save this socket as the
          default one for subsequent calls to methods with an optional socket
        - `family` accepts the 'unix' and 'inet' values, a socket of the
          corresponding type will be created.
          If family is 'unix', then the address must be a filename, the
          `port` value won't be used. 'unix' sockets are not defined on
          Windows.

        The socket created to listen is returned, and can be used later
        with methods accepting the `sock` parameter.
        """
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

    def close(self, sock=None):
        """Close a socket opened by the server."""
        if not sock and self.default_socket:
            sock = self.default_socket
        elif not sock:
            raise RuntimeError('no default socket yet and no socket provided')

        if platform != 'win32' and sock.family == socket.AF_UNIX:
            os.unlink(sock.getsockname())
        else:
            sock.close()

        if sock == self.default_socket:
            self.default_socket = None

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

    def stop(self, s):
        """Close and remove a socket from the server's sockets."""
        if s in self.sockets:
            s.close()
            self.sockets.remove(s)
        else:
            raise RuntimeError('{} is not one of my sockets!'.format(s))

    def stop_all(self):
        """Call stop on all the existing sockets."""
        for s in self.sockets[:]:
            self.stop(s)

    def _listen(self):
        """(internal) Busy loop to listen for events.

        This method is called in a thread by the `listen` method, and
        will be the one actually listening for messages on the server's
        sockets, and calling the callbacks when messages are received.
        """
        match = self._match_address
        advanced_matching = self.advanced_matching
        addresses = self.addresses

        while True:
            drop_late = self.drop_late_bundles
            if not self.sockets:
                sleep(.01)
                continue
            else:
                read, write, error = select(self.sockets, [], [], self.timeout)

            for sender_socket in read:
                data, sender = sender_socket.recvfrom(65535)
                for address, types, values, offset in read_packet(
                    data, drop_late=drop_late, encoding=self.encoding,
                    encoding_errors=self.encoding_errors
                ):
                    if advanced_matching:
                        for sock, addr in addresses:
                            if sock == sender_socket and match(addr, address):
                                for cb in addresses[(sock, addr)]:
                                    cb(*values)

                    else:
                        for cb in addresses.get((sender_socket, address), []):
                            cb(*values)

    @staticmethod
    def _match_address(smart_address, target_address):
        """(internal) Check if provided `smart_address` matches address.

        A `smart_address` is a list of regexps to match
        against the parts of the `target_address`.
        """
        target_parts = target_address.split(b'/')
        if len(target_parts) != len(smart_address):
            return False

        return all(
            model.match(part)
            for model, part in
            zip(smart_address, target_parts)
        )

    def send_message(
        self, osc_address, values, ip_address, port, sock=None, safer=False
    ):
        """Shortcut to the client's `send_message` method.

        Use the default_socket of the server by default.
        See `client.send_message` for more info about the parameters.
        """
        if not sock and self.default_socket:
            sock = self.default_socket
        elif not sock:
            raise RuntimeError('no default socket yet and no socket provided')

        send_message(
            osc_address, values, ip_address, port, sock=sock, safer=safer)

    def send_bundle(
        self, messages, ip_address, port, timetag=None, sock=None, safer=False
    ):
        """Shortcut to the client's `send_bundle` method.

        Use the `default_socket` of the server by default.
        See `client.send_bundle` for more info about the parameters.
        """
        if not sock and self.default_socket:
            sock = self.default_socket
        elif not sock:
            raise RuntimeError('no default socket yet and no socket provided')

        send_bundle(messages, ip_address, port, sock=sock, safer=safer)

    def answer(
        self, address=None, values=None, bundle=None, timetag=None,
        safer=False, port=None
    ):
        """Answers a message or bundle to a client.

        This method can only be called from a callback, it will lookup
        the sender of the packet that triggered the callback, and send
        the given message or bundle to it.

        `timetag` is only used if `bundle` is True.
        See `send_message` and `send_bundle` for info about the parameters.

        Only one of `values` or `bundle` should be defined, if `values`
        is defined, `send_message` is used with it, if `bundle` is
        defined, `send_bundle` is used with its value.
        """
        if not values:
            values = []
        frames = inspect.getouterframes(inspect.currentframe())
        for frame, filename, line, function, lines, index in frames:
            if function == '_listen' and __file__.startswith(filename):
                break
        else:
            raise RuntimeError('answer() not called from a callback')

        ip_address, response_port = frame.f_locals.get('sender')
        if port is not None:
            response_port = port
        sock = frame.f_locals.get('sender_socket')

        if bundle:
            self.send_bundle(
                bundle, ip_address, response_port, timetag=timetag, sock=sock,
                safer=safer
            )
        else:
            self.send_message(
                address, values, ip_address, response_port, sock=sock
            )

    def address(self, address, sock=None):
        """Decorate functions to bind them from their definition.

        `address` is the osc address to bind to the callback.

        example:
            server = OSCThreadServer()
            server.listen('localhost', 8000, default=True)

            @server.address(b'/printer')
            def printer(values):
                print(values)

            send_message(b'/printer', [b'hello world'])

        note:
            This won't work on methods as it'll call them as normal
            functions, and the callback won't get a `self` argument.

            To bind a method use the `address_method` decorator.
        """
        def decorator(callback):
            self.bind(address, callback, sock)
            return callback

        return decorator

    def address_method(self, address, sock=None):
        """Decorate methods to bind them from their definition.

        The class defining the method must itself be decorated with the
        `ServerClass` decorator, the methods will be bound to the
        address when the class is instantiated.

        example:

            osc = OSCThreadServer()
            osc.listen(default=True)

            @ServerClass
            class MyServer(object):

                @osc.address_method(b'/test')
                def success(*args):
                    print("success!", args)
        """
        def decorator(decorated):
            decorated._address = (self, address, sock)
            return decorated

        return decorator
