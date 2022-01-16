# coding: utf8
import pytest
from time import time, sleep
from sys import platform, version_info
import socket
from tempfile import mktemp
from os.path import exists
from os import unlink
from threading import Event

from oscpy.server import OSCThreadServer, ServerClass
from oscpy.client import send_message, send_bundle, OSCClient
from oscpy import __version__

from utils import runner, _await, _callback

if version_info > (3, 5, 0):
    from oscpy.server.curio_server import OSCCurioServer
    from oscpy.server.trio_server import OSCTrioServer
    from oscpy.server.asyncio_server import OSCAsyncioServer
    server_classes = {
        OSCThreadServer,
        # OSCTrioServer,
        OSCAsyncioServer,
        OSCCurioServer,
    }
else:
    server_classes = [OSCThreadServer]


@pytest.mark.parametrize("cls", server_classes)
def test_instance(cls):
    cls()


@pytest.mark.parametrize("cls", server_classes)
def test_listen(cls):
    osc = cls()
    sock = osc.listen()
    runner(osc, timeout=1, socket=sock)


@pytest.mark.parametrize("cls", server_classes)
def test_getaddress(cls):
    osc = cls()
    sock = _await(osc.listen, osc)
    assert osc.getaddress(sock)[0] == '127.0.0.1'

    with pytest.raises(RuntimeError):
        osc.getaddress()

    sock2 = _await(osc.listen, osc, kwargs=dict(default=True))
    assert osc.getaddress(sock2)[0] == '127.0.0.1'
    runner(osc, timeout=1, socket=sock)


@pytest.mark.parametrize("cls", server_classes)
def test_listen_default(cls):
    osc = cls()
    sock = _await(osc.listen, osc, kwargs=dict(default=True))

    with pytest.raises(RuntimeError) as e_info:  # noqa
        # osc.listen(default=True)
        _await(osc.listen, osc, kwargs=dict(default=True))

    osc.close(sock)
    _await(osc.listen, osc, kwargs=dict(default=True))


@pytest.mark.parametrize("cls", server_classes)
def test_close(cls):
    osc = cls()
    _await(osc.listen, osc, kwargs=dict(default=True))

    osc.close()
    with pytest.raises(RuntimeError) as e_info:  # noqa
        osc.close()


@pytest.mark.skipif(platform == 'win32', reason="unix sockets not available on windows")
@pytest.mark.parametrize("cls", server_classes)
def test_close_unix(cls):
    osc = cls()
    filename = mktemp()
    # unix = osc.listen(address=filename, family='unix')
    unix = _await(osc.listen, osc, kwargs=dict(address=filename, family='unix'))
    assert exists(filename)
    osc.close(unix)
    assert not exists(filename)


@pytest.mark.parametrize("cls", server_classes - {OSCCurioServer})
def test_stop_unknown(cls):
    osc = cls()
    with pytest.raises(RuntimeError):
        _await(osc.stop, osc, args=[socket.socket()])


@pytest.mark.parametrize("cls", server_classes - {OSCCurioServer})
def test_stop_default(cls):
    osc = cls()
    _await(osc.listen, osc, kwargs=dict(default=True))
    assert len(osc.sockets) == 1
    osc.stop()
    assert len(osc.sockets) == 0


@pytest.mark.parametrize("cls", server_classes - {OSCCurioServer})
def test_stop_all(cls):
    osc = cls()
    sock = _await(osc.listen, osc, kwargs=dict(default=True))
    host, port = sock.getsockname()
    sock2 = _await(osc.listen, osc)
    assert len(osc.sockets) == 2
    osc.stop_all()
    assert len(osc.sockets) == 0
    sleep(.1)
    sock3 = _await(osc.listen, osc, kwargs=dict(default=True))
    assert len(osc.sockets) == 1
    osc.stop_all()


