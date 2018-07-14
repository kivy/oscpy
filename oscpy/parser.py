'''Parse and format data types, from and to packets that can be sent

types are automatically infered using the `parsers` and `writters` members.

Allowed types are:
    int (but not *long* ints) -> osc int
    floats -> osc float
    bytes (encoded strings) -> osc strings
    bytearray (raw data) -> osc blob

'''
from struct import Struct, pack, unpack_from, calcsize
from time import time
import sys

if sys.version_info.major > 2:
    UNICODE = str
else:
    UNICODE = unicode

Int = Struct('>i')
Float = Struct('>f')
String = Struct('>s')
TimeTag = Struct('>II')

TP_PACKET_FORMAT = "!12I"
# 1970-01-01 00:00:00
NTP_DELTA = 2208988800


def padded(l, n=4):
    m, r = divmod(l, n)
    return n * (min(1, r) + l // n)


def parse_int(value, offset=0, **kwargs):
    return Int.unpack_from(value, offset)[0], Int.size


def parse_float(value, offset=0, **kwargs):
    return Float.unpack_from(value, offset)[0], Float.size


def parse_string(value, offset=0, encoding='', encoding_errors='strict'):
    result = []
    n = 0
    while True:
        c = String.unpack_from(value, offset + n)[0]
        n += String.size

        if c == b'\0':
            break
        result.append(c)

    r = b''.join(result)
    if encoding:
        return r.decode(encoding, errors=encoding_errors), padded(n)
    else:
        return r, padded(n)


def parse_blob(value, offset=0, **kwargs):
    size = calcsize('>i')
    length = unpack_from('>i', value, offset)[0]
    data = unpack_from('>%iQ' % length, value, offset + size)
    return data, padded(length, 8)


parsers = {
    b'i': parse_int,
    b'f': parse_float,
    b's': parse_string,
    b'b': parse_blob,
}

parsers.update({
    ord(k): v
    for k, v in parsers.items()
})

writters = (
    (float, (b'f', b'f')),
    (int, (b'i', b'i')),
    (bytes, (b's', b'%is')),
    (bytearray, (b'b', b'%ib')),
)

padsizes = {
    bytes: 4,
    bytearray: 8
}


def parse(hint, value, offset=0, encoding='', encoding_errors='strict'):
    parser = parsers.get(hint)

    if not parser:
        raise ValueError(
            "no known parser for type hint: {}, value: {}".format(hint, value)
        )

    return parser(
        value, offset=offset, encoding=encoding,
        encoding_errors=encoding_errors
    )


def format_message(address, values, encoding='', encoding_errors='strict'):
    tags = [b',']
    fmt = []
    if encoding:
        values = values[:]

    for i, v in enumerate(values):
        if encoding and isinstance(v, UNICODE):
            v = v.encode(encoding, errors=encoding_errors)
            values[i] = v

        for cls, writter in writters:
            if isinstance(v, cls):
                tag, f = writter
                if b'%i' in f:
                    v += b'\0'
                    f = f % padded(len(v), padsizes[cls])

                tags.append(tag)
                fmt.append(f)
                break
        else:
            raise TypeError(
                u'unable to find a writter for value {}, type not in: {}.'
                .format(v, [x[0] for x in writters])
            )

    fmt = b''.join(fmt)
    tags = b''.join(tags + [b'\0'])

    if encoding and isinstance(address, UNICODE):
        address = address.encode(encoding, errors=encoding_errors)

    if not address.endswith(b'\0'):
        address += b'\0'

    fmt = b'>%is%is%s' % (padded(len(address)), padded(len(tags)), fmt)
    return pack(fmt, address, tags, *values)


def read_message(data, offset=0, encoding='', encoding_errors='strict'):
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
        v, off = parse(
            tag, data, offset=offset + n, encoding=encoding,
            encoding_errors=encoding_errors
        )
        values.append(v)
        n += off

    return address, tags, values, n


def time_to_timetag(timetag):
    if timetag is None:
        return (0, 1)
    seconds, fract = divmod(timetag, 1)
    seconds += NTP_DELTA
    seconds = int(seconds)
    fract = int(fract * 2**32)
    return (seconds, fract)


def timetag_to_time(timetag):
    if timetag == (0, 1):
        return time()

    seconds, fract = timetag
    return seconds + fract / 2. ** 32 - NTP_DELTA


def format_bundle(data, timetag=None, encoding='', encoding_errors='strict'):
    timetag = time_to_timetag(timetag)
    bundle = [pack('8s', b'#bundle\0')]
    bundle.append(TimeTag.pack(*timetag))

    for address, values in data:
        msg = format_message(
            address, values, encoding='',
            encoding_errors=encoding_errors
        )
        bundle.append(pack('>i', len(msg)))
        bundle.append(msg)

    return b''.join(bundle)


def read_bundle(data, encoding='', encoding_errors='strict'):
    length = len(data)

    header = unpack_from('7s', data, 0)[0]
    offset = 8 * String.size
    if header != b'#bundle':
        raise ValueError(
            "the message doesn't start with '#bundle': {}".format(header))

    timetag = timetag_to_time(TimeTag.unpack_from(data, offset))
    offset += TimeTag.size

    messages = []
    while offset < length:
        # NOTE, we don't really care about the size of the message, our
        # parsing will compute it anyway
        # size = Int.unpack_from(data, offset)
        offset += Int.size
        address, tags, values, off = read_message(
            data, offset, encoding=encoding, encoding_errors=encoding_errors
        )
        offset += off
        messages.append((address, tags, values, offset))

    return (timetag, messages)


def read_packet(data, drop_late=False, encoding='', encoding_errors='strict'):
    d = unpack_from('>c', data, 0)[0]
    if d == b'/':
        return [
            read_message(
                data, encoding=encoding,
                encoding_errors=encoding_errors
            )
        ]

    elif d == b'#':
        timetag, messages = read_bundle(
            data, encoding=encoding, encoding_errors=encoding_errors
        )
        if drop_late:
            if time() > timetag:
                return []
        return messages
    else:
        raise ValueError('packet is not a message or a bundle')
