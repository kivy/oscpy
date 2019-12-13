# coding: utf8
import pytest
from time import time, sleep
from sys import platform
import socket
from tempfile import mktemp
from os.path import exists
from os import unlink

from oscpy.server import OSCThreadServer, ServerClass
from oscpy.client import send_message, send_bundle, OSCClient
from oscpy import __version__


def test_instance():
    OSCThreadServer()


def test_listen():
    osc = OSCThreadServer()
    sock = osc.listen()
    osc.stop(sock)


def test_getaddress():
    osc = OSCThreadServer()
    sock = osc.listen()
    assert osc.getaddress(sock)[0] == '127.0.0.1'

    with pytest.raises(RuntimeError):
        osc.getaddress()

    sock2 = osc.listen(default=True)
    assert osc.getaddress(sock2)[0] == '127.0.0.1'
    osc.stop(sock)


def test_listen_default():
    osc = OSCThreadServer()
    sock = osc.listen(default=True)

    with pytest.raises(RuntimeError) as e_info:  # noqa
        osc.listen(default=True)

    osc.close(sock)
    osc.listen(default=True)


def test_close():
    osc = OSCThreadServer()
    osc.listen(default=True)

    osc.close()
    with pytest.raises(RuntimeError) as e_info:  # noqa
        osc.close()

    if platform != 'win32':
        filename = mktemp()
        unix = osc.listen(address=filename, family='unix')
        assert exists(filename)
        osc.close(unix)
        assert not exists(filename)


def test_stop_unknown():
    osc = OSCThreadServer()
    with pytest.raises(RuntimeError):
        osc.stop(socket.socket())


def test_stop_default():
    osc = OSCThreadServer()
    osc.listen(default=True)
    assert len(osc.sockets) == 1
    osc.stop()
    assert len(osc.sockets) == 0


def test_stop_all():
    osc = OSCThreadServer()
    sock = osc.listen(default=True)
    host, port = sock.getsockname()
    osc.listen()
    assert len(osc.sockets) == 2
    osc.stop_all()
    assert len(osc.sockets) == 0
    sleep(.1)
    osc.listen(address=host, port=port)
    assert len(osc.sockets) == 1
    osc.stop_all()


def test_terminate_server():
    osc = OSCThreadServer()
    assert not osc.join_server(timeout=0.1)
    assert osc._thread.is_alive()
    osc.terminate_server()
    assert osc.join_server(timeout=0.1)
    assert not osc._thread.is_alive()


def test_send_message_without_socket():
    osc = OSCThreadServer()
    with pytest.raises(RuntimeError):
        osc.send_message(b'/test', [], 'localhost', 0)


def test_intercept_errors(caplog):

    cont = []

    def success(*values):
        cont.append(True)

    def broken_callback(*values):
        raise ValueError("some bad value")

    osc = OSCThreadServer()
    sock = osc.listen()
    port = sock.getsockname()[1]
    osc.bind(b'/broken_callback', broken_callback, sock)
    osc.bind(b'/success', success, sock)
    send_message(b'/broken_callback', [b'test'], 'localhost', port)
    sleep(0.01)
    send_message(b'/success', [b'test'], 'localhost', port)
    assert not osc.join_server(timeout=0.02)  # Thread not stopped
    assert cont == [True]

    assert len(caplog.records) == 1, caplog.records
    record = caplog.records[0]
    assert record.msg == "Unhandled exception caught in oscpy server"
    assert not record.args
    assert record.exc_info

    osc = OSCThreadServer(intercept_errors=False)
    sock = osc.listen()
    port = sock.getsockname()[1]
    osc.bind(b'/broken_callback', broken_callback, sock)
    send_message(b'/broken_callback', [b'test'], 'localhost', port)
    assert osc.join_server(timeout=0.02)  # Thread properly sets termination event on crash

    assert len(caplog.records) == 1, caplog.records  # Unchanged


def test_send_bundle_without_socket():
    osc = OSCThreadServer()
    with pytest.raises(RuntimeError):
        osc.send_bundle([], 'localhost', 0)

    osc.listen(default=True)
    osc.send_bundle(
        (
            (b'/test', []),
        ),
        'localhost', 1
    )


