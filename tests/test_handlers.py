# -*- coding: utf-8 -*-

import collections
import pytest

from collections import OrderedDict

from typo.handlers import Handler
from typing import Any, List, Tuple, Dict, Sequence, MutableSequence, Set, TypeVar


pytest.add_handler_test(
    'test_any', (Any, object), 'Any',
    ok=[
        None,
        (1, '2', {})
    ]
)

pytest.add_handler_test(
    'test_builtin_type', int, 'int',
    ok=[
        42
    ],
    fail=[
        ('foo', 'expected int, got str')
    ]
)

P = type('P', (), {})
A = type('A', (P,), {})
B = type('B', (A,), {})

pytest.add_handler_test(
    'test_user_type', A, 'test_handlers.A',
    ok=[
        A(),
        B()
    ],
    fail=[
        (A, 'expected test_handlers.A, got type'),
        (42, 'expected test_handlers.A, got int'),
        (P(), 'expected test_handlers.A, got test_handlers.P')
    ]
)

pytest.add_handler_test(
    'test_list_basic', List[int], 'List[int]',
    ok=[
        [],
        [1],
        [1, 2, 3]
    ],
    fail=[
        (1, 'expected list, got int'),
        ([1, 'foo', 2], 'invalid item #1.*expected int, got str')
    ]
)

pytest.add_handler_test(
    'test_list_nested', List[List[int]], 'List[List[int]]',
    ok=[
        [],
        [[]],
        [[], []],
        [[1, 2], [], [3]]
    ],
    fail=[
        (1, 'expected list, got int'),
        ([[], 1, []], 'invalid item #1.*expected list, got int'),
        ([[], [1, 2, [], 4]], 'invalid item #2 of item #1.*expected int, got list')
    ]
)

pytest.add_handler_test(
    'test_list_no_typevar', (List, List[Any], List[object]), 'list',
    ok=[
        [],
        [1, 'foo']
    ],
    fail=[
        (1, 'expected list, got int')
    ]
)

pytest.add_handler_test(
    'test_tuple_no_ellipsis', Tuple[int, str], 'Tuple[int, str]',
    ok=[
        (1, 'foo')
    ],
    fail=[
        (42, 'expected tuple, got int'),
        ((1, 2, 3), 'expected tuple of length 2, got tuple of length 3'),
        (('foo', 'bar'), 'invalid item #0.*expected int, got str'),
        ((1, 2), 'invalid item #1.*expected str, got int')
    ]
)

pytest.add_handler_test(
    'test_tuple_ellipsis', Tuple[int, ...], 'Tuple[int, ...]',
    ok=[
        (),
        (1,),
        (1, 2, 3)
    ],
    fail=[
        (42, 'expected tuple, got int'),
        ((1, 'foo'), 'invalid item #1.*expected int, got str')
    ]
)

pytest.add_handler_test(
    'test_tuple_no_typevar', (Tuple, Tuple[Any, ...], Tuple[object, ...]), 'tuple',
    ok=[
        (),
        (1, 'foo')
    ],
    fail=[
        (1, 'expected tuple, got int')
    ]
)

pytest.add_handler_test(
    'test_dict_basic', Dict[int, str], 'Dict[int, str]',
    ok=[
        {},
        {1: 'foo', 2: 'bar'}
    ],
    fail=[
        (42, 'expected dict, got int'),
        ({1: 'foo', 2: 3}, 'invalid value at 2 of.*expected str, got int'),
        ({1: 'foo', 'bar': 'baz'}, 'invalid key of.*expected int, got str')
    ]
)

pytest.add_handler_test(
    'test_dict_complex', Dict[Tuple[object, int], List[Dict[Any, str]]],
    'Dict[Tuple[Any, int], List[Dict[Any, str]]]',
    ok=[
        {},
        {('foo', 1): [{2: 'bar'}]}
    ],
    fail=[
        ({('foo', 'bar'): []},
         'invalid item #1 of key of.*expected int, got str'),
        ({(1, 1): [{3: 'bar', 'baz': 2}]},
         r'invalid value at \'baz\' of item #0 of value at \(1, 1\) of.*expected str, got int')
    ]
)

pytest.add_handler_test(
    'test_dict_no_typevar', (Dict, Dict[Any, Any], Dict[Any, object],
                             Dict[object, Any], Dict[object, object]), 'dict',
    ok=[
        {},
        {1: 'foo', 'bar': 2}
    ],
    fail=[
        (42, 'expected dict, got int')
    ]
)


class MySequence(collections.Sequence):
    def __len__(self):
        return 2

    def __getitem__(self, k):
        return [0, 1][k]


class MyMutableSequence(MySequence, collections.MutableSequence):
    def __setitem__(self, k):
        pass

    def __delitem__(self, k):
        pass

    def insert(self, k, v):
        pass


pytest.add_handler_test(
    'test_sequence', Sequence[int], 'Sequence[int]',
    ok=[
        [],
        [1, 2],
        MySequence(),
        MyMutableSequence()
    ],
    fail=[
        (42, 'expected sequence, got int'),
        ([1, '2'], 'invalid item #1.*expected int, got str')
    ]
)

pytest.add_handler_test(
    'test_sequence_no_typevar', (Sequence, collections.Sequence,
                                 Sequence[object], Sequence[Any]),
    'Sequence',
    ok=[
        [],
        [1, 'foo'],
        MySequence(),
        MyMutableSequence()
    ],
    fail=[
        (42, 'expected sequence, got int')
    ]
)

