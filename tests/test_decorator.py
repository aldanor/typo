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

@type_check_test(
    ok=[
        _(1),
        _(1, b='a'),
        _(1, c=1.1, d=1.2),
        _(1, b='a', c=1.1, d=1.2)
    ],
    fail=[
        (_('a'), 'invalid `a`: expected int, got str'),
        (_(1, b=1), 'invalid `b`: expected str, got int'),
        (_(1, c=1.1, d='a'), 'keyword argument `d`: expected float, got str'),
    ]
)
def test_mixed_args(a: int, *, b: str = 'foo', **kwargs: float):
    ...
