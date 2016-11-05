# -*- coding: utf-8 -*-

from typo.decorator import type_check


def test_wrapper():
    T = type('T', (), {})

    def f(x: int, *args, **kwargs: T) -> int:
        "The docstring."

    g = type_check(f)
    for magic in ('module', 'name', 'qualname', 'doc', 'annotations'):
        attr = '__' + magic + '__'
        assert getattr(f, attr) == getattr(g, attr)

    assert isinstance(g.wrapper_code, str)
