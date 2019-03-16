from collections import Counter
from textwrap import dedent

from oscpy.stats import Stats


def test_create_stats():
    stats = Stats(calls=1, bytes=2, params=3, types=Counter('abc'))
    assert stats.calls == 1
    assert stats.bytes == 2
    assert stats.params == 3
    assert stats.types['a'] == 1


def test_add_stats():
    stats = Stats(calls=1) + Stats(calls=3, bytes=2)
    assert stats.calls == 4
    assert stats.bytes == 2


def test_compare_stats():
    assert Stats(
        calls=1, bytes=2, params=3, types=Counter('abc')
    ) == Stats(
        calls=1, bytes=2, params=3, types=Counter('abc')
    )


def test_to_tuple_stats():
    tpl = Stats(
        calls=1, bytes=2, params=3, types=Counter("import antigravity")
    ).to_tuple()

    assert tpl[:3] == (1, 2, 3,)
    assert set(tpl[3]) == set('import antigravity')


def test_repr_stats():
    r = repr(Stats(calls=0, bytes=1, params=2, types=Counter('abc')))
    assert r == dedent(
    '''
    Stats:
        calls: 0
        bytes: 1
        params: 2
        types:
            a: 1
            b: 1
            c: 1
    ''').strip()