def test_bind():
    osc = OSCThreadServer()
    sock = osc.listen()
    port = sock.getsockname()[1]
    cont = []

    def success(*values):
        cont.append(True)

    osc.bind(b'/success', success, sock)

    send_message(b'/success', [b'test', 1, 1.12345], 'localhost', port)

    timeout = time() + 5
    while not cont:
        if time() > timeout:
            raise OSError('timeout while waiting for success message.')


def test_bind_get_address():
    osc = OSCThreadServer()
    sock = osc.listen()
    port = sock.getsockname()[1]
    cont = []

    def success(address, *values):
        assert address == b'/success'
        cont.append(True)

    osc.bind(b'/success', success, sock, get_address=True)

    send_message(b'/success', [b'test', 1, 1.12345], 'localhost', port)

    timeout = time() + 5
    while not cont:
        if time() > timeout:
            raise OSError('timeout while waiting for success message.')


def test_bind_get_address_smart():
    osc = OSCThreadServer(advanced_matching=True)
    sock = osc.listen()
    port = sock.getsockname()[1]
    cont = []

    def success(address, *values):
        assert address == b'/success/a'
        cont.append(True)

    osc.bind(b'/success/?', success, sock, get_address=True)

    send_message(b'/success/a', [b'test', 1, 1.12345], 'localhost', port)

    timeout = time() + 5
    while not cont:
        if time() > timeout:
            raise OSError('timeout while waiting for success message.')


def test_reuse_callback():
    osc = OSCThreadServer()
    sock = osc.listen()
    port = sock.getsockname()[1]
    cont = []

    def success(*values):
        cont.append(True)

    osc.bind(b'/success', success, sock)
    osc.bind(b'/success', success, sock)
    osc.bind(b'/success2', success, sock)
    assert len(osc.addresses.get((sock, b'/success'))) == 1
    assert len(osc.addresses.get((sock, b'/success2'))) == 1


def test_unbind():
    osc = OSCThreadServer()
    sock = osc.listen()
    port = sock.getsockname()[1]
    cont = []

    def failure(*values):
        cont.append(True)

    osc.bind(b'/failure', failure, sock)
    with pytest.raises(RuntimeError) as e_info:  # noqa
        osc.unbind(b'/failure', failure)
    osc.unbind(b'/failure', failure, sock)

    send_message(b'/failure', [b'test', 1, 1.12345], 'localhost', port)

    timeout = time() + 1
    while time() > timeout:
        assert not cont
        sleep(10e-9)


def test_unbind_default():
    osc = OSCThreadServer()
    sock = osc.listen(default=True)
    port = sock.getsockname()[1]
    cont = []

    def failure(*values):
        cont.append(True)

    osc.bind(b'/failure', failure)
    osc.unbind(b'/failure', failure)

    send_message(b'/failure', [b'test', 1, 1.12345], 'localhost', port)

    timeout = time() + 1
    while time() > timeout:
        assert not cont
        sleep(10e-9)


def test_bind_multi():
    osc = OSCThreadServer()
    sock1 = osc.listen()
    port1 = sock1.getsockname()[1]

    sock2 = osc.listen()
    port2 = sock2.getsockname()[1]
    cont = []

    def success1(*values):
        cont.append(True)

    def success2(*values):
        cont.append(False)

    osc.bind(b'/success', success1, sock1)
    osc.bind(b'/success', success2, sock2)

    send_message(b'/success', [b'test', 1, 1.12345], 'localhost', port1)
    send_message(b'/success', [b'test', 1, 1.12345], 'localhost', port2)

    timeout = time() + 5
    while len(cont) < 2:
        if time() > timeout:
            raise OSError('timeout while waiting for success message.')

    assert True in cont and False in cont


def test_bind_address():
    osc = OSCThreadServer()
    osc.listen(default=True)
    result = []

    @osc.address(b'/test')
    def success(*args):
        result.append(True)

    timeout = time() + 1

    send_message(b'/test', [], *osc.getaddress())

    while len(result) < 1:
        if time() > timeout:
            raise OSError('timeout while waiting for success message.')
        sleep(10e-9)

    assert True in result


