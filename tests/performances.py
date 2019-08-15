"""A crude performance assessment of oscpy."""
from oscpy.server import OSCThreadServer
from oscpy.client import send_message
from oscpy.parser import format_message, read_message

from time import time, sleep
import socket
import os

DURATION = 1

patterns = [
    [],
    [b'B' * 65435],
    [b'test'],
    [b'test', b'auie nstau'],
    [b'test', b'auie nstau'] * 5,
    [1.2345],
    [1.2345, 1.2345, 10000000000.],
    list(range(500)),
]

print("#" * 80)
print("format/parse test")

for i, pattern in enumerate(patterns):
    print("*" * 100)
    print(f"pattern: {i}")
    n = 0
    timeout = time() + DURATION

    while time() < timeout:
        n += 1
        p, s = format_message(b'/address', pattern)

    size = len(p) / 1000
    print(
        f"formated message {n} times ({n / DURATION}/s) "
        f"({n * size / DURATION:.2f}MB/s)"
    )

    n = 0
    timeout = time() + DURATION

    while time() < timeout:
        n += 1
        read_message(p)

    print(
        f"parsed message {n} times ({n / DURATION}/s) "
        f"({n * size / DURATION:.2f}MB/s)"
    )


    n = 0
    timeout = time() + DURATION

    while time() < timeout:
        n += 1
        read_message(format_message(b'/address', pattern)[0])

    print(
        f"round-trip {n} times ({n / DURATION}/s) "
        f"({n * size / DURATION:.2f}MB/s)"
    )


print("#" * 80)
print("sending/receiving test")
# address, port = osc.getaddress()

received = 0


def count(*values):
    """Count calls."""
    global received
    received += 1


for family in 'unix', 'inet':
    osc = OSCThreadServer()
    print(f"family: {family}")
    if family == 'unix':
        address, port = '/tmp/test_sock', 0
        if os.path.exists(address):
            os.unlink(address)
        sock = SOCK = osc.listen(address=address, family='unix')
    else:
        SOCK = sock = osc.listen()
        address, port = osc.getaddress(sock)

    osc.bind(b'/count', count, sock=sock)
    for i, pattern in enumerate(patterns):
        for safer in (False, True):
            timeout = time() + DURATION
            sent = 0
            received = 0

            while time() < timeout:
                send_message(
                    b'/count', pattern, address, port, sock=SOCK, safer=safer
                )
                sent += 1
            sleep(10e-9)

            size = len(format_message(b'/count', pattern)[0]) / 1000.

            print(
                f"{i}: safe: {safer}\t",
                f"sent:\t{sent}\t({sent / DURATION}/s)\t({sent * size / DURATION:.2f}MB/s)\t"                  # noqa
                f"received:\t{received}\t({received / DURATION}/s)\t({received * size / DURATION:.2f}MB/s)\t"  # noqa
                f"loss {((sent - received) / sent) * 100}%"
            )

    if family == 'unix':
        os.unlink(address)
    osc.stop_all()
