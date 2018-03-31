import struct

Int = struct.Struct('>i')
Float = struct.Struct('>f')
String = struct.Struct('>s')


def padded(l, n=4):
    m, r = divmod(l, n)
    return n * (min(1, r) + l // n)


def parse_int(value, offset=0):
    return Int.unpack_from(value, offset)[0], Int.size


def parse_float(value, offset=0):
    return Float.unpack_from(value, offset)[0], Float.size


def parse_string(value, offset=0):
    length = len(value)
    return (
        struct.unpack_from('%ss' % length, value, offset)[0].strip(b'\0'),
        String.size * (length + 1)
    )


def parse_blob(value, offset=0):
    size = struct.calcsize('>i')
    length = struct.unpack_from('>i', value, offset)[0]
    data = struct.unpack(
        '>%iQ' % length,
        value[offset + size:offset + size + struct.calcsize('%iQ' % length)]
    )
    return data, length


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


def read_message(data):
    n = 0
    address = []
    while True:
        c = String.unpack_from(data, n)[0]
        print(c)
        if n == 0 and c != b'/':
            raise ValueError("address doesn't start with a '/'")
        elif c == b'\0':
            break
        address.append(c)
        n += 1

    n += 1
    n = padded(n)
    tags = []
    while True:
        c = String.unpack_from(data, n)[0]
        print(n, c)
        # XXX
        # if not tags and c != b',':
        #     raise ValueError("typetags string doesn't start with a ','")
        if c == b'\0':
            n += 1
            break
        if c in parsers.keys():
            tags.append(c)
        elif tags:
            ValueError('unrecognized symbol in typetag string: {}'.format(c))
        n += 1

    n = padded(n)
    address = b''.join(address)
    tags = b''.join(tags)

    print(address)
    n += 1

    values = []
    for tag in tags:
        print(n)
        v, offset = parse(tag, data, offset=n)
        values.append(v)
        n += offset

    return address, tags, values
