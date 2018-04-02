OSCPy
=====

/!\ This is very much a work in progress /!\

A modern implementation of OSC for python2/3.

Goals:
- python2.7/3.6+ compatibility (can be relaxed more on the python3 side if needed, but nothing before 2.7 will be supported)
- fast
- easy to use
- robust (returns meaningful errors in case of malformed messages, always do the right thing on correct messages)
- separation of concerns (message parsing vs communication)
- sync and async compatibility (threads, asyncio, trio…)
- clean and easy to read code

features:
- serialize and parse OSC data types/Messages/Bundles
- a thread based udp server to open sockets and bind callbacks on osc addresses on them
- a simple client


usage:
------

Server (thread)
```python
    from oscpy.server import OSCThreadServer as OSC
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
    from oscpy.server import OSCThreadServer as OSC
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
    from oscpy.server import OSCThreadServer as OSC
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
    from oscpy.server import OSCThreadServer as OSC

    with OSCAsyncServer(port=8000) as OSC:
        for address, values in OSC.listen():
           if address == b'/example':
                print("got {} on /example".format(values))
           else:
                print("unknown address {}".format(address))
```

Client
```python

    from oscpy import OSCClient

    osc = OSCClient(address, port)
    for i in range(10):
        osc.send_message(b'/ping', i)
```

TODO:
- address matching (outside of the currently supported *exact* matching)
- real support for timetag (currently only supports optionally dropping late bundles, not delaying those with timetags in the future)
- support for additional arguments types
- an asyncio-oriented server implementation
- performances assessment (profiling and comparison with other implementations)
- examples & documentation

license
-------

MIT
