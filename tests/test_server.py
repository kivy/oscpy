import socket
from time import time

from oscpy.server import OSCThreadServer
from oscpy.parser import format_message
from oscpy.client import send_message, send_bundle


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

    send_message(b'/success', [b'test', 1, 1.12345], 'localhost', port)

    timeout = time() + 5
    while not cont:
        if time() > timeout:
            raise OSError('timeout while waiting for success message.')


def test_decorator():
    osc = OSCThreadServer()
    sock = osc.listen()
    port = sock.getsockname()[1]
    cont = []

    @osc.address(sock, b'/success')
    def success(*values):
        cont.append(True)

    send_message(b'/success', [b'test', 1, 1.12345], 'localhost', port)

    timeout = time() + 1
    while not cont:
        if time() > timeout:
            raise OSError('timeout while waiting for success message.')
