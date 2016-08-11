# -*- coding: utf-8 -*-

import pytest

from typing import Any

from typo.handlers import AnyHandler, TypeHandler


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