pytest.add_handler_test(
    'test_mutable_sequence', MutableSequence[int], 'MutableSequence[int]',
    ok=[
        [],
        [1, 2],
        MyMutableSequence()
    ],
    fail=[
        (42, 'expected mutable sequence, got int'),
        (MySequence(), 'expected mutable sequence, got test_handlers.MySequence'),
        ([1, '2'], 'invalid item #1.*expected int, got str')
    ]
)

pytest.add_handler_test(
    'test_sequence_no_typevar', (MutableSequence, collections.MutableSequence,
                                 MutableSequence[object], MutableSequence[Any]),
    'MutableSequence',
    ok=[
        [],
        [1, 'foo'],
        MyMutableSequence()
    ],
    fail=[
        (42, 'expected mutable sequence, got int'),
        (MySequence(), 'expected mutable sequence, got test_handlers.MySequence')
    ]
)

pytest.add_handler_test(
    'test_set', Set[int], 'Set[int]',
    ok=[
        set(),
        {1},
        {1, 2, 3}
    ],
    fail=[
        (1, 'expected set, got int'),
        ({1, 'foo', 2}, 'invalid item of.*expected int, got str')
    ]
)

pytest.add_handler_test(
    'test_set_no_typevar', (Set, Set[Any], Set[object]), 'set',
    ok=[
        set(),
        {1, 'foo'}
    ],
    fail=[
        (1, 'expected set, got int')
    ]
)


@pytest.mark.parametrize('bound', [
    List['T'], List[TypeVar('T', int, 'T')]
])
def test_forward_reference(bound):
    pytest.raises_regexp(ValueError, 'forward references are not currently supported',
                         Handler, bound)


@pytest.mark.parametrize('bound', [
    List[int], Dict[int, int], Set[int], TypeVar('X'), List[TypeVar('X')]
])
def test_invalid_typevar_bound(bound):
    T = TypeVar('T', bound=bound)
    pytest.raises_regexp(ValueError, 'invalid typevar bound',
                         Handler, T)


@pytest.mark.parametrize('constraint', [
    Any, List[int], Dict[int, int], Set[int]
])
def test_invalid_typevar_constraint(constraint):
    T = TypeVar('T', int, constraint)
    pytest.raises_regexp(ValueError, 'invalid typevar constraint',
                         Handler, T)


class Int(int):
    ...

T, U = TypeVar('T'), TypeVar('U')


pytest.add_handler_test(
    'test_typevar_basic', Tuple[T, Dict[U, T]], 'Tuple[T, Dict[U, T]]',
    ok=[
        (1, {}),
        (1, {1: 2, 3: 4}),
        ({}, {'a': {1: 2}})
    ],
    fail=[
        (1, 'expected tuple, got int'),
        ((1, {2: '3'}), 'invalid value at 2 of item #1.*cannot assign str to T'),
        ((1, OrderedDict([('a', 1), (2, 3)])), 'key.*cannot assign int to U'),
        ((1, OrderedDict([(Int(2), 3), (4, 5)])), 'key.*cannot assign int to U'),
        ((1, OrderedDict([(2, 3), (Int(4), 5)])), 'key.*cannot assign test_handlers.Int to U'),
        ((Int(1), {'a': 2}), 'invalid value.*cannot assign int to T'),
        ((1, {'a': Int(2)}), 'invalid value.*cannot assign test_handlers.Int to T')
    ]
)

V = TypeVar('V', bound=int)

pytest.add_handler_test(
    'test_typevar_bound', List[V], 'List[V]',
    ok=[
        [],
        [1, 2],
        [Int(1), Int(2)]
    ],
    fail=[
        ('foo', 'expected list, got str'),
        (['a'], r'cannot assign str to V'),
        ([1, 'a'], r'cannot assign str to V'),
        ([1, Int(2)], r'cannot assign test_handlers.Int to V'),
        ([Int(1), 2], r'cannot assign int to V')
    ]
)

W = TypeVar('W', int, float)

pytest.add_handler_test(
    'test_typevar_basic_constraints', Tuple[W, W], 'Tuple[W, W]',
    ok=[
        (1, 2),
        (1.1, 2.2)
    ],
    fail=[
        (('a', 'b'), 'cannot assign str to W'),
        ((1, 2.2), 'cannot assign float to W'),
        ((1.1, 2), 'cannot assign int to W'),
        ((Int(1), Int(1)), 'cannot assign test_handlers.Int to W')
    ]
)

X = TypeVar('X', str, W, T)

pytest.add_handler_test(
    'test_typevar_complex_constraints', Tuple[X, W, T], 'Tuple[X, W, T]',
    ok=[
        ('a', 1, {}),
        ('a', 2.2, {}),
        (1, 2, {}),
        (1.1, 2.2, {}),
        ([], 1, []),
        ([], 1.1, [])
    ],
    fail=[
        (('a', 'b', {}), 'cannot assign str to W'),
        ((1, 'b', {}), 'cannot assign str to W'),
        ((1.1, 'b', {}), 'cannot assign str to W'),
        (([], 'b', {}), 'cannot assign str to W'),
        (([], 1, 'a'), 'cannot assign str to T')
    ]
)
