# -*- coding: utf-8 -*-

import pytest

from typing import Any, List, Tuple, Dict


pytest.add_handler_test(
    'test_any', (Any, object), 'Any',
    [None, (1, '2', {})]
)

pytest.add_handler_test(
    'test_builtin_type', int, 'int',
    [42],
    [('foo', 'expected int, got str')]
)

A = type('A', (), {})

pytest.add_handler_test(
    'test_user_type', A, 'test_typo.A',
    [A()],
    [(A, 'expected test_typo.A, got type'),
     (42, 'expected test_typo.A, got int')]
)

pytest.add_handler_test(
    'test_list_basic', List[int], 'List[int]',
    [[], [1], [1, 2, 3]],
    [(1, 'expected list, got int'),
     ([1, 'foo', 2], 'invalid item #1.*expected int, got str')]
)

pytest.add_handler_test(
    'test_list_nested', List[List[int]], 'List[List[int]]',
    [[], [[]], [[], []], [[1, 2], [], [3]]],
    [(1, 'expected list, got int'),
     ([[], 1, []], 'invalid item #1.*expected list, got int'),
     ([[], [1, 2, [], 4]], 'invalid item #2 of item #1.*expected int, got list')]
)

pytest.add_handler_test(
    'test_list_no_typevar', (List, List[Any], List[object]), 'list',
    [[], [1, 'foo']],
    [(1, 'expected list, got int')]
)

pytest.add_handler_test(
    'test_tuple_no_ellipsis', Tuple[int, str], 'Tuple[int, str]',
    [(1, 'foo')],
    [(42, 'expected tuple, got int'),
     ((1, 2, 3), 'expected tuple of length 2, got tuple of length 3'),
     (('foo', 'bar'), 'invalid item #0.*expected int, got str'),
     ((1, 2), 'invalid item #1.*expected str, got int')]
)

pytest.add_handler_test(
    'test_tuple_ellipsis', Tuple[int, ...], 'Tuple[int, ...]',
    [(), (1,), (1, 2, 3)],
    [(42, 'expected tuple, got int'),
     ((1, 'foo'), 'invalid item #1.*expected int, got str')]
)

pytest.add_handler_test(
    'test_tuple_no_typevar', (Tuple, Tuple[Any, ...], Tuple[object, ...]), 'tuple',
    [(), (1, 'foo')],
    [(1, 'expected tuple, got int')]
)

pytest.add_handler_test(
    'test_dict_basic', Dict[int, str], 'Dict[int, str]',
    [{}, {1: 'foo', 2: 'bar'}],
    [(42, 'expected dict, got int'),
     ({1: 'foo', 2: 3}, 'invalid value at 2 of.*expected str, got int'),
     ({1: 'foo', 'bar': 'baz'}, 'invalid key of.*expected int, got str')]
)

pytest.add_handler_test(
    'test_dict_complex', Dict[Tuple[object, int], List[Dict[Any, str]]],
    'Dict[Tuple[Any, int], List[Dict[Any, str]]]',
    [{}, {('foo', 1): [{2: 'bar'}]}],
    [({('foo', 'bar'): []}, 'invalid item #1 of key of.*expected int, got str'),
     ({(1, 1): [{3: 'bar', 'baz': 2}]},
      r'invalid value at \'baz\' of item #0 of value at \(1, 1\) of.*expected str, got int')]
)

pytest.add_handler_test(
    'test_dict_no_typevar', (Dict, Dict[Any, Any], Dict[Any, object],
                             Dict[object, Any], Dict[object, object]), 'dict',
    [{}, {1: 'foo', 'bar': 2}],
    [(42, 'expected dict, got int')]
)
