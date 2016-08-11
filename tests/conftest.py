# -*- coding: utf-8 -*-

import inspect
import pytest


def pytest_namespace():
    return {'check_handler': check_handler}


def check_handler(name, bound, exp_type, exp_str, ok=[], fail=[]):
    from typo.handlers import Handler

    h = Handler(bound)
    c = h.compile()

    params = [('type', None), ('str', None)]
    params += [('ok', arg) for arg in ok]
    params += [('fail', arg) for arg in fail]

    ids = ['type', 'str']
    ids += ['ok{}'.format(i) for i in range(len(ok))]
    ids += ['fail{}'.format(i) for i in range(len(fail))]

    @pytest.mark.parametrize('test, arg', params, ids=ids)
    def func(test, arg):
        if test == 'type':
            assert isinstance(h, exp_type)
        elif test == 'str':
            assert str(h) == exp_str
        elif test == 'ok':
            c(arg)
        elif test == 'fail':
            arg, msg = arg
            pytest.raises_regexp(TypeError, msg, c, arg)

    inspect.stack()[1][0].f_locals[name] = func
    # print(list(inspect.stack()[1][0].f_locals))
    # globals()[name] = func