@pytest.mark.parametrize("cls", {OSCThreadServer})
def test_terminate_server(cls):
    osc = cls()
    assert not osc.join_server(timeout=0.1)
    assert osc._thread.is_alive()
    osc.terminate_server()
    assert osc.join_server(timeout=0.1)
    assert not osc._thread.is_alive()


@pytest.mark.parametrize("cls", server_classes)
def test_send_message_without_socket(cls):
    osc = cls()
    with pytest.raises(RuntimeError):
        osc.send_message(b'/test', [], 'localhost', 0)


@pytest.mark.parametrize("cls", server_classes)
def test_intercept_errors(caplog, cls):

    event = Event()

    def success(*values):
        event.set()

    def broken_callback(*values):
        raise ValueError("some bad value")

    osc = cls()
    sock = osc.listen()
    port = sock.getsockname()[1]
    osc.bind(b'/broken_callback', broken_callback, sock)
    osc.bind(b'/success', success, sock)
    send_message(b'/broken_callback', [b'test'], 'localhost', port)
    send_message(b'/success', [b'test'], 'localhost', port)
    runner(osc, timeout=.2)
    assert event.is_set()

    assert len(caplog.records) == 1, caplog.records
    record = caplog.records[0]
    assert record.msg == "Ignoring unhandled exception caught in oscpy server"
    assert not record.args
    assert record.exc_info

    osc = cls(intercept_errors=False)
    sock = osc.listen()
    port = sock.getsockname()[1]
    osc.bind(b'/broken_callback', broken_callback, sock)
    send_message(b'/broken_callback', [b'test'], 'localhost', port)
    runner(osc, timeout=.2)
    assert len(caplog.records) == 2, caplog.records  # Unchanged


@pytest.mark.parametrize("cls", server_classes)
def test_send_bundle_without_socket(cls):
    osc = cls()
    with pytest.raises(RuntimeError):
        osc.send_bundle([], 'localhost', 0)

    osc.listen(default=True)
    osc.send_bundle(
        (
            (b'/test', []),
        ),
        'localhost', 1
    )


@pytest.mark.parametrize("cls", server_classes)
def test_bind1(cls):
    osc = cls()
    sock = osc.listen(default=True)
    port = sock.getsockname()[1]
    event = Event()

    def success(*values):
        event.set()

    osc.bind(b'/success', success)

    send_message(b'/success', [b'test', 1, 1.12345], 'localhost', port)
    runner(osc, timeout=.2)
    assert event.is_set(), 'timeout while waiting for success message.'


@pytest.mark.parametrize("cls", server_classes)
def test_bind_get_address(cls):
    osc = cls()
    sock = osc.listen(default=True)
    port = sock.getsockname()[1]
    event = Event()

    def success(address, *values):
        assert address == b'/success'
        event.set()

    osc.bind(b'/success', success, sock, get_address=True)

    send_message(b'/success', [b'test', 1, 1.12345], 'localhost', port)

    runner(osc)
    assert event.wait(1), 'timeout while waiting for success message.'


@pytest.mark.parametrize("cls", server_classes)
def test_bind_get_address_smart(cls):
    osc = cls(advanced_matching=True)
    sock = osc.listen(default=True)
    port = sock.getsockname()[1]
    event = Event()

    def success(address, *values):
        assert address == b'/success/a'
        event.set()

    osc.bind(b'/success/?', success, sock, get_address=True)

    send_message(b'/success/a', [b'test', 1, 1.12345], 'localhost', port)
    runner(osc, timeout=1, socket=sock)
    assert event.wait(1), 'timeout while waiting for success message.'

@pytest.mark.parametrize("cls", server_classes)
def test_reuse_callback(cls):
    osc = cls()
    sock = osc.listen()
    port = sock.getsockname()[1]

    def success(*values):
        pass

    osc.bind(b'/success', success, sock)
    osc.bind(b'/success', success, sock)
    osc.bind(b'/success2', success, sock)
    assert len(osc.addresses.get((sock, b'/success'))) == 1
    assert len(osc.addresses.get((sock, b'/success2'))) == 1


