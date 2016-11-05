# -*- coding: utf-8 -*-

import inspect
import pytest


def pytest_namespace():
    return {'add_handler_test': add_handler_test,
            'type_check_test': type_check_test,
            '_': _}


def add_handler_test(name, bound, exp_str, ok=[], fail=[]):
    from typo.handlers import Handler

    handlers, params, ids = [], [], []
    for n, b in enumerate(bound if isinstance(bound, tuple) else [bound]):
        h = Handler(b)
        handlers.append((h, h.compile()))

        params += [('str', n, None)]
        params += [('ok', n, arg) for arg in ok]
        params += [('fail', n, arg) for arg in fail]

        ids += ['str-{}'.format(n)]
        ids += ['ok-{}-{}'.format(n, i) for i in range(len(ok))]
        ids += ['fail-{}-{}'.format(n, i) for i in range(len(fail))]

    @pytest.mark.parametrize('test, n, arg', params, ids=ids)
    def func(test, n, arg):
        h, f = handlers[n]
        if test == 'str':
            assert str(h) == exp_str
        elif test == 'ok':
            f(arg)
        elif test == 'fail':
            arg, msg = arg
            pytest.raises_regexp(TypeError, msg, f, arg)

    inspect.stack()[1][0].f_locals[name] = func


class _:
    def __init__(self, *args, **kwargs):
        self.args = args
        self.kwargs = kwargs

    def apply(self, func):
        return func(*self.args, **self.kwargs)


def type_check_test(ok=[], fail=[]):
    from typo.decorator import type_check

    params, ids = [], []

    params += [('func', None)]
    params += [('ok', arg) for arg in ok]
    params += [('fail', arg) for arg in fail]

    ids += ['func']
    ids += ['ok-{}'.format(i) for i in range(len(ok))]
    ids += ['fail-{}'.format(i) for i in range(len(fail))]

    def decorator(func):
        wrapped = type_check(func)

        @pytest.mark.parametrize('test, arg', params, ids=ids)
        def test_runner(test, arg):
            if test == 'func':
                for magic in ('module', 'name', 'qualname', 'doc', 'annotations'):
                    attr = '__' + magic + '__'
                    assert getattr(func, attr) == getattr(wrapped, attr)
                assert isinstance(wrapped.wrapper_code, str)
            elif test == 'ok':
                arg.apply(wrapped)
            elif test == 'fail':
                arg, msg = arg
                pytest.raises_regexp(TypeError, msg, arg.apply, wrapped)

        test_runner.__name__ == func.__name__
        return test_runner

    return decorator
