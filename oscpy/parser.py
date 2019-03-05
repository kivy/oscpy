"""Parse and format data types, from and to packets that can be sent.

types are automatically inferred using the `parsers` and `writers` members.

Allowed types are:
    int (but not *long* ints) -> osc int
    floats -> osc float
    bytes (encoded strings) -> osc strings
    bytearray (raw data) -> osc blob

"""
from collections import namedtuple
from struct import Struct, pack, unpack_from, calcsize
from time import time
import sys

if sys.version_info.major > 2:
    UNICODE = str
    izip = zip
else:
    UNICODE = unicode
    from itertools import izip

Int = Struct('>i')
Float = Struct('>f')
String = Struct('>s')
TimeTag = Struct('>II')

TP_PACKET_FORMAT = "!12I"
# 1970-01-01 00:00:00
NTP_DELTA = 2208988800

MidiTuple = namedtuple('MidiTuple', 'port_id status_byte data1 data2')


def padded(l, n=4):
    """Return the size to pad a thing to.

    - `l` being the current size of the thing.
    - `n` being the desired divisor of the thing's padded size.
    """
    m, r = divmod(l, n)
    return n * (min(1, r) + l // n)


def parse_int(value, offset=0, **kwargs):
    """Return an int from offset in value."""
    return Int.unpack_from(value, offset)[0], Int.size


def parse_float(value, offset=0, **kwargs):
    """Return a float from offset in value."""
    return Float.unpack_from(value, offset)[0], Float.size


def parse_string(value, offset=0, encoding='', encoding_errors='strict'):
    """Return a string from offset in value.

    If encoding is defined, the string will be decoded. `encoding_errors`
    will be used to manage encoding errors in decoding.
    """
    result = []
    n = 0
    ss = String.size
    while True:
        c = String.unpack_from(value, offset + n)[0]
        n += ss

        if c == b'\0':
            break
        result.append(c)

    r = b''.join(result)
    if encoding:
        return r.decode(encoding, errors=encoding_errors), padded(n)
    else:
        return r, padded(n)


def parse_blob(value, offset=0, **kwargs):
    """Return a blob from offset in value."""
    size = calcsize('>i')
    length = unpack_from('>i', value, offset)[0]
    data = unpack_from('>%iQ' % length, value, offset + size)
    return data, padded(length, 8)


def parse_midi(value, offset=0, **kwargs):
    """Return a MIDI tuple from offset in value.

    A valid MIDI message: (port id, status byte, data1, data2).
    """
    val = unpack_from('>I', value, offset)[0]
    args = tuple((val & 0xFF << 8 * i) >> 8 * i for i in range(3, -1, -1))
    midi = MidiTuple(*args)
    return midi, len(midi)


def format_midi(value):
    return sum((val & 0xFF) << 8 * (3 - pos) for pos, val in enumerate(value))


parsers = {
    b'i': parse_int,
    b'f': parse_float,
    b's': parse_string,
    b'b': parse_blob,
    b'm': parse_midi,
}

parsers.update({
    ord(k): v
    for k, v in parsers.items()
})

writers = (
    (float, (b'f', b'f')),
    (int, (b'i', b'i')),
    (bytes, (b's', b'%is')),
    (UNICODE, (b's', b'%is')),
    (bytearray, (b'b', b'%ib')),
    (MidiTuple, (b'm', b'I'))
)

# XXX in case someone imported writters from us, keep the misspelled
# version around for some time
writters = writers

padsizes = {
    bytes: 4,
    bytearray: 8
}


def parse(hint, value, offset=0, encoding='', encoding_errors='strict'):
    """Call the correct parser function for the provided hint.

    `hint` will be used to determine the correct parser, other parameters
    will be passed to this parser.
    """
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
    """Create a message."""
    tags = [b',']
    fmt = []

    encode_cache = {}

    for i, v in enumerate(values):
        for cls, writer in writers:
            if isinstance(v, cls):
                if cls == UNICODE:
                    if encoding:
                        cls = bytes
                        if v in encode_cache:
                            v = encode_cache[v]
                        else:
                            v = encode_cache.setdefault(
                                v, v.encode(encoding, errors=encoding_errors)
                            )
                    else:
                        raise TypeError(u"Can't format unicode string without encoding")

                tag, f = writer
                if b'%i' in f:
                    f = f % padded(len(v) + 1, padsizes[cls])

                tags.append(tag)
                fmt.append(f)
                break
        else:
            raise TypeError(
                u'unable to find a writer for value {}, type not in: {}.'
                .format(v, [x[0] for x in writers])
            )

    fmt = b''.join(fmt)
    tags = b''.join(tags + [b'\0'])

    if encoding and isinstance(address, UNICODE):
        address = address.encode(encoding, errors=encoding_errors)

    if not address.endswith(b'\0'):
        address += b'\0'

    fmt = b'>%is%is%s' % (padded(len(address)), padded(len(tags)), fmt)
    return pack(
        fmt,
        address,
        tags,
        *(
            (
                encode_cache.get(v) + b'\0' if isinstance(v, UNICODE) and encoding
                else (v + b'\0') if t in (b's', b'b')
                else format_midi(v) if isinstance(v, MidiTuple)
                else v
            )
            for t, v in
            izip(tags[1:], values)
        )
    )


def read_message(data, offset=0, encoding='', encoding_errors='strict'):
    """Return address, tags, values, and length of a decoded message.

    Can be called either on a standalone message, or on a message
    extracted from a bundle.
    """
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


def time_to_timetag(time):
    """Create a timetag from a time.

    `time` is an unix timestamp (number of seconds since 1/1/1970).
    result is the equivalent time using the NTP format.
    """
    if time is None:
        return (0, 1)
    seconds, fract = divmod(time, 1)
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
    """Decode a bundle into a (timestamp, messages) tuple."""
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
    """Detect if the data received is a simple message or a bundle, read it.

    Always return a list of messages.
    If drop_late is true, and the received data is an expired bundle,
    then returns an empty list.
    """
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
