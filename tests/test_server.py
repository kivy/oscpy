import socket
from time import time

from oscpy.server import OSCThreadServer
from oscpy.parser import format_message


def test_instance():
    osc = OSCThreadServer()


def test_listen():
    osc = OSCThreadServer()
    sock = osc.listen()
    osc.stop(sock)


def test_bind():
    osc = OSCThreadServer()
    sock = osc.listen()
    port = sock.getsockname()[1]
    cont = []

    def success(*values):
        cont.append(True)

    osc.bind(sock, b'/success', success)

    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    s.sendto(
        format_message(b'/success', [b"test", b"test", 1, 1.2345]),
        ('localhost', port)
    )

    timeout = time() + 5
    while not cont:
        if time() > timeout:
            raise OSError('timeout while waiting for  success message.')


def test_decorator():
    osc = OSCThreadServer()
    sock = osc.listen()
    port = sock.getsockname()[1]
    cont = []

    @osc.address(sock, '/success')
    def success(*values):
        cont.append(True)

    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    s.sendto(
        format_message(b'/success', [b"test", b"test", 1, 1.2345]),
        ('localhost', port)
    )

    timeout = time() + 5
    while not cont:
        if time() > timeout:
            raise OSError('timeout while waiting for  success message.')
