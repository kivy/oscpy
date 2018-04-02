from oscpy.client import send_message, send_bundle, OSCClient
from oscpy.server import OSCThreadServer
from time import time


def test_send_message():
    osc = OSCThreadServer()
    sock = osc.listen()
    port = sock.getsockname()[1]
    acc = []

    def success(*values):
        acc.append(values[0])

    osc.bind(b'/success', success, sock)

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

    osc.bind(b'/success', success, sock)

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

    osc.bind(b'/success', success, sock)

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


def test_timetag():
    osc = OSCThreadServer(drop_late_bundles=True)
    osc.drop_late_bundles = True
    sock = osc.listen()
    port = sock.getsockname()[1]
    acc = []

    def success(*values):
        acc.append(True)

    def failure(*values):
        acc.append(False)

    osc.bind(b'/success', success, sock)
    osc.bind(b'/failure', failure, sock)

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
                (b'/failure', [i])
                for i in range(10)
            ],
            timetag=time() - 1
        )

        client.send_bundle(
            [
                (b'/success', [i])
                for i in range(10)
            ],
            timetag=time()
        )

    if False in acc:
        assert False
