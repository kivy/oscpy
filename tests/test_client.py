from oscpy.client import send_message, send_bundle, OSCClient
from oscpy.server import OSCThreadServer
from time import time


def test_send_message():
    osc = OSCThreadServer()
    sock = osc.listen()
    port = sock.getsockname()[1]
    acc = []

    def success(*values):
        print("success called")
        acc.append(values[0])

    osc.bind(sock, b'/success', success)

    timeout = time() + 5
    while len(acc) < 100:
        if time() > timeout:
            raise OSError('timeout while waiting for  success message.')

        send_message(b'/success', [1], 'localhost', port)


def test_send_bundle():
    osc = OSCThreadServer()
    sock = osc.listen()
    port = sock.getsockname()[1]
    acc = []

    def success(*values):
        acc.append(values[0])

    osc.bind(sock, b'/success', success)

    timeout = time() + 5
    while len(acc) < 100:
        if time() > timeout:
            raise OSError('timeout while waiting for  success message.')

        send_bundle(
            [
                (b'/success', [i])
                for i in range(10)
            ],
            'localhost', port
        )


def test_oscclient():
    osc = OSCThreadServer()
    sock = osc.listen()
    port = sock.getsockname()[1]
    acc = []

    def success(*values):
        acc.append(values[0])

    osc.bind(sock, b'/success', success)

    client = OSCClient('localhost', port)

    timeout = time() + 5
    while len(acc) < 50:
        if time() > timeout:
            raise OSError('timeout while waiting for  success message.')

        client.send_message(b'/success', [1])

    while len(acc) < 100:
        if time() > timeout:
            raise OSError('timeout while waiting for  success message.')

        client.send_bundle(
            [
                (b'/success', [i])
                for i in range(10)
            ]
        )
