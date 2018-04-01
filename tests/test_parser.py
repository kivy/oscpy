from oscpy.parser import parse, padded, read_message, read_bundle
import struct


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
    assert parse(b's', struct.pack('%is' % len(s), s))[0] == s
    s = b'test padding'
    assert parse(b's', struct.pack('%is' % padded(len(s)), s))[0] == s


def test_parse_blob():
    length = 10
    data = tuple(range(length))
    pad = padded(length, 8)
    fmt = '>i%iQ' % pad
    s = struct.pack(fmt, length, *(data + (pad - length) * (0, )))
    result = parse(b'b', s)[0]
    assert result == data


def test_read_message():
    address = b'/test'
    pad = padded(len(address))
    tags = b'i'
    pad_tags = padded(len(tags))
    values = [1]

    fmt = b'>%isc%is%ii' % (pad, pad_tags, len(values))
    assert read_message(
        struct.pack(
            fmt, address, b',', tags, *values)
    )[:-1] == (address, tags, values)


def test_read_bundle():
    pad = padded(len('#bundle'))
    data = struct.pack('>%isQ' % pad, b'#bundle', 1)

    tests = (
        (b'/a', [1]),
        (b'/b', [2]),
        (b'/c', [3]),
        (b'/d', [4]),
        (b'/e', [5]),
    )

    for addr, value in tests:
        fmt = b'>%isc%is%ii' % (padded(len(addr)), padded(2), len(value))

        msg = struct.pack(fmt, addr, b',', b'i', *value)
        assert read_message(msg)[::2] == (addr, value)
        data += struct.pack('>i', len(msg)) + msg

    for i, r in enumerate(read_bundle(data)):
        assert (r[0], r[2]) == tests[i]
