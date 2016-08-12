# -*- coding: utf-8 -*-

import inspect
import pytest


def pytest_namespace():
    return {'add_handler_test': add_handler_test}


def add_handler_test(name, bound, exp_str, ok=[], fail=[]):
    from typo.handlers import Handler

    handlers, params, ids = [], [], []
    for n, b in enumerate(bound if isinstance(bound, tuple) else [bound]):
        h = Handler(b)
        handlers.append((h, h.compile()))

        params = [('str', n, None)]
        params += [('ok', n, arg) for arg in ok]
        params += [('fail', n, arg) for arg in fail]

        ids = ['str-{}'.format(n)]
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