@pytest.mark.parametrize("cls", server_classes)
def test_unbind(cls):
    osc = cls()
    sock = osc.listen()
    port = sock.getsockname()[1]
    event = Event()

    def failure(*values):
        event.set()

    osc.bind(b'/failure', failure, sock)
    with pytest.raises(RuntimeError) as e_info:  # noqa
        osc.unbind(b'/failure', failure)
    osc.unbind(b'/failure', failure, sock)

    send_message(b'/failure', [b'test', 1, 1.12345], 'localhost', port)

    assert not event.wait(1), "Unexpected call to failure()"


@pytest.mark.parametrize("cls", server_classes)
def test_unbind_default(cls):
    osc = cls()
    sock = osc.listen(default=True)
    port = sock.getsockname()[1]
    event = Event()

    def failure(*values):
        event.set()

    osc.bind(b'/failure', failure)
    osc.unbind(b'/failure', failure)

    send_message(b'/failure', [b'test', 1, 1.12345], 'localhost', port)

    assert not event.wait(1), "Unexpected call to failure()"


@pytest.mark.parametrize("cls", server_classes)
def test_bind_multi(cls):
    osc = cls()

    sock1 = osc.listen()
    port1 = sock1.getsockname()[1]
    event1 = Event()
    osc.bind(b'/success', _callback(osc, lambda *_: event1.set()), sock1)

    sock2 = osc.listen()
    port2 = sock2.getsockname()[1]
    event2 = Event()
    osc.bind(b'/success', _callback(osc, lambda *_: event2.set()), sock2)

    send_message(b'/success', [b'test', 1, 1.12345], 'localhost', port1)
    send_message(b'/success', [b'test', 1, 1.12345], 'localhost', port2)

    runner(osc, timeout=.1)
    assert (
        event2.is_set()
        and
        event1.is_set()
    ), 'timeout while waiting for success message.'


@pytest.mark.parametrize("cls", server_classes)
def test_bind_address(cls):
    osc = cls()
    osc.listen(default=True)
    result = []
    event = Event()

    @osc.address(b'/test')
    def success(*args):
        event.set()

    timeout = time() + 1

    send_message(b'/test', [], *osc.getaddress())

    runner(osc)
    assert event.wait(1), 'timeout while waiting for test message.'


@pytest.mark.parametrize("cls", server_classes)
def test_bind_address_class(cls):
    osc = cls()
    osc.listen(default=True)

    @ServerClass
    class Test(object):
        def __init__(self):
            self.event = Event()

        @osc.address_method(b'/test')
        def success(self, *args):
            self.event.set()

    test = Test()
    send_message(b'/test', [], *osc.getaddress())
    runner(osc)
    assert test.event.wait(1), 'timeout while waiting for test message.'


@pytest.mark.parametrize("cls", server_classes)
def test_bind_no_default(cls):
    osc = cls()

    def success(*values):
        pass

    with pytest.raises(RuntimeError) as e_info:  # noqa
        osc.bind(b'/success', success)


@pytest.mark.parametrize("cls", server_classes)
def test_bind_default(cls):
    osc = cls()
    osc.listen(default=True)
    port = osc.getaddress()[1]
    event = Event()

    def success(*values):
        event.set()

    osc.bind(b'/success', success)

    send_message(b'/success', [b'test', 1, 1.12345], 'localhost', port)

    runner(osc)
    assert event.wait(1), 'timeout while waiting for test message.'


