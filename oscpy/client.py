import socket
from oscpy.parser import format_message, format_bundle

SOCK = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)


def send_message(osc_address, values, ip_address, port, sock=None):
    if not sock:
        sock = SOCK
    sock.sendto(
        format_message(osc_address, values),
        (ip_address, port)
    )


def send_bundle(messages, ip_address, port, timetag=None, sock=None):
    '''Send a bundle built from the `messages` iterable.
    each item in the `messages` list should be a two-tuple of the form:
    (address, values).

    example:
        (
            ('/create', ['name', 'value']),
            ('/select', ['name']),
            ('/update', ['name', 'value2']),
            ('/delete', ['name']),
        )

    timetag is optional but can be a float of the number of seconds
    since 1970 when the events described in the bundle should happen.
    '''
    if not sock:
        sock = SOCK
    sock.sendto(
        format_bundle(messages, timetag=timetag),
        (ip_address, port),
    )


class OSCClient(object):
    def __init__(self, address, port, sock=None):
        self.address = address
        self.port = port
        self.sock = sock or SOCK

    def send_message(self, address, values):
        send_message(address, values, self.address, self.port, self.sock)

    def send_bundle(self, messages, timetag=None):
        send_bundle(
            messages, self.address, self.port, timetag=timetag, sock=self.sock)
