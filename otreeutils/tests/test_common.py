from collections import OrderedDict

import pytest

from otreeutils.common import columnwise_data_as_rows, hierarchical_data_columnwise

NN = None


def test_columnwise_data_as_rows():
    assert columnwise_data_as_rows({}, with_header=True) == ([], [])
    assert columnwise_data_as_rows({}, with_header=False) == []

    assert columnwise_data_as_rows({'a': [], 'b': []}, with_header=True) == (['a', 'b'], [])
    assert columnwise_data_as_rows({'a': [], 'b': []}, with_header=False) == []

    assert columnwise_data_as_rows({'a': [1, 2, 3], 'b': [4, 5, 6]}, with_header=False) == [(1, 4), (2, 5), (3, 6)]

    with pytest.raises(ValueError):
        columnwise_data_as_rows({'a': [], 'b': [1]})

    with pytest.raises(ValueError):
        columnwise_data_as_rows({'a': [1, 2], 'b': [3, 4, 5]})


def test_hierarchical_data_columnwise_empty():
    assert hierarchical_data_columnwise([]) == {}


def test_hierarchical_data_columnwise_1level():
    # test data 1

    input = [
        {'a': 1, 'b': 3},
    ]

    output = hierarchical_data_columnwise(input)

    _check_hierarchical_data_columnwise_return_type(output)

    assert list(output.items()) == [
        ('a', [1]),
        ('b', [3]),
    ]

    # test data 2

    input = [
        {'a': 1, 'b': 3},
        {'a': 1, 'b': 4},
    ]

    output = hierarchical_data_columnwise(input)

    _check_hierarchical_data_columnwise_return_type(output)

    assert list(output.items()) == [
        ('a', [1, 1]),
        ('b', [3, 4]),
    ]

    # test data 3

    input = [
        {'a': 1, 'b': 3},
        {'a': 1, 'b': 4, 'c': 5},
    ]

    output = hierarchical_data_columnwise(input)

    _check_hierarchical_data_columnwise_return_type(output)

    assert list(output.items()) == [
        ('a', [1, 1]),
        ('b', [3, 4]),
        ('c', [None, 5]),
    ]

    # test data 3

    input = [
        {'a': 1, 'b': 4, 'c': 5},
        {'a': 1, 'b': 3},
    ]

    output = hierarchical_data_columnwise(input)

    _check_hierarchical_data_columnwise_return_type(output)

    assert list(output.items()) == [
        ('a', [1, 1]),
        ('b', [4, 3]),
        ('c', [5, None]),
    ]


