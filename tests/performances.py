from oscpy.server import OSCThreadServer
from oscpy.client import send_message
from oscpy.parser import format_message, read_message

from time import time, sleep

DURATION = 5

print("#" * 80)
print("format/parse test")

n = 0
timeout = time() + DURATION

while time() < timeout:
    n += 1
    p = format_message(b'/address', [b'test', 1, 1.2345])

print("formated message {} times ({}/s)".format(n, n / DURATION))

n = 0
timeout = time() + DURATION

while time() < timeout:
    n += 1
    read_message(p)

print("parsed message {} times ({}/s)".format(n, n / DURATION))


print("#" * 80)
print("sending/receiving test")
osc = OSCThreadServer()
osc.listen(default=True)
address, port = osc.getaddress()

received = 0

print(address, port)


@osc.address(b'/count')
def count(*values):
    global received
    received += 1


timeout = time() + DURATION
sent = 0

while time() < timeout:
    send_message(b'/count', [b'test', b'auie nstau', 1.2345], address, port)
    sent += 1
    # sleep(delay)

print(
    "sent: {} ({}/s), received: {} ({}/s)"
    .format(sent, sent / DURATION, received, received / DURATION)
)
