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


usage:
------

Server (thread)
```python
    from oscpy import OSCThreadServer as OSC
    from time import sleep

    def callback(msg):
        print(
            "from={}, types={}, values={}".
            .format(msg.from, msg.types, msg.values)
        )

    osc = OSCThreadServer()
    osc.bind('/address', callback)
    osc.listen(address='0.0.0.0', port=8000)
    sleep(1000)
    osc.stop()
```

Server (async)
```python
    from oscpy import OSCThreadServer as OSC
    from time import sleep

    with OSCAsyncServer(port=8000) as OSC:
        for msg in OSC.listen():
           if msg.address == '/example':
                print("got {} on /example".format(msg.values))
           else:
                print("unsupported address {}".format(msg.address))
```

Client
```python

    from oscpy import OSCClient

    osc = OSCClient(address, port)
    for i in range(10):
        osc.send([i])
```

license
-------

MIT
