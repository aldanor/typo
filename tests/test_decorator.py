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


@type_check_test(
    ok=[
        _(),
        _(x=1),
        _(x=1, y=2),
    ],
    fail=[
        (_(x='foo'), 'invalid keyword argument `x`: expected int, got str'),
        (_(x=1, y=2.2), 'invalid keyword argument `y`: expected int, got float')
    ]
)
def test_kwargs(**kwargs: int):
    ...

@type_check_test(
    ok=[
        _(),
        _(1),
        _(1, 2)
    ],
    fail=[
        (_('a'), r'invalid item #0 of `\*args`: expected int, got str'),
        (_(1, 'a'), r'invalid item #1 of `\*args`: expected int, got str')
    ]
)
def test_varargs(*args: int):
    ...
