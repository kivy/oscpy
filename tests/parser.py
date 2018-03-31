from oscpy.parser import parse
import struct


def test_parse_int():
    assert parse(b'i', struct.pack('>i', 1)) == 1


def test_parse_float():
    assert parse(b'f', struct.pack('>f', 1.5)) == 1.5