def test_hierarchical_data_columnwise_2levels():
    # test data 1

    input = [
        {
            'a': 1,
            'b': 3,
            'c': [
                {'x': 10},
                {'x': 11},
            ]
        },
        {
            'c': [
                {'x': 12},
            ],
            'a': 2,
            'b': 4
        },
    ]

    output = hierarchical_data_columnwise(input)

    _check_hierarchical_data_columnwise_return_type(output)

    assert list(output.items()) == [
        ('a',   [ 1, 1,   2]),
        ('b',   [ 3, 3,   4]),
        ('c.x', [10, 11, 12]),
    ]

    # test data 2

    input = [
        {
            'a': 1,
            'b': 3,
            'c': [
                {'x': 10},
                {'x': 11},
            ]
        },
        {
            'a': 2,
            'b': 4,
            'c': [
                {'x': 12},
            ],
        },
    ]

    output = hierarchical_data_columnwise(input)

    _check_hierarchical_data_columnwise_return_type(output)

    assert list(output.items()) == [
        ('a',   [ 1, 1,   2]),
        ('b',   [ 3, 3,   4]),
        ('c.x', [10, 11, 12]),
    ]

    # test data 3

    input = [
        {
            'a': 1,
            'b': 3,
            'c': []
        },
        {
            'a': 2,
            'b': 4,
            'c': [
                {'x': 12},
            ],
        },
    ]

    output = hierarchical_data_columnwise(input)

    _check_hierarchical_data_columnwise_return_type(output)

    assert list(output.items()) == [
        ('a',   [   1,  2]),
        ('b',   [   3,  4]),
        ('c.x', [None, 12]),
    ]

    # test data 4

    input = [
        {
            'a': 1,
            'b': 3,
            'c': [
                {'x': 10},
                {'x': 11},
            ],
            'd': []
        },
        {
            'a': 2,
            'b': 4,
            'c': [
                {'x': 12},
                {'x': 12},
            ],
            'd': [
                {'x': 13, 'y': 14},
                {'x': 15, 'y': 16},
                {'x': 17, 'y': 18},
            ]
        },
    ]

    output = hierarchical_data_columnwise(input)

    _check_hierarchical_data_columnwise_return_type(output)

    assert list(output.items()) == [
        ('a',   [ 1,  1,  2,  2,  2,  2,  2]),
        ('b',   [ 3,  3,  4,  4,  4,  4,  4]),
        ('c.x', [10, 11, 12, 12, NN, NN, NN]),
        ('d.x', [NN, NN, NN, NN, 13, 15, 17]),
        ('d.y', [NN, NN, NN, NN, 14, 16, 18]),
    ]

    # test data 5

    input = [
        {
            'a': 1,
            'b': 3,
            'c': [
                {'x': 10},
                {'x': 11},
            ],
            'd': []
        },
        {
            'a': 2,
            'b': 4,
            'c': [
                {'x': 12},
            ],
            'd': [
                {'x': 13, 'y': 14},
                {'x': 15, 'y': 16},
                {'x': 17, 'y': 18},
            ]
        },
    ]

    output = hierarchical_data_columnwise(input)

    _check_hierarchical_data_columnwise_return_type(output)

    assert list(output.items()) == [
        ('a',   [ 1,  1,  2,  2,  2,  2]),
        ('b',   [ 3,  3,  4,  4,  4,  4]),
        ('c.x', [10, 11, 12, NN, NN, NN]),
        ('d.x', [NN, NN, NN, 13, 15, 17]),
        ('d.y', [NN, NN, NN, 14, 16, 18]),
    ]

    # test data 6

    input = [
        {
            'a': 1,
            'b': [
                {
                    'x': 2,
                    'y': 3,
                },
                {
                    'x': 4,
                    'y': 5,
                }
            ],
            'c': [
                {
                    'z': 6,
                }
            ]
        },
        {
            'a': 7,
            'b': [],
            'c': [
                {
                    'z': 8,
                },
                {
                    'z': 9,
                }
            ]
        },
    ]

    output = hierarchical_data_columnwise(input)

    _check_hierarchical_data_columnwise_return_type(output)

    assert list(output.items()) == [
        ('a',   [   1,     1,      1,      7,      7]),
        ('b.x', [   2,     4,   None,   None,   None]),
        ('b.y', [   3,     5,   None,   None,   None]),
        ('c.z', [None,  None,      6,      8,      9])
    ]


def test_hierarchical_data_columnwise_3levels():
    # test data 1

    input = [
        {
            'a': [
                {
                    'h': [
                        {'i': 100, 'j': 110},
                        {'i': 120, 'j': 130},
                    ],
                    'k': 10
                }
            ],
            'b': [
                {
                    'x': 2,
                    'y': 3,
                },
                {
                    'x': 4,
                    'y': 5,
                }
            ],
            'c': [
                {
                    'z': 6,
                }
            ]
        },
        {
            'a': [
                {
                    'k': 11,
                    'h': [
                        {'i': 200, 'j': 210},
                    ]
                }
            ],
            'b': [],
            'c': [
                {
                    'z': 8,
                },
                {
                    'z': 9,
                }
            ]
        },
    ]

    output = hierarchical_data_columnwise(input)

    _check_hierarchical_data_columnwise_return_type(output)

    assert list(output.items()) == [
        ('a.h.i', [100, 120, NN, NN, NN, 200, NN, NN]),
        ('a.h.j', [110, 130, NN, NN, NN, 210, NN, NN]),
        ('a.k',   [ 10,  10, NN, NN, NN,  11, NN, NN]),
        ('b.x',   [ NN,  NN,  2,  4, NN,  NN, NN, NN]),
        ('b.y',   [ NN,  NN,  3,  5, NN,  NN, NN, NN]),
        ('c.z',   [ NN,  NN, NN, NN,  6,  NN,  8,  9])
    ]


def test_hierarchical_data_columnwise_invalid_data():
    pass


def _check_hierarchical_data_columnwise_return_type(output):
    assert type(output) is OrderedDict

