### OSCPy

[![Coverage Status](https://coveralls.io/repos/github/kivy/oscpy/badge.svg?branch=master)](https://coveralls.io/github/kivy/oscpy?branch=master)
[![Build Status](https://travis-ci.org/kivy/oscpy.svg?branch=master)](https://travis-ci.org/kivy/oscpy)

A modern implementation of OSC for python2/3.

#### What is OSC.

OpenSoundControl is an UDP based network protocol, that is designed for fast
dispatching of time-sensitive messages, as the name suggests, it was designed
as a replacement for MIDI, but applies well to other situations. The protocol is
simple to use, OSC addresses look like http URLs, and accept various basic
types, such as string, float, int, etc. You can think of it basically as an
http POST, with less overhead.

You can learn more about OSC on [OpenSoundControl.org](http://opensoundcontrol.org/introduction-osc)

#### Goals

- python2.7/3.6+ compatibility (can be relaxed more on the python3 side
  if needed, but nothing before 2.7 will be supported)
- fast
- easy to use
- robust (returns meaningful errors in case of malformed messages,
  always do the right thing on correct messages)
- separation of concerns (message parsing vs communication)
- sync and async compatibility (threads, asyncio, trio…)
- clean and easy to read code

#### Features

- serialize and parse OSC data types/Messages/Bundles
- a thread based udp server to open sockets and bind callbacks on osc addresses on them
- a simple client

#### Install
```sh
pip install oscpy
```

#### Usage

Server (thread)

```python
from oscpy.server import OSCThreadServer
from time import sleep

def callback(values):
    print("got values: {}".format(values))

osc = OSCThreadServer()
sock = osc.listen(address='0.0.0.0', port=8000, default=True)
osc.bind(b'/address', callback)
sleep(1000)
osc.stop()
```

or you can use the decorator API.

Server (thread)

```python
from oscpy.server import OSCThreadServer
from time import sleep

osc = OSCThreadServer()
sock = osc.listen(address='0.0.0.0', port=8000, default=True)

@osc.address(b'/address')
def callback(values):
    print("got values: {}".format(values))

sleep(1000)
osc.stop()
```

Servers are also client, in the sense they can send messages and answer to
messages from other servers

```python
from oscpy.server import OSCThreadServer
from time import sleep

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
```


Server (async) (TODO!)

```python
from oscpy.server import OSCThreadServer

with OSCAsyncServer(port=8000) as OSC:
    for address, values in OSC.listen():
       if address == b'/example':
            print("got {} on /example".format(values))
       else:
            print("unknown address {}".format(address))
```

Client

```python
from oscpy.client import OSCClient

osc = OSCClient(address, port)
for i in range(10):
    osc.send_message(b'/ping', [i])
```

#### Unicode

By default, the server and client take bytes (encoded strings), not unicode
strings, for osc addresses as well as osc strings. However, you can pass an
`encoding` parameter to have your strings automatically encoded and decoded by
them, so your callbacks will get unicode strings (unicode in python2, str in
python3).

```python
osc = OSCThreadServer(encoding='utf8')
osc.listen(default=True)

values = []

@osc.address(u'/encoded')
def encoded(*val):
    for v in val:
        assert not isinstance(v, bytes)
    values.append(val)

send_message(
    u'/encoded',
    [u'hello world', u'ééééé ààààà'],
    *osc.getaddress(), encoding='utf8')
```

(`u` literals added here for clarity).

#### TODO

- real support for timetag (currently only supports optionally
  dropping late bundles, not delaying those with timetags in the future)
- support for additional argument types
- an asyncio-oriented server implementation
- examples & documentation

#### Contributing

Check out our [contribution guide](CONTRIBUTING.md) and feel free to improve OSCPy.

#### License

OSCPy is released under the terms of the MIT License.
Please see the [LICENSE.txt](LICENSE.txt) file.
