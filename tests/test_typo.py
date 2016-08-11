# -*- coding: utf-8 -*-

import pytest

from typing import Any, List


pytest.add_handler_test(
    'test_any', Any, 'Any',
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
