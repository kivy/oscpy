import sys
from time import sleep

from oscpy.server import OSCThreadServer

osc = OSCThreadServer(encoding='utf8')
sock = osc.listen(address='0.0.0.0', port=8000, default=True)

@osc.address('/address')
def callback(*values):
    print("got values: {}".format(values))


@osc.address('/stop')
def callback(*values):
    print("time to leave")
    osc.stop_all()
    osc.terminate_server()


# wait until the server exits
osc.join_server()
