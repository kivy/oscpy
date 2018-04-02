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
    sock = osc.listen(address='0.0.0.0', port=8000)
    osc.bind(sock, b'/address', callback)
    sleep(1000)
    osc.stop()
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
        osc.send(b'/ping', i)
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
