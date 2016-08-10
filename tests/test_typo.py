# -*- coding: utf-8 -*-

import pytest

from typing import Any

from typo.handlers import Handler, AnyHandler, TypeHandler


def test_any():
    h = Handler(Any)
    assert isinstance(h, AnyHandler)
    c = h.compile()
    c(None)
    c([1, '2', {}])


def test_builtin_type():
    h = Handler(int)
    assert isinstance(h, TypeHandler)
    c = h.compile()
    c(1)
    pytest.raises_regexp(TypeError, 'expected int, got str', c, 'foo')


def test_user_type():
    A = type('A', (), {})
    h = Handler(A)
    assert isinstance(h, TypeHandler)
    c = h.compile()
    c(A())
    pytest.raises_regexp(TypeError, 'expected test_typo.A, got int', c, 1)
