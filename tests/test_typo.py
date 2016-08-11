# -*- coding: utf-8 -*-

import pytest

from typing import Any, List

from typo.handlers import AnyHandler, TypeHandler, ListHandler


pytest.check_handler(
    'test_any', Any, AnyHandler, 'Any',
    [None, (1, '2', {})]
)

pytest.check_handler(
    'test_builtin_type', int, TypeHandler, 'int',
    [42],
    [('foo', 'expected int, got str')]
)

A = type('A', (), {})

pytest.check_handler(
    'test_user_type', A, TypeHandler, 'test_typo.A',
    [A()],
    [(A, 'expected test_typo.A, got type'),
     (42, 'expected test_typo.A, got int')]
)

pytest.check_handler(
    'test_list_basic', List[int], ListHandler, 'List[int]',
    [[], [1], [1, 2, 3]],
    [(1, 'expected list, got int'),
     ([1, 'foo', 2], 'invalid item #1.*expected int, got str')]
)
