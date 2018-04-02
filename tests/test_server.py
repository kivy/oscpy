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

    osc.bind(b'/success', success, sock)

    send_message(b'/success', [b'test', 1, 1.12345], 'localhost', port)

    timeout = time() + 5
    while not cont:
        if time() > timeout:
            raise OSError('timeout while waiting for success message.')


def test_bind_default():
    osc = OSCThreadServer()
    osc.listen(default=True)
    port = osc.getaddress()[1]
    cont = []

    def success(*values):
        cont.append(True)

    osc.bind(b'/success', success)

    send_message(b'/success', [b'test', 1, 1.12345], 'localhost', port)

    timeout = time() + 5
    while not cont:
        if time() > timeout:
            raise OSError('timeout while waiting for success message.')


def test_decorator():
    osc = OSCThreadServer()
    sock = osc.listen(default=True)
    port = sock.getsockname()[1]
    cont = []

    @osc.address(b'/test1', sock)
    def test1(*values):
        print("test1 called")
        cont.append(True)

    @osc.address(b'/test2')
    def test2(*values):
        print("test1 called")
        cont.append(True)

    send_message(b'/test1', [], 'localhost', port)
    send_message(b'/test2', [], 'localhost', port)

    timeout = time() + 1
    while len(cont) < 2:
        if time() > timeout:
            raise OSError('timeout while waiting for success message.')


def test_answer():
    cont = []

    osc_1 = OSCThreadServer()
    osc_1.listen(default=True)

    @osc_1.address(b'/ping')
    def ping(*values):
        print("ping called")
        if True in values:
            cont.append(True)
        else:
            osc_1.answer(b'/pong')

    osc_2 = OSCThreadServer()
    osc_2.listen(default=True)

    @osc_2.address(b'/pong')
    def pong(*values):
        print("pong called")
        osc_2.answer(b'/ping', [True])

    osc_2.send_message(b'/ping', [], *osc_1.getaddress())

    timeout = time() + 1
    while not cont:
        if time() > timeout:
            raise OSError('timeout while waiting for success message.')