def test_bind_address_class():
    osc = OSCThreadServer()
    osc.listen(default=True)

    @ServerClass
    class Test(object):
        def __init__(self):
            self.result = []

        @osc.address_method(b'/test')
        def success(self, *args):
            self.result.append(True)

    timeout = time() + 1

    test = Test()
    send_message(b'/test', [], *osc.getaddress())

    while len(test.result) < 1:
        if time() > timeout:
            raise OSError('timeout while waiting for success message.')
        sleep(10e-9)

    assert True in test.result


def test_bind_no_default():
    osc = OSCThreadServer()

    def success(*values):
        pass

    with pytest.raises(RuntimeError) as e_info:  # noqa
        osc.bind(b'/success', success)


def test_bind_default():
    osc = OSCThreadServer()
    osc.listen(default=True)
    port = osc.getaddress()[1]
    cont = []

    def success(*values):
        cont.append(True)

    osc.bind(b'/success', success)

    send_message(b'/success', [b'test', 1, 1.12345], 'localhost', port)

    timeout = time() + 5
    while not cont:
        if time() > timeout:
            raise OSError('timeout while waiting for success message.')


def test_smart_address_match():
    osc = OSCThreadServer(advanced_matching=True)

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


def test_smart_address_cache():
    osc = OSCThreadServer(advanced_matching=True)
    assert osc.create_smart_address(b'/a') == osc.create_smart_address(b'/a')


def test_advanced_matching():
    osc = OSCThreadServer(advanced_matching=True)
    osc.listen(default=True)
    port = osc.getaddress()[1]
    result = {}

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

    timeout = time() + 5
    while result != expected:
        if time() > timeout:
            print("expected: {}\n result: {}\n".format(expected, result))
            raise OSError('timeout while waiting for expected result.')
        sleep(10e-9)


def test_decorator():
    osc = OSCThreadServer()
    sock = osc.listen(default=True)
    port = sock.getsockname()[1]
    cont = []

    @osc.address(b'/test1', sock)
    def test1(*values):
        print("test1 called")
        cont.append(True)

    @osc.address(b'/test2')
    def test2(*values):
        print("test1 called")
        cont.append(True)

    send_message(b'/test1', [], 'localhost', port)
    send_message(b'/test2', [], 'localhost', port)

    timeout = time() + 1
    while len(cont) < 2:
        if time() > timeout:
            raise OSError('timeout while waiting for success message.')


def test_answer():
    cont = []

    osc_1 = OSCThreadServer()
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

    osc_2 = OSCThreadServer()
    osc_2.listen(default=True)

    @osc_2.address(b'/pong')
    def pong(*values):
        osc_2.answer(b'/ping', [True])

    osc_3 = OSCThreadServer()
    osc_3.listen(default=True)

    @osc_3.address(b'/zap')
    def zap(*values):
        if True in values:
            cont.append(True)

    osc_2.send_message(b'/ping', [], *osc_1.getaddress())

    with pytest.raises(RuntimeError) as e_info:  # noqa
        osc_1.answer(b'/bing', [])

    timeout = time() + 2
    while not cont:
        if time() > timeout:
            raise OSError('timeout while waiting for success message.')
        sleep(10e-9)


def test_socket_family():
    osc = OSCThreadServer()
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


def test_encoding_send():
    osc = OSCThreadServer()
    osc.listen(default=True)

    values = []

    @osc.address(b'/encoded')
    def encoded(*val):
        for v in val:
            assert isinstance(v, bytes)
        values.append(val)

    send_message(
        u'/encoded',
        ['hello world', u'ééééé ààààà'],
        *osc.getaddress(), encoding='utf8')

    timeout = time() + 2
    while not values:
        if time() > timeout:
            raise OSError('timeout while waiting for success message.')
        sleep(10e-9)


def test_encoding_receive():
    osc = OSCThreadServer(encoding='utf8')
    osc.listen(default=True)

    values = []

    @osc.address(u'/encoded')
    def encoded(*val):
        for v in val:
            assert not isinstance(v, bytes)
        values.append(val)

    send_message(
        b'/encoded',
        [
            b'hello world',
            u'ééééé ààààà'.encode('utf8')
        ],
        *osc.getaddress())

    timeout = time() + 2
    while not values:
        if time() > timeout:
            raise OSError('timeout while waiting for success message.')
        sleep(10e-9)