@pytest.mark.parametrize("cls", server_classes)
def test_smart_address_match(cls):
    osc = cls(advanced_matching=True)

    address = osc.create_smart_address(b'/test?')
    assert osc._match_address(address, b'/testa')
    assert osc._match_address(address, b'/testi')
    assert not osc._match_address(address, b'/test')
    assert not osc._match_address(address, b'/testaa')
    assert not osc._match_address(address, b'/atast')

    address = osc.create_smart_address(b'/?test')
    assert osc._match_address(address, b'/atest')
    assert osc._match_address(address, b'/etest')
    assert not osc._match_address(address, b'/test')
    assert not osc._match_address(address, b'/testb')
    assert not osc._match_address(address, b'/atast')

    address = osc.create_smart_address(b'/*test')
    assert osc._match_address(address, b'/aaaatest')
    assert osc._match_address(address, b'/test')
    assert not osc._match_address(address, b'/tast')
    assert not osc._match_address(address, b'/testb')
    assert not osc._match_address(address, b'/atesta')

    address = osc.create_smart_address(b'/t[ea]st')
    assert osc._match_address(address, b'/test')
    assert osc._match_address(address, b'/tast')
    assert not osc._match_address(address, b'/atast')
    assert not osc._match_address(address, b'/tist')
    assert not osc._match_address(address, b'/testb')
    assert not osc._match_address(address, b'/atesta')

    address = osc.create_smart_address(b'/t[^ea]st')
    assert osc._match_address(address, b'/tist')
    assert osc._match_address(address, b'/tost')
    assert not osc._match_address(address, b'/tast')
    assert not osc._match_address(address, b'/test')
    assert not osc._match_address(address, b'/tostb')
    assert not osc._match_address(address, b'/atosta')

    address = osc.create_smart_address(b'/t[^ea]/st')
    assert osc._match_address(address, b'/ti/st')
    assert osc._match_address(address, b'/to/st')
    assert not osc._match_address(address, b'/tist')
    assert not osc._match_address(address, b'/tost')
    assert not osc._match_address(address, b'/to/stb')
    assert not osc._match_address(address, b'/ato/sta')

    address = osc.create_smart_address(b'/t[a-j]t')
    assert osc._match_address(address, b'/tit')
    assert osc._match_address(address, b'/tat')
    assert not osc._match_address(address, b'/tot')
    assert not osc._match_address(address, b'/tiit')
    assert not osc._match_address(address, b'/tost')

    address = osc.create_smart_address(b'/test/*/stuff')
    assert osc._match_address(address, b'/test/blah/stuff')
    assert osc._match_address(address, b'/test//stuff')
    assert not osc._match_address(address, b'/teststuff')
    assert not osc._match_address(address, b'/test/stuffstuff')
    assert not osc._match_address(address, b'/testtest/stuff')

    address = osc.create_smart_address(b'/test/{str1,str2}/stuff')
    assert osc._match_address(address, b'/test/str1/stuff')
    assert osc._match_address(address, b'/test/str2/stuff')
    assert not osc._match_address(address, b'/test//stuff')
    assert not osc._match_address(address, b'/test/stuffstuff')
    assert not osc._match_address(address, b'/testtest/stuff')


@pytest.mark.parametrize("cls", server_classes)
def test_smart_address_cache(cls):
    osc = cls(advanced_matching=True)
    assert osc.create_smart_address(b'/a') == osc.create_smart_address(b'/a')


