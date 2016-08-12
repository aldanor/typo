# -*- coding: utf-8 -*-

import collections
import contextlib
import typing

from typing import Any, Union, Tuple, List

from typo.utils import type_name


class Codegen:
    _v_cache_seq = {list: True, tuple: True, str: True, bytes: True}
    _v_cache_mut_seq = {list: True}

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
            'rt_type_fail': self.rt_type_fail,
            'v_cache_seq': self._v_cache_seq,
            'v_cache_mut_seq': self._v_cache_mut_seq
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

    def if_not_isinstance(self, varname: str, tp: Union[type, Tuple[type, ...]]) -> None:
        if isinstance(tp, tuple):
            if len(tp) == 1:
                tp = self.ref_type(tp[0])
            else:
                tp = '({})'.format(', '.join(map(self.ref_type, tp)))
        else:
            tp = self.ref_type(tp)

        self.write_line('if not isinstance({}, {}):'.format(varname, tp))

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

    def enumerate_and_check(self, varname: str, desc: str,
                            handler: 'typo.handlers.Handler') -> None:
        var_i, var_v = self.new_var(), self.new_var()
        self.write_line('for {}, {} in enumerate({}):'.format(var_i, var_v, varname))
        with self.indent():
            handler(self, var_v, None if desc is None else
                    'item #{{{}}} of {}'.format(var_i, desc))

    def check_attrs_cached(self, varname: str, desc: str, expected: str,
                           cache: str, attrs: List[str]) -> None:
        var_t = self.new_var()
        self.write_line('{} = type({})'.format(var_t, varname))
        self.write_line('if {} in {}:'.format(var_t, cache))
        var_a = self.new_var()
        with self.indent():
            self.write_line('{} = {}[{}]'.format(var_a, cache, var_t))
        self.write_line('else:')
        with self.indent():
            conds = ['hasattr({}, "{}")'.format(varname, attr) for attr in attrs]
            self.write_line('{} = {}'.format(var_a, ' and '.join(conds)))
            self.write_line('{}[{}] = {}'.format(cache, var_t, var_a))
        self.write_line('if not {}:'.format(var_a))
        with self.indent():
            self.fail(desc, expected, varname)

    def __str__(self):
        return '\n'.join(self.lines) + '\n'
