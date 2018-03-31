import struct


def parse_int(value):
    return struct.unpack('>i', value)[0]


def parse_float(value):
    return struct.unpack('>f', value)[0]


def parse_string(value):
    pass


def parse_blob(value):
    pass


parsers = {
    b'i': parse_int,
    b'f': parse_float,
    b's': parse_string,
    b'b': parse_blob,
}


def parse(hint, value):
    parser = parsers.get(hint)

    if not parser:
        raise ValueError(
            "no known parser for type hint: {}, value: {}".format(hint, value)
        )

    return parser(value)