@pytest.mark.parametrize("cls", server_classes)
def test_advanced_matching(cls):
    osc = cls(advanced_matching=True)
    osc.listen(default=True)
    port = osc.getaddress()[1]
    result = {}
    event = Event()

    def save_result(f):
        name = f.__name__

        def wrapped(*args):
            r = result.get(name, [])
            r.append(args)
            result[name] = r
            return f(*args)
        return wrapped

    @osc.address(b'/?')
    @save_result
    def singlechar(*values):
        pass

    @osc.address(b'/??')
    @save_result
    def twochars(*values):
        pass

    @osc.address(b'/prefix*')
    @save_result
    def prefix(*values):
        pass

    @osc.address(b'/*suffix')
    @save_result
    def suffix(*values):
        pass

    @osc.address(b'/[abcd]')
    @save_result
    def somechars(*values):
        pass

    @osc.address(b'/{string1,string2}')
    @save_result
    def somestrings(*values):
        pass

    @osc.address(b'/part1/part2')
    @save_result
    def parts(*values):
        pass

    @osc.address(b'/part1/*/part3')
    @save_result
    def parts_star(*values):
        pass

    @osc.address(b'/part1/part2/?')
    @save_result
    def parts_prefix(*values):
        pass

    @osc.address(b'/part1/[abcd]/part3')
    @save_result
    def parts_somechars(*values):
        pass

    @osc.address(b'/part1/[c-f]/part3')
    @save_result
    def parts_somecharsrange(*values):
        pass

    @osc.address(b'/part1/[!abcd]/part3')
    @save_result
    def parts_notsomechars(*values):
        pass

    @osc.address(b'/part1/[!c-f]/part3')
    @save_result
    def parts_notsomecharsrange(*values):
        pass

    @osc.address(b'/part1/{string1,string2}/part3')
    @save_result
    def parts_somestrings(*values):
        pass

    @osc.address(b'/part1/part2/{string1,string2}')
    @save_result
    def parts_somestrings2(*values):
        pass

    @osc.address(b'/part1/part2/prefix-{string1,string2}')
    @save_result
    def parts_somestrings3(*values):
        pass

    @osc.address(b'/done')
    def done(*values):
        event.set()

    send_bundle(
        (
            (b'/a', [1]),
            (b'/b', [2]),
            (b'/z', [3]),
            (b'/1', [3]),
            (b'/?', [4]),

            (b'/ab', [5]),
            (b'/bb', [6]),
            (b'/z?', [7]),
            (b'/??', [8]),
            (b'/?*', [9]),

            (b'/prefixab', [10]),
            (b'/prefixbb', [11]),
            (b'/prefixz?', [12]),
            (b'/prefix??', [13]),
            (b'/prefix?*', [14]),

            (b'/absuffix', [15]),
            (b'/bbsuffix', [16]),
            (b'/z?suffix', [17]),
            (b'/??suffix', [18]),
            (b'/?*suffix', [19]),

            (b'/string1', [20]),
            (b'/string2', [21]),
            (b'/string1aa', [22]),
            (b'/string1b', [23]),
            (b'/string1?', [24]),
            (b'/astring1?', [25]),

            (b'/part1', [26]),
            (b'/part1/part', [27]),
            (b'/part1/part2', [28]),
            (b'/part1/part3/part2', [29]),
            (b'/part1/part2/part3', [30]),
            (b'/part1/part?/part2', [31]),

            (b'/part1', [32]),
            (b'/part1/a/part', [33]),
            (b'/part1/b/part2', [34]),
            (b'/part1/c/part3/part2', [35]),
            (b'/part1/d/part2/part3', [36]),
            (b'/part1/e/part?/part2', [37]),

            (b'/part1/test/part2', [38]),
            (b'/part1/a/part2', [39]),
            (b'/part1/b/part2', [40]),
            (b'/part1/c/part2/part2', [41]),
            (b'/part1/d/part2/part3', [42]),
            (b'/part1/0/part2', [43]),

            (b'/part1/string1/part', [45]),
            (b'/part1/string2/part3', [46]),
            (b'/part1/part2/string1', [47]),
            (b'/part1/part2/string2', [48]),
            (b'/part1/part2/prefix-string1', [49]),
            (b'/part1/part2/sprefix-tring2', [50]),
            (b'/done', []),
        ),
        'localhost', port
    )

    expected = {
        'singlechar': [(1,), (2,), (3,), (3,), (4,)],
        'twochars': [(5,), (6,), (7,), (8,), (9,)],
        'prefix': [(10,), (11,), (12,), (13,), (14,)],
        'suffix': [(15,), (16,), (17,), (18,), (19,)],
        'somechars': [(1,), (2,)],
        'somestrings': [(20,), (21,)], 'parts': [(28,)],
        'parts_star': [(30,), (46,)],
        'parts_somestrings': [(46,)],
        'parts_somestrings2': [(47,), (48,)],
        'parts_somestrings3': [(49,)]
    }

    runner(osc, timeout=.1)
    assert event.wait(1), 'timeout while waiting for test message.'
    assert result == expected


