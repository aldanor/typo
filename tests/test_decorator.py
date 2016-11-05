# -*- coding: utf-8 -*-

from pytest import _, type_check_test


@type_check_test()
def test_wrapper(x: int, *args, **kwargs: type('T', (), {})) -> int:
    "Test docstring."


@type_check_test(
    ok=[
        _(1.1)
    ],
    fail=[
        (_(1), 'invalid `x`: expected float, got int'),
        (_('foo'), 'invalid `x`: expected float, got str'),
        (_(0.), 'invalid return value: expected tuple, got float')
    ]
)
def test_basic(x: float) -> tuple:
    return (x, x) if x else x
