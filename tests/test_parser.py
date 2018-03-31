from oscpy.parser import parse, padded
import struct


def test_parse_int():
    assert parse(b'i', struct.pack('>i', 1)) == 1


def test_parse_float():
    assert parse(b'f', struct.pack('>f', 1.5)) == 1.5


def test_padd_string():
    for i in range(8):
        length = padded(i)
        assert length % 4 == 0
        assert length >= i


def test_parse_string():
    assert parse(b's', struct.pack('%ss' % padded(len('t')), b't')) == b't'
    s = b'test'
    assert parse(b's', struct.pack('%ss' % len(s), s)) == s
    s = b'test padding'
    assert parse(b's', struct.pack('%ss' % padded(len(s)), s)) == s


def test_parse_blob():
    l = 10
    data = tuple(range(l))
    pad = padded(l, 8)
    fmt = '>i%iQ' % pad
    s = struct.pack(fmt, l, *(data + (pad - l) * (0, )))
    result = parse(b'b', s)
    assert result == data