@pytest.mark.parametrize("cls", server_classes)
def test_decorator(cls):
    osc = cls()
    sock = osc.listen(default=True)
    port = sock.getsockname()[1]
    event1 = Event()
    event2 = Event()

    @osc.address(b'/test1', sock)
    def test1(*values):
        event1.set()

    @osc.address(b'/test2')
    def test2(*values):
        event2.set()

    send_message(b'/test1', [], 'localhost', port)
    send_message(b'/test2', [], 'localhost', port)

    runner(osc)
    assert event1.wait(1) and event2.is_set(), "timeout waiting for test messages"


@pytest.mark.parametrize("cls", {OSCThreadServer})
def test_answer(cls):
    event = Event()

    osc_1 = cls(intercept_errors=False)
    osc_1.listen(default=True)

    @osc_1.address(b'/ping')
    def ping(*values):
        if True in values:
            osc_1.answer(b'/zap', [True], port=osc_3.getaddress()[1])
        else:
            osc_1.answer(
                bundle=[
                    (b'/pong', [])
                ]
            )

    osc_2 = OSCThreadServer(intercept_errors=False)
    osc_2.listen(default=True)

    @osc_2.address(b'/pong')
    def pong(*values):
        osc_2.answer(b'/ping', [True])

    osc_3 = OSCThreadServer(intercept_errors=False)
    osc_3.listen(default=True)

    @osc_3.address(b'/zap')
    def zap(*values):
        if True in values:
            event.set()

    osc_2.send_message(b'/ping', [], *osc_1.getaddress())

    runner(osc_1)
    runner(osc_2)
    runner(osc_3)
    with pytest.raises(RuntimeError) as e_info:  # noqa
        osc_1.answer(b'/bing', [])

    assert event.wait(1), 'timeout while waiting for test message.'


@pytest.mark.parametrize("cls", server_classes)
def test_socket_family(cls):
    osc = cls()
    assert osc.listen().family == socket.AF_INET
    filename = mktemp()
    if platform != 'win32':
        assert osc.listen(address=filename, family='unix').family == socket.AF_UNIX  # noqa

    else:
        with pytest.raises(AttributeError) as e_info:
            osc.listen(address=filename, family='unix')

    if exists(filename):
        unlink(filename)

    with pytest.raises(ValueError) as e_info:  # noqa
        osc.listen(family='')


@pytest.mark.parametrize("cls", server_classes)
def test_encoding_send(cls):
    osc = cls()
    osc.listen(default=True)

    values = []
    event = Event()

    @osc.address(b'/encoded')
    def encoded(*val):
        for v in val:
            assert isinstance(v, bytes)
        values.append(val)
        event.set()

    send_message(
        u'/encoded',
        ['hello world', u'ééééé ààààà'],
        *osc.getaddress(), encoding='utf8')

    runner(osc)
    assert event.wait(1), 'timeout while waiting for test message.'


@pytest.mark.parametrize("cls", server_classes)
def test_encoding_receive(cls):
    osc = cls(encoding='utf8')
    osc.listen(default=True)

    values = []
    event = Event()

    @osc.address(u'/encoded')
    def encoded(*val):
        for v in val:
            assert not isinstance(v, bytes)
        values.append(val)
        event.set()

    send_message(
        b'/encoded',
        [
            b'hello world',
            u'ééééé ààààà'.encode('utf8')
        ],
        *osc.getaddress())

    runner(osc)
    assert event.wait(1), 'timeout while waiting for test message.'


@pytest.mark.parametrize("cls", server_classes)
def test_encoding_send_receive(cls):
    osc = cls(encoding='utf8')
    osc.listen(default=True)
    event = Event()

    values = []

    @osc.address(u'/encoded')
    def encoded(*val):
        for v in val:
            assert not isinstance(v, bytes)
        values.append(val)
        event.set()

    send_message(
        u'/encoded',
        ['hello world', u'ééééé ààààà'],
        *osc.getaddress(), encoding='utf8')

    runner(osc)
    assert event.wait(1), 'timeout while waiting for test message.'


