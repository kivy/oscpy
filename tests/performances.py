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

# print("#" * 80)
# print("format/parse test")

# for pattern in patterns:
#     print("*" * 100)
#     print(f"pattern: {pattern}")
#     n = 0
#     timeout = time() + DURATION

#     while time() < timeout:
#         n += 1
#         p = format_message(b'/address', [b'test', 1, 1.2345])

#     size = len(p) / 1000
#     print(f"formated message {n} times ({n / DURATION}/s) ({n * size / DURATION:.2f}MB/s)")

#     n = 0
#     timeout = time() + DURATION

#     while time() < timeout:
#         n += 1
#         read_message(p)

#     print(f"parsed message {n} times ({n / DURATION}/s) ({n * size / DURATION:.2f}MB/s)")


print("#" * 80)
print("sending/receiving test")
osc = OSCThreadServer()
# address, port = osc.getaddress()

received = 0


def count(*values):
    global received
    received += 1


for family in 'unix', 'inet':
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
    for pattern in patterns:
        timeout = time() + DURATION
        sent = 0
        received = 0

        print("*" * 100)
        # print(f"pattern: {pattern}")

        while time() < timeout:
            send_message(b'/count', pattern, address, port, sock=SOCK)
            sent += 1

        size = len(format_message(b'/count', pattern)) / 1000.

        print(
            f"sent: {sent} ({sent / DURATION}/s) ({sent * size / DURATION:.2f}MB/s)\n"                 # noqa
            f"received: {received} ({received / DURATION}/s)({received * size / DURATION:.2f}MB/s)\n"  # noqa
            f"loss {((sent - received) / sent) * 100}%"
        )

    osc.unbind(b'/count', count, sock=sock)
    if family == 'unix':
        os.unlink(address)
