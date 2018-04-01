from threading import Thread
from select import select
import socket

from oscpy.parser import read_packet


class OSCThreadServer(object):
    def __init__(self, drop_late_bundles=False):
        self.addresses = {}
        self.sockets = []
        self.timeout = 0
        self.drop_late_bundles = drop_late_bundles
        t = Thread(target=self._listen)
        t.daemon = True
        t.start()

    def bind(self, socket, address, callback):
        callbacks = self.addresses.get((socket, address), [])
        if callback not in callbacks:
            callbacks.append(callback)
        self.addresses[(socket, address)] = callbacks

    def listen(self, address='localhost', port=9000):
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.bind((address, port))
        sock.setblocking(0)
        self.sockets.append(sock)
        return sock

    def stop(self, s):
        if s in self.sockets:
            s.close()
            self.sockets.remove(s)

    def stop_all(self):
        for s in self.sockets[:]:
            self.stop(s)

    def _listen(self):
        while True:
            read, write, error = select(self.sockets, [], [], self.timeout)

            for s in read:
                data = s.recv(1024)
                for address, values in read_packet(data):
                    for cb in self.addresses.get((s, address), []):
                        cb(*values)
