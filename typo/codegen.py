# -*- coding: utf-8 -*-

import collections
import contextlib
import typing

from typing import Any, Union, Tuple

from typo.utils import type_name


class Codegen:
    def __init__(self):
        self.lines = []
        self.indent_level = 0
        self.next_var_id = 0
        self.next_type_id = 0
        self.types = {}
        self.context = {
            'collections': collections,
            'typing': typing,
            'rt_fail': self.rt_fail,
            'rt_type_fail': self.rt_type_fail
        }

    def compile(self, name):
        context = self.context.copy()
        exec(str(self), context)
        return context[name]

    @staticmethod
    def rt_fail(desc: str, expected: str, var: Any, got: str, **kwargs):
        raise TypeError('invalid {}: expected {}, got {}'
                        .format(desc.format(**kwargs), expected, got.format(**kwargs)))

    @staticmethod
    def rt_type_fail(desc: str, expected: str, var: Any, **kwargs):
        raise TypeError('invalid {}: expected {}, got {}'
                        .format(desc.format(**kwargs), expected, type_name(type(var))))

    def write_line(self, line):
        self.lines.append(' ' * self.indent_level * 4 + line)

    @contextlib.contextmanager
    def indent(self):
        self.indent_level += 1
        yield
        self.indent_level -= 1

    def new_var(self):
        varname = 'v_{}'.format(self.next_var_id)
        self.next_var_id += 1
        return varname

    def ref_type(self, tp):
        if tp.__module__ == 'builtins':
            return tp.__name__
        elif tp.__module__ == 'collections.abc':
            return 'collections.' + tp.__name__
        elif tp.__module__ == 'typing':
            return 'typing.' + tp.__name__
        elif tp not in self.types:
            varname = 'T_{}'.format(self.next_type_id)
            self.next_type_id += 1
            self.types[tp] = varname
            self.context[varname] = tp
        return self.types[tp]

    def fail(self, desc: str, expected: str, varname: str, got: str=None):
        if desc is None:
            self.write_line('raise TypeError')
        elif got is None:
            self.write_line('rt_type_fail("{}", "{}", {}, **locals())'
                            .format(desc, expected, varname))
        else:
            self.write_line('rt_fail("{}", "{}", {}, "{}", **locals())'
                            .format(desc, expected, varname, got))

    def if_not_isinstance(self, varname, tp):
        if isinstance(tp, tuple):
            if len(tp) == 1:
                tp = self.ref_type(tp[0])
            else:
                tp = '({})'.format(', '.join(map(self.ref_type, tp)))
        else:
            tp = self.ref_type(tp)

        self.write_line('if not isinstance({}, {}):'.format(varname, tp))

    def if_not_hasattrs(self, varname, *attrs):
        conds = ['not hasattr({}, "{}")'.format(varname, attr) for attr in attrs]
        self.write_line('if {}:'.format(' or '.join(conds)))

    def check_type(self, varname: str, desc: str, tp: Union[Tuple[type, ...], type]):
        if isinstance(tp, tuple):
            if len(tp) == 1:
                expected = type_name(tp)
            else:
                expected = ' or '.join(map(type_name, tp))
        else:
            expected = type_name(tp)

        self.if_not_isinstance(varname, tp)
        with self.indent():
            self.fail(desc, expected, varname)

    def __str__(self):
        return '\n'.join(self.lines) + '\n'
