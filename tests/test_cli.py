from textwrap import dedent
from random import randint
from time import sleep
from oscpy.cli import init_parser, main, _send, __dump
from oscpy.client import send_message


class Mock(object):
    pass


def test_init_parser():
    parser = init_parser()


def test__send(capsys):
    options = Mock()
    options.repeat = 2
    options.host = 'localhost'
    options.port = 12345
    options.address = '/test'
    options.safer = False
    options.encoding = 'utf8'
    options.encoding_errors = 'strict'
    options.message = (1, 2, 3, 4, b"hello world")

    _send(options)
    captured = capsys.readouterr()
    out = captured.out
    assert out.startswith(dedent(
        '''
        Stats:
            calls: 2
            bytes: 88
            params: 10
            types:
        '''
    ).lstrip())
    assert ' i: 8' in out
    assert ' s: 2' in out


def test___dump(capsys):
    options = Mock()
    options.repeat = 2
    options.host = 'localhost'
    options.port = randint(60000, 65535)
    options.address = b'/test'
    options.safer = False
    options.encoding = None
    options.encoding_errors = 'strict'
    options.message = (1, 2, 3, 4, b"hello world")

    osc = __dump(options)
    out = capsys.readouterr().out
    assert out == ''

    send_message(
        options.address,
        options.message,
        options.host,
        options.port,
        safer=options.safer,
        encoding=options.encoding,
        encoding_errors=options.encoding_errors
    )

    sleep(0.1)
    out, err = capsys.readouterr()
    assert err == ''
    lines = out.split('\n')
    assert lines[0] == u"/test: 1, 2, 3, 4, hello world"

    osc.stop()