@pytest.mark.parametrize("cls", server_classes)
def test_default_handler(cls):
    results = []
    event = Event()

    def test(address, *values):
        results.append((address, values))
        event.set()

    osc = cls(default_handler=test)
    osc.listen(default=True)

    @osc.address(b'/passthrough')
    def passthrough(*values):
        pass

    send_bundle(
        (
            (b'/test', []),
            (b'/passthrough', []),
            (b'/test/2', [1, 2, 3]),
        ),
        *osc.getaddress()
    )

    runner(osc)
    assert event.wait(2), 'timeout while waiting for test message.'

    expected = (
        (b'/test', tuple()),
        (b'/test/2', (1, 2, 3)),
    )

    for e, r in zip(expected, results):
        assert e == r


@pytest.mark.parametrize("cls", {OSCThreadServer})
def test_get_version(cls):
    osc = cls(encoding='utf8')
    osc.listen(default=True)

    values = []

    @osc.address(u'/_oscpy/version/answer')
    def cb(val):
        values.append(val)

    send_message(
        b'/_oscpy/version',
        [
            osc.getaddress()[1]
        ],
        *osc.getaddress(),
        encoding='utf8',
        encoding_errors='strict'
    )

    runner(osc)
    assert __version__ in values


@pytest.mark.parametrize("cls", {OSCThreadServer})
def test_get_routes(cls):
    osc = cls(encoding='utf8')
    osc.listen(default=True)

    event = Event()
    values = []

    @osc.address(u'/test_route')
    def dummy(*val):
        pass

    @osc.address(u'/_oscpy/routes/answer')
    def cb(*routes):
        values.extend(routes)
        event.set()

    send_message(
        b'/_oscpy/routes',
        [
            osc.getaddress()[1]
        ],
        *osc.getaddress(),
        encoding='utf8',
        encoding_errors='strict'
    )

    runner(osc)
    assert event.wait(1)
    assert u'/test_route' in values


@pytest.mark.parametrize("cls", server_classes)
def test_get_sender(cls):
    osc = cls(encoding='utf8')
    osc.listen(default=True)
    event = Event()

    @osc.address(u'/test_route')
    def callback(*val):
        osc.get_sender()
        event.set()

    with pytest.raises(RuntimeError,
                       match=r'get_sender\(\) not called from a callback'):
        osc.get_sender()

    send_message(
        u'/test_route',
        [osc.getaddress()[1]],
        *osc.getaddress(),
        encoding='utf8'
    )

    runner(osc)
    assert event.wait(2), 'timeout while waiting for test message.'


@pytest.mark.parametrize("cls", server_classes)
def test_server_different_port(cls):
    # used for storing values received by callback_3000
    checklist = [Event(), Event()]

    def callback(index):
        checklist[index].set()

    # server, will be tested:
    osc = cls(encoding='utf8')
    sock = osc.listen(address='0.0.0.0', default=True)
    port = sock.getsockname()[1]
    osc.bind('/callback', callback)

    # clients sending to different ports, used to test the osc:
    client = OSCClient(address='localhost', port=port, encoding='utf8')

    # osc.send_message(b'/callback', [0], ip_address='localhost', port=port)
    client.send_message('/callback', [0])

    # sever sends message on different port, might crash the server on windows:
    osc.send_message('/callback', ["nobody is going to receive this"], ip_address='localhost', port=port + 1)

    # client sends message to server again. if server is dead, message
    # will not be received:
    client.send_message('/callback', [1])

    # if 'c' is missing in the received checklist, the server thread
    # crashed and could not recieve the last message from the client:
    runner(osc, timeout=0.1)
    assert all(event.wait(1) for event in checklist)

    # osc.stop()  # clean up
