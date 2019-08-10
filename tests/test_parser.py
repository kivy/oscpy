# coding: utf8

from oscpy.parser import (
    parse, padded, read_message, read_bundle, read_packet,
    format_message, format_bundle, timetag_to_time, time_to_timetag,
    format_midi, format_true, format_false, format_nil, format_infinitum, MidiTuple
)
from pytest import approx, raises
from time import time
import struct
from oscpy.stats import Stats

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


def test_parse_string_encoded():
    assert parse(
        b's', struct.pack('%is' % padded(len('t')), u'é'.encode('utf8')),
        encoding='utf8'
    )[0] == u'é'

    s = u'aééééààààa'
    s_ = s.encode('utf8')
    assert parse(
        b's',
        struct.pack('%is' % padded(len(s_) + 1), s_ + b'\0'),
        encoding='utf8'
    )[0] == s

    with raises(UnicodeDecodeError):
        parse(
            b's',
            struct.pack('%is' % padded(len(s_) + 1), s_ + b'\0'),
            encoding='ascii'
        )[0] == s

    assert parse(
        b's',
        struct.pack('%is' % padded(len(s_) + 1), s_ + b'\0'),
        encoding='ascii',
        encoding_errors='replace'
    )[0] == u'a����������������a'

    assert parse(
        b's',
        struct.pack('%is' % padded(len(s_) + 1), s_ + b'\0'),
        encoding='ascii',
        encoding_errors='ignore'
    )[0] == 'aa'


def test_parse_blob():
    length = 10
    data = tuple(range(length))
    pad = padded(length, 8)
    fmt = '>i%iQ' % pad
    s = struct.pack(fmt, length, *(data + (pad - length) * (0, )))
    result = parse(b'b', s)[0]
    assert result == data


def test_parse_midi():
    data = MidiTuple(0, 144, 72, 64)
    result = parse(b'm', struct.pack('>I', format_midi(data)))[0]
    assert result == data


def test_parse_nil():
    result = parse(b'N', '')[0]
    assert result == None


def test_parse_true():
    result = parse(b'T', '')[0]
    assert result == True


def test_parse_false():
    result = parse(b'F', '')[0]
    assert result == False


def test_parse_inf():
    result = parse(b'I', '')[0]
    assert result == float('inf')


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
    msg, stat = format_message(b'test', [])
    with raises(ValueError, match="doesn't start with a '/'") as e:
        address, tags, values, size = read_message(msg)


def test_read_broken_bundle():
    s = b'not a bundle'
    data = struct.pack('>%is' % len(s), s)
    with raises(ValueError):
        read_bundle(data)


def test_read_broken_message():
    # a message where ',' starting the list of tags has been replaced
    # with \x00
    s = b'/tmp\x00\x00\x00\x00\x00i\x00\x00\x00\x00\x00\x01'
    with raises(ValueError):
        read_message(s)


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


def test_read_packet():
    with raises(ValueError):
        read_packet(struct.pack('>%is' % len('test'), b'test'))


def tests_format_message():
    for message in message_1, message_2:
        source, msg, result = message
        msg = struct.pack('>%iB' % len(msg), *msg)
        assert format_message(*source)[0] == msg


def tests_format_message_null_terminated_address():
    for message in message_1, message_2:
        source, msg, result = message
        source = source[0] + b'\0', source[1]
        msg = struct.pack('>%iB' % len(msg), *msg)
        assert format_message(*source)[0] == msg


def test_format_true():
    assert format_true(True) == tuple()


def test_format_false():
    assert format_false(False) == tuple()


def test_format_nil():
    assert format_nil(None) == tuple()


def test_format_inf():
    assert format_infinitum(float('inf')) == tuple()


def test_format_wrong_types():
    with raises(TypeError):
        format_message(b'/test', values=[u'test'])


def test_format_unknown_type():
    with raises(TypeError):
        format_message(b'/test', values=[object])


def test_format_bundle():
    bundle, stats = format_bundle((message_1[0], message_2[0]), timetag=None)

    assert struct.pack('>%iB' % len(message_1[1]), *message_1[1]) in bundle
    assert struct.pack('>%iB' % len(message_2[1]), *message_2[1]) in bundle

    timetag, messages = read_bundle(bundle)

    assert timetag == approx(time())
    assert len(messages) == 2
    assert messages[0][::2] == message_1[2]
    assert messages[1][::2] == message_2[2]

    assert stats.calls == 2
    assert stats.bytes == 72
    assert stats.params == 6
    assert stats.types['f'] == 3
    assert stats.types['i'] == 2
    assert stats.types['s'] == 1


def test_timetag():
    assert time_to_timetag(None) == (0, 1)
    assert time_to_timetag(0)[1] == 0
    assert time_to_timetag(30155831.26845886) == (2239144631, 1153022032)
    assert timetag_to_time(time_to_timetag(30155831.26845886)) == approx(30155831.26845886)  # noqa


def test_format_encoding():
    s = u'éééààà'
    with raises(TypeError):
        read_message(format_message('/test', [s])[0])

    assert read_message(format_message('/test', [s], encoding='utf8')[0])[2][0] == s.encode('utf8')  # noqa
    assert read_message(format_message('/test', [s], encoding='utf8')[0], encoding='utf8')[2][0] == s  # noqa

    with raises(UnicodeEncodeError):
        format_message('/test', [s], encoding='ascii')  # noqa

    with raises(UnicodeDecodeError):
        read_message(format_message('/test', [s], encoding='utf8')[0], encoding='ascii')  # noqa

    assert read_message(
        format_message('/test', [s], encoding='utf8')[0],
        encoding='ascii', encoding_errors='ignore'
    )[2][0] == ''

    assert read_message(
        format_message('/test', [s], encoding='utf8')[0],
        encoding='ascii', encoding_errors='replace'
    )[2][0] == u'������������'