def test_encoding_send_receive():
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
        ['hello world', u'ééééé ààààà'],
        *osc.getaddress(), encoding='utf8')

    timeout = time() + 2
    while not values:
        if time() > timeout:
            raise OSError('timeout while waiting for success message.')
        sleep(10e-9)


def test_default_handler():
    results = []

    def test(address, *values):
        results.append((address, values))

    osc = OSCThreadServer(default_handler=test)
    osc.listen(default=True)

    @osc.address(b'/passthrough')
    def passthrough(*values):
        pass

    osc.send_bundle(
        (
            (b'/test', []),
            (b'/passthrough', []),
            (b'/test/2', [1, 2, 3]),
        ),
        *osc.getaddress()
    )

    timeout = time() + 2
    while len(results) < 2:
        if time() > timeout:
            raise OSError('timeout while waiting for success message.')
        sleep(10e-9)

    expected = (
        (b'/test', tuple()),
        (b'/test/2', (1, 2, 3)),
    )

    for e, r in zip(expected, results):
        assert e == r


def test_get_version():
    osc = OSCThreadServer(encoding='utf8')
    osc.listen(default=True)

    values = []

    @osc.address(u'/_oscpy/version/answer')
    def cb(val):
        print(val)
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

    timeout = time() + 2
    while not values:
        if time() > timeout:
            raise OSError('timeout while waiting for success message.')
        sleep(10e-9)

    assert __version__ in values


def test_get_routes():
    osc = OSCThreadServer(encoding='utf8')
    osc.listen(default=True)

    values = []

    @osc.address(u'/test_route')
    def dummy(*val):
        pass

    @osc.address(u'/_oscpy/routes/answer')
    def cb(*routes):
        values.extend(routes)

    send_message(
        b'/_oscpy/routes',
        [
            osc.getaddress()[1]
        ],
        *osc.getaddress(),
        encoding='utf8',
        encoding_errors='strict'
    )

    timeout = time() + 2
    while not values:
        if time() > timeout:
            raise OSError('timeout while waiting for success message.')
        sleep(10e-9)

    assert u'/test_route' in values


def test_get_sender():
    osc = OSCThreadServer(encoding='utf8')
    osc.listen(default=True)

    values = []

    @osc.address(u'/test_route')
    def callback(*val):
        values.append(osc.get_sender())

    with pytest.raises(RuntimeError,
                       match='get_sender\(\) not called from a callback'):
        osc.get_sender()

    send_message(
        b'/test_route',
        [
            osc.getaddress()[1]
        ],
        *osc.getaddress(),
        encoding='utf8'
    )

    timeout = time() + 2
    while not values:
        if time() > timeout:
            raise OSError('timeout while waiting for success message.')
        sleep(10e-9)


def test_server_different_port():
    # used for storing values received by callback_3000
    checklist = []

    def callback_3000(*values):
        checklist.append(values[0])

    # server, will be tested:
    server_3000 = OSCThreadServer(encoding='utf8')
    sock_3000 = server_3000.listen(address='0.0.0.0', port=3000, default=True)
    server_3000.bind(b'/callback_3000', callback_3000)

    # clients sending to different ports, used to test the server:
    client_3000 = OSCClient(address='localhost', port=3000, encoding='utf8')

    # server sends message to himself, should work:
    server_3000.send_message(
        b'/callback_3000',
        ["a"],
        ip_address='localhost',
        port=3000
    )
    sleep(0.05)

    # client sends message to server, will be received properly:
    client_3000.send_message(b'/callback_3000', ["b"])
    sleep(0.05)

    # sever sends message on different port, might crash the server on windows:
    server_3000.send_message(
        b'/callback_3000',
        ["nobody is going to receive this"],
        ip_address='localhost',
        port=3001
    )
    sleep(0.05)

    # client sends message to server again. if server is dead, message
    # will not be received:
    client_3000.send_message(b'/callback_3000', ["c"])
    sleep(0.1)

    # if 'c' is missing in the received checklist, the server thread
    # crashed and could not recieve the last message from the client:
    assert checklist == ['a', 'b', 'c']

    server_3000.stop()	# clean up
