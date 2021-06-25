from time import sleep

from oscpy.server import OSCThreadServer

osc = OSCThreadServer(encoding='utf8')
sock = osc.listen(address='0.0.0.0', port=8000, default=True)

@osc.address('/address')
def callback(*values):
    print("got values: {}".format(values))


# exit after 1000 seconds
sleep(1000)
osc.stop()
