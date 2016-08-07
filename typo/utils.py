# -*- coding: utf-8 -*-


def type_name(tp: type) -> str:
    if tp.__module__ in ('builtins', 'abc', 'typing'):
        return tp.__name__
    return tp.__module__ + '.' + getattr(tp, '__qualname__', tp.__name__)
