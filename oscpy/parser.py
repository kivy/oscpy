import struct

Int = struct.Struct('>i')
Float = struct.Struct('>f')
String = struct.Struct('>s')
TimeTag = struct.Struct('>II')


def padded(l, n=4):
    m, r = divmod(l, n)
    return n * (min(1, r) + l // n)


def parse_int(value, offset=0):
    return Int.unpack_from(value, offset)[0], Int.size


def parse_float(value, offset=0):
    return Float.unpack_from(value, offset)[0], Float.size


def parse_string(value, offset=0):
    result = []
    n = 0
    while True:
        c = String.unpack_from(value, offset + n)[0]
        n += String.size

        if c == b'\0':
            break
        result.append(c)

    return b''.join(result), padded(n)


def parse_blob(value, offset=0):
    size = struct.calcsize('>i')
    length = struct.unpack_from('>i', value, offset)[0]
    data = struct.unpack(
        '>%iQ' % length,
        value[offset + size:offset + size + struct.calcsize('%iQ' % length)]
    )
    return data, padded(length, 8)


parsers = {
    b'i': parse_int,
    b'f': parse_float,
    b's': parse_string,
    b'b': parse_blob,
    ord('i'): parse_int,
    ord('f'): parse_float,
    ord('s'): parse_string,
    ord('b'): parse_blob,
}


def parse(hint, value, offset=0):
    parser = parsers.get(hint)

    if not parser:
        raise ValueError(
            "no known parser for type hint: {}, value: {}".format(hint, value)
        )

    return parser(value, offset=offset)


def read_message(data, offset=0):
    address, size = parse_string(data, offset=offset)
    n = size
    if not address.startswith(b'/'):
        raise ValueError("address {} doesn't start with a '/'".format(address))

    tags, size = parse_string(data, offset=offset + n)
    if not tags.startswith(b','):
        raise ValueError("tag string {} doesn't start with a ','".format(tags))
    tags = tags[1:]

    n += size

    values = []
    for tag in tags:
        v, off = parse(tag, data, offset=offset + n)
        values.append(v)
        n += off

    return address, tags, values, n


def read_bundle(data):
    length = len(data)

    header = struct.unpack_from('7s', data, 0)[0]
    offset = 8 * String.size
    if header != b'#bundle':
        raise ValueError(
            "the message doesn't start with '#bundle': {}".format(header))

    timetag = TimeTag.unpack_from(data, offset)
    offset += TimeTag.size

    messages = []
    while offset < length:
        size = Int.unpack_from(data, offset)
        offset += Int.size
        address, tags, values, off = read_message(data, offset)
        offset += off
        messages.append((address, tags, values))

    return (timetag, messages)
