import socket
from random import randint
from time import time

from oscpy.server import OSCThreadServer
from oscpy.parser import format_message


def test_instance():
    osc = OSCThreadServer()


def test_listen():
    osc = OSCThreadServer()
    sock = osc.listen(port=9000)
    osc.stop(sock)


def test_bind():
    osc = OSCThreadServer()
    port = randint(9000, 9100)
    sock = osc.listen(port=port)
    cont = []

    def success(*values):
        print("success called")
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
