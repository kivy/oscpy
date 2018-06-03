from oscpy.parser import (
    parse, padded, read_message, read_bundle, format_message,
    format_bundle, timetag_to_time, time_to_timetag
)
from pytest import approx, raises
from time import time
import struct

# example messages from
# http://opensoundcontrol.org/spec-1_0-examples#argument

message_1 = (
    (b'/oscillator/4/frequency', [440.0]),
    [
        0x2f, 0x6f, 0x73, 0x63,
        0x69, 0x6c, 0x6c, 0x61,
        0x74, 0x6f, 0x72, 0x2f,
        0x34, 0x2f, 0x66, 0x72,
        0x65, 0x71, 0x75, 0x65,
        0x6e, 0x63, 0x79, 0x0,
        0x2c, 0x66, 0x0,  0x0,
        0x43, 0xdc, 0x0,  0x0,
    ],
    (b'/oscillator/4/frequency', [approx(440.0)]),
)

message_2 = (
    (b'/foo', [1000, -1, b'hello', 1.234, 5.678]),
    [
        0x2f, 0x66, 0x6f, 0x6f,
        0x0,  0x0,  0x0,  0x0,
        0x2c, 0x69, 0x69, 0x73,
        0x66, 0x66, 0x0,  0x0,
        0x0,  0x0,  0x3,  0xe8,
        0xff, 0xff, 0xff, 0xff,
        0x68, 0x65, 0x6c, 0x6c,
        0x6f, 0x0,  0x0,  0x0,
        0x3f, 0x9d, 0xf3, 0xb6,
        0x40, 0xb5, 0xb2, 0x2d,
    ],
    (b'/foo', [1000, -1, b'hello', approx(1.234), approx(5.678)]),
)


def test_parse_int():
    assert parse(b'i', struct.pack('>i', 1))[0] == 1


def test_parse_float():
    assert parse(b'f', struct.pack('>f', 1.5))[0] == 1.5


def test_padd_string():
    for i in range(8):
        length = padded(i)
        assert length % 4 == 0
        assert length >= i


def test_parse_string():
    assert parse(b's', struct.pack('%is' % padded(len('t')), b't'))[0] == b't'
    s = b'test'
    # XXX should we need to add the null byte ourselves?
    assert parse(
        b's', struct.pack('%is' % padded(len(s) + 1), s + b'\0')
    )[0] == s


def test_parse_blob():
    length = 10
    data = tuple(range(length))
    pad = padded(length, 8)
    fmt = '>i%iQ' % pad
    s = struct.pack(fmt, length, *(data + (pad - length) * (0, )))
    result = parse(b'b', s)[0]
    assert result == data


def test_parse_unknown():
    with raises(ValueError):
        parse(b'H', struct.pack('>f', 1.5))


def test_read_message():
    source, msg, result = message_1
    msg = struct.pack('>%iB' % len(msg), *msg)
    address, tags, values, size = read_message(msg)
    assert address == result[0]
    assert values == result[1]

    source, msg, result = message_2
    msg = struct.pack('>%iB' % len(msg), *msg)
    address, tags, values, size = read_message(msg)
    assert address == result[0]
    assert tags == b'iisff'
    assert values == result[1]


def test_read_message_wrong_address():
    msg = format_message(b'test', [])
    with raises(ValueError) as e:
        address, tags, values, size = read_message(msg)

    assert "doesn't start with a '/'" in str(e)


def test_read_bundle():
    pad = padded(len('#bundle'))
    data = struct.pack('>%isQ' % pad, b'#bundle', 1)

    tests = (
        message_1,
        message_2,
        message_1,
        message_2,
    )

    for source, msg, result in tests:
        msg = struct.pack('>%iB' % len(msg), *msg)
        assert read_message(msg)[::2] == result
        data += struct.pack('>i', len(msg)) + msg

    timetag, messages = read_bundle(data)
    for test, r in zip(tests, messages):
        assert (r[0], r[2]) == test[2]


def tests_format_message():
    for message in message_1, message_2:
        source, msg, result = message
        msg = struct.pack('>%iB' % len(msg), *msg)
        assert format_message(*source) == msg


def tests_format_message_null_terminated_address():
    for message in message_1, message_2:
        source, msg, result = message
        source = source[0] + b'\0', source[1]
        msg = struct.pack('>%iB' % len(msg), *msg)
        assert format_message(*source) == msg


def test_format_wrong_types():
    with raises(TypeError):
        format_message(b'/test', values=[u'test'])


def test_format_bundle():
    bundle = format_bundle((message_1[0], message_2[0]), timetag=None)

    assert struct.pack('>%iB' % len(message_1[1]), *message_1[1]) in bundle
    assert struct.pack('>%iB' % len(message_2[1]), *message_2[1]) in bundle

    timetag, messages = read_bundle(bundle)

    assert timetag == approx(time())
    assert len(messages) == 2
    assert messages[0][::2] == message_1[2]
    assert messages[1][::2] == message_2[2]


def test_timetag():
    assert time_to_timetag(None) == (0, 1)
    assert time_to_timetag(0)[1] == 0
