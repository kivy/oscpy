from oscpy.parser import parse
import struct


def test_parse_int():
    assert parse(b'i', struct.pack('>i', 1)) == 1
