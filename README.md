### OSCPy

OSCPy is a Python implementation of Open Sound Control (OSC) network protocol.

OSCPy is managed by the [Kivy Team](https://kivy.org/about.html).

[![Backers on Open Collective](https://opencollective.com/kivy/backers/badge.svg)](https://opencollective.com/kivy)
[![Sponsors on Open Collective](https://opencollective.com/kivy/sponsors/badge.svg)](https://opencollective.com/kivy)
[![Contributor Covenant](https://img.shields.io/badge/Contributor%20Covenant-2.1-4baaaa.svg)](CODE_OF_CONDUCT.md)

![PyPI - Version](https://img.shields.io/pypi/v/oscpy)
![PyPI - Python Version](https://img.shields.io/pypi/pyversions/oscpy)

[![PR Tests](https://github.com/kivy/oscpy/actions/workflows/push.yml/badge.svg)](https://github.com/kivy/oscpy/actions/workflows/push.yml)
[![Coverage Status](https://coveralls.io/repos/github/kivy/oscpy/badge.svg?branch=master)](https://coveralls.io/github/kivy/oscpy?branch=master)

#### What is OSC?

[Open Sound Control](http://opensoundcontrol.org/) (OSC) is a 
[UDP](https://en.wikipedia.org/wiki/User_Datagram_Protocol)-based network
protocol that was designed for fast dispatching of time-sensitive messages.

As the name suggests, it was designed as a replacement for
[MIDI](https://en.wikipedia.org/wiki/MIDI), but applies well to other 
situations. The protocol is simple to use. OSC addresses look like HTTP URLs.
It accepts various basic types, such as string, float and int. 

You can think of it basically as an
[HTTP POST](https://en.wikipedia.org/wiki/POST_(HTTP)), with less overhead.

#### OSCPy Design Goals

- modern, pure Python implementation
- fast
- easy-to-use
- robust (returns meaningful errors in case of malformed messages,
  always do the right thing on correct messages, and by default intercept+log 
  the exceptions raised by callbacks)
- separation of concerns (message parsing vs communication)
- sync and async compatibility (threads, `asyncio`, `trio`)
- clean and easy-to-read code

#### Features

- serialize and parse OSC data types/Messages/Bundles
- a thread-based UDP server to open sockets (INET or UNIX)
- bind callbacks on OSC addresses
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

def callback(*values):
    print("got values: {}".format(values))

osc = OSCThreadServer()  # See sources for all the arguments

# You can also use an \*nix socket path here
sock = osc.listen(address='0.0.0.0', port=8000, default=True)
osc.bind(b'/address', callback)
sleep(1000)
osc.stop()  # Stop the default socket

osc.stop_all()  # Stop all sockets

# Here the server is still alive, one might call osc.listen() again

osc.terminate_server()  # Request the handler thread to stop looping

osc.join_server()  # Wait for the handler thread to finish pending tasks and exit
```

or you can use the decorator API.

Server (thread)

```python
from oscpy.server import OSCThreadServer
from time import sleep

osc = OSCThreadServer()
sock = osc.listen(address='0.0.0.0', port=8000, default=True)

@osc.address(b'/address')
def callback(*values):
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

address = "127.0.0.1"
port = 8000

osc = OSCClient(address, port)
for i in range(10):
    osc.send_message(b'/ping', [i])
```

#### Unicode

By default, the server and client take bytes (encoded strings), not unicode
strings, for OSC addresses as well as OSC strings. However, you can pass an
`encoding` parameter to have your strings automatically encoded and decoded by
them, so your callbacks will get unicode strings.

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

#### CLI

OSCPy provides an "oscli" utility to help with debugging:
- `oscli dump` to listen for messages and dump them
- `oscli send` to send messages or bundles to a server

See `oscli -h` for more information.

#### GOTCHAS

- `None` values are not allowed in serialization
- Unix-type sockets must not already exist when you `listen()` on them

#### TODO

- real support for timetag (currently only supports optionally
  dropping late bundles, not delaying those with timetags in the future)
- support for additional argument types
- an asyncio-oriented server implementation
- examples & documentation

## License

OSCPy is [MIT licensed](LICENSE), actively developed by a great
community and is supported by many projects managed by the 
[Kivy Organization](https://www.kivy.org/about.html).

## Support

Are you having trouble using OSCPy or any of its related projects
in the Kivy ecosystem?
Is there an error you don’t understand? Are you trying to figure out how to use 
it? We have volunteers who can help!

The best channels to contact us for support are listed in the latest 
[Contact Us](https://github.com/kivy/oscpy/blob/master/CONTACT.md)
document.

## Code of Conduct

In the interest of fostering an open and welcoming community, we as 
contributors and maintainers need to ensure participation in our project and 
our sister projects is a harassment-free and positive experience for everyone. 
It is vital that all interaction is conducted in a manner conveying respect, 
open-mindedness and gratitude.

Please consult the [latest Code of Conduct](https://github.com/kivy/oscpy/blob/master/CODE_OF_CONDUCT.md).

## Contributors

This project exists thanks to 
[all the people who contribute](https://github.com/kivy/oscpy/graphs/contributors).
[[Become a contributor](CONTRIBUTING.md)].

<img src="https://contrib.nn.ci/api?repo=kivy/oscpy&pages=5&no_bot=true&radius=22&cols=18">

## Backers

Thank you to [all of our backers](https://opencollective.com/kivy)! 
🙏 [[Become a backer](https://opencollective.com/kivy#backer)]

<img src="https://opencollective.com/kivy/backers.svg?width=890&avatarHeight=44&button=false">

## Sponsors

Special thanks to 
[all of our sponsors, past and present](https://opencollective.com/kivy).
Support this project by 
[[becoming a sponsor](https://opencollective.com/kivy#sponsor)].

Here are our top current sponsors. Please click through to see their websites,
and support them as they support us. 

<!--- See https://github.com/orgs/kivy/discussions/15 for explanation of this code. -->
<a href="https://opencollective.com/kivy/sponsor/0/website" target="_blank"><img src="https://opencollective.com/kivy/sponsor/0/avatar.svg"></a>
<a href="https://opencollective.com/kivy/sponsor/1/website" target="_blank"><img src="https://opencollective.com/kivy/sponsor/1/avatar.svg"></a>
<a href="https://opencollective.com/kivy/sponsor/2/website" target="_blank"><img src="https://opencollective.com/kivy/sponsor/2/avatar.svg"></a>
<a href="https://opencollective.com/kivy/sponsor/3/website" target="_blank"><img src="https://opencollective.com/kivy/sponsor/3/avatar.svg"></a>

<a href="https://opencollective.com/kivy/sponsor/4/website" target="_blank"><img src="https://opencollective.com/kivy/sponsor/4/avatar.svg"></a>
<a href="https://opencollective.com/kivy/sponsor/5/website" target="_blank"><img src="https://opencollective.com/kivy/sponsor/5/avatar.svg"></a>
<a href="https://opencollective.com/kivy/sponsor/6/website" target="_blank"><img src="https://opencollective.com/kivy/sponsor/6/avatar.svg"></a>
<a href="https://opencollective.com/kivy/sponsor/7/website" target="_blank"><img src="https://opencollective.com/kivy/sponsor/7/avatar.svg"></a>

<a href="https://opencollective.com/kivy/sponsor/8/website" target="_blank"><img src="https://opencollective.com/kivy/sponsor/8/avatar.svg"></a>
<a href="https://opencollective.com/kivy/sponsor/9/website" target="_blank"><img src="https://opencollective.com/kivy/sponsor/9/avatar.svg"></a>
<a href="https://opencollective.com/kivy/sponsor/10/website" target="_blank"><img src="https://opencollective.com/kivy/sponsor/10/avatar.svg"></a>
<a href="https://opencollective.com/kivy/sponsor/11/website" target="_blank"><img src="https://opencollective.com/kivy/sponsor/11/avatar.svg"></a>

<a href="https://opencollective.com/kivy/sponsor/12/website" target="_blank"><img src="https://opencollective.com/kivy/sponsor/12/avatar.svg"></a>
<a href="https://opencollective.com/kivy/sponsor/13/website" target="_blank"><img src="https://opencollective.com/kivy/sponsor/13/avatar.svg"></a>
<a href="https://opencollective.com/kivy/sponsor/14/website" target="_blank"><img src="https://opencollective.com/kivy/sponsor/14/avatar.svg"></a>
<a href="https://opencollective.com/kivy/sponsor/15/website" target="_blank"><img src="https://opencollective.com/kivy/sponsor/15/avatar.svg"></a>
