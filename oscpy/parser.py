"""Parse and format data types, from and to packets that can be sent.

types are automatically inferred using the `PARSERS` and `WRITERS` members.

Allowed types are:
    int (but not *long* ints) -> osc int
    floats -> osc float
    bytes (encoded strings) -> osc strings
    bytearray (raw data) -> osc blob

"""

__all__ = (
    'parse',
    'read_packet', 'read_message', 'read_bundle',
    'format_bundle', 'format_message',
    'MidiTuple',
)


from struct import Struct, pack, unpack_from, calcsize
from time import time
import sys
from collections import Counter
from oscpy.stats import Stats

if sys.version_info.major > 2:  # pragma: no cover
    UNICODE = str
    izip = zip
else:  # pragma: no cover
    UNICODE = unicode
    from itertools import izip

INT = Struct('>i')
FLOAT = Struct('>f')
STRING = Struct('>s')
TIME_TAG = Struct('>II')

TP_PACKET_FORMAT = "!12I"
# 1970-01-01 00:00:00
NTP_DELTA = 2208988800

NULL = b'\0'


def padded(l, n=4):
    """Return the size to pad a thing to.

    - `l` being the current size of the thing.
    - `n` being the desired divisor of the thing's padded size.
    """
    return n * (min(1, divmod(l, n)[1]) + l // n)


def parse_int(value, offset=0, **kwargs):
    """Return an int from offset in value."""
    return INT.unpack_from(value, offset)[0], INT.size


def parse_float(value, offset=0, **kwargs):
    """Return a float from offset in value."""
    return FLOAT.unpack_from(value, offset)[0], FLOAT.size


def parse_string(value, offset=0, encoding='', encoding_errors='strict'):
    """Return a string from offset in value.

    If encoding is defined, the string will be decoded. `encoding_errors`
    will be used to manage encoding errors in decoding.
    """
    result = []
    count = 0
    ss = STRING.size
    while True:
        c = STRING.unpack_from(value, offset + count)[0]
        count += ss

        if c == NULL:
            break
        result.append(c)

    r = b''.join(result)
    if encoding:
        return r.decode(encoding, errors=encoding_errors), padded(count)
    else:
        return r, padded(count)


def parse_blob(value, offset=0, **kwargs):
    """Return a blob from offset in value."""
    size = calcsize('>i')
    length = unpack_from('>i', value, offset)[0]
    data = unpack_from('>%iQ' % length, value, offset + size)
    return data, padded(length, 8)


PARSERS = {
    b'i': parse_int,
    b'f': parse_float,
    b's': parse_string,
    b'b': parse_blob,
}


PARSERS.update({
    ord(k): v
    for k, v in PARSERS.items()
})


WRITERS = (
    (float, (b'f', b'f')),
    (int, (b'i', b'i')),
    (bytes, (b's', b'%is')),
    (UNICODE, (b's', b'%is')),
    (bytearray, (b'b', b'%ib')),
)


PADSIZES = {
    bytes: 4,
    bytearray: 8
}


def parse(hint, value, offset=0, encoding='', encoding_errors='strict'):
    """Call the correct parser function for the provided hint.

    `hint` will be used to determine the correct parser, other parameters
    will be passed to this parser.
    """
    parser = PARSERS.get(hint)

    if not parser:
        raise ValueError(
            "no known parser for type hint: {}, value: {}".format(hint, value)
        )

    return parser(
        value, offset=offset, encoding=encoding,
        encoding_errors=encoding_errors
    )


def format_message(address, values, encoding='', encoding_errors='strict'):
    """Create a message."""
    tags = [b',']
    fmt = []

    encode_cache = {}

    lv = 0
    count = Counter()

    for value in values:
        lv += 1
        cls, writer = None, None
        for cls, writer in WRITERS:
            if isinstance(value, cls):
                break
        else:
            raise TypeError(
                u'unable to find a writer for value {}, type not in: {}.'
                .format(value, [x[0] for x in WRITERS])
            )

        if cls == UNICODE:
            if not encoding:
                raise TypeError(u"Can't format unicode string without encoding")

            cls = bytes
            value = (
                encode_cache[value]
                if value in encode_cache else
                encode_cache.setdefault(
                    value, value.encode(encoding, errors=encoding_errors)
                )
            )

        assert cls, writer

        tag, v_fmt = writer
        if b'%i' in v_fmt:
            v_fmt = v_fmt % padded(len(value) + 1, PADSIZES[cls])

        tags.append(tag)
        fmt.append(v_fmt)
        count[tag.decode('utf8')] += 1

    fmt = b''.join(fmt)
    tags = b''.join(tags + [NULL])

    if encoding and isinstance(address, UNICODE):
        address = address.encode(encoding, errors=encoding_errors)

    if not address.endswith(NULL):
        address += NULL

    fmt = b'>%is%is%s' % (padded(len(address)), padded(len(tags)), fmt)
    message = pack(
        fmt,
        address,
        tags,
        *(
            (
                encode_cache.get(v) + NULL if isinstance(v, UNICODE) and encoding
                else (v + NULL) if t in (b's', b'b')
                else v
            )
            for t, v in
            izip(tags[1:], values)
        )
    )
    return message, Stats(1, len(message), lv, count)


def read_message(data, offset=0, encoding='', encoding_errors='strict'):
    """Return address, tags, values, and length of a decoded message.

    Can be called either on a standalone message, or on a message
    extracted from a bundle.
    """
    address, size = parse_string(data, offset=offset)
    index = size
    if not address.startswith(b'/'):
        raise ValueError("address {} doesn't start with a '/'".format(address))

    tags, size = parse_string(data, offset=offset + index)
    if not tags.startswith(b','):
        raise ValueError("tag string {} doesn't start with a ','".format(tags))
    tags = tags[1:]

    index += size

    values = []
    for tag in tags:
        value, off = parse(
            tag, data, offset=offset + index, encoding=encoding,
            encoding_errors=encoding_errors
        )
        values.append(value)
        index += off

    return address, tags, values, index


def time_to_timetag(value):
    """Create a timetag from a time.

    `time` is an unix timestamp (number of seconds since 1/1/1970).
    result is the equivalent time using the NTP format.
    """
    if value is None:
        return (0, 1)
    seconds, fract = divmod(value, 1)
    seconds += NTP_DELTA
    seconds = int(seconds)
    fract = int(fract * 2**32)
    return (seconds, fract)


def timetag_to_time(timetag):
    """Decode a timetag to a time.

    `timetag` is an NTP formated time.
    retult is the equivalent unix timestamp (number of seconds since 1/1/1970).
    """
    if timetag == (0, 1):
        return time()

    seconds, fract = timetag
    return seconds + fract / 2. ** 32 - NTP_DELTA


def format_bundle(data, timetag=None, encoding='', encoding_errors='strict'):
    """Create a bundle from a list of (address, values) tuples.

    String values will be encoded using `encoding` or must be provided
    as bytes.
    `encoding_errors` will be used to manage encoding errors.
    """
    timetag = time_to_timetag(timetag)
    bundle = [pack('8s', b'#bundle\0')]
    bundle.append(TIME_TAG.pack(*timetag))

    stats = Stats()
    for address, values in data:
        msg, st = format_message(
            address, values, encoding='',
            encoding_errors=encoding_errors
        )
        bundle.append(pack('>i', len(msg)))
        bundle.append(msg)
        stats += st

    return b''.join(bundle), stats


def read_bundle(data, encoding='', encoding_errors='strict'):
    """Decode a bundle into a (timestamp, messages) tuple."""
    length = len(data)

    header = unpack_from('7s', data, 0)[0]
    offset = 8 * STRING.size
    if header != b'#bundle':
        raise ValueError(
            "the message doesn't start with '#bundle': {}".format(header))

    timetag = timetag_to_time(TIME_TAG.unpack_from(data, offset))
    offset += TIME_TAG.size

    messages = []
    while offset < length:
        # NOTE, we don't really care about the size of the message, our
        # parsing will compute it anyway
        # size = Int.unpack_from(data, offset)
        offset += INT.size
        address, tags, values, off = read_message(
            data, offset, encoding=encoding, encoding_errors=encoding_errors
        )
        offset += off
        messages.append((address, tags, values, offset))

    return (timetag, messages)


def read_packet(data, drop_late=False, encoding='', encoding_errors='strict'):
    """Detect if the data received is a simple message or a bundle, read it.

    Always return a list of messages.
    If drop_late is true, and the received data is an expired bundle,
    then returns an empty list.
    """
    header = unpack_from('>c', data, 0)[0]
    if header == b'/':
        return [
            read_message(
                data, encoding=encoding,
                encoding_errors=encoding_errors
            )
        ]

    elif header == b'#':
        timetag, messages = read_bundle(
            data, encoding=encoding, encoding_errors=encoding_errors
        )
        if drop_late:
            if time() > timetag:
                return []
        return messages
    else:
        raise ValueError('packet is not a message or a bundle')
