# -*- coding: utf-8 -*-

from pytest import _, type_check_test


@type_check_test()
def test_wrapper(x: int, *args, **kwargs: type('T', (), {})) -> int:
    "Test docstring."


