# -*- coding: utf-8 -*-

import abc
import collections

from typing import (
    Any, Dict, List, Tuple, Union, Optional, Callable, Sequence, MutableSequence, Set
)

from typo.codegen import Codegen
from typo.utils import type_name


class HandlerMeta(abc.ABCMeta):
    origin_handlers = {}
    subclass_handlers = {}

    def __new__(meta, name, bases, ns, *, origin=None, subclass=None):
        cls = super().__new__(meta, name, bases, ns)
        if origin is not None:
            meta.origin_handlers[origin] = cls
        elif subclass is not None:
            meta.subclass_handlers[type(subclass)] = cls
        return cls

    def __init__(self, name, bases, ns, **kwargs):
        super().__init__(name, bases, ns)

    def __call__(cls, bound: Any) -> None:
        bound = {
            Tuple: Tuple[Any, ...],
            collections.Sequence: Sequence,
            collections.MutableSequence: MutableSequence
        }.get(bound, bound)

        origin = getattr(bound, '__origin__', None)

        if bound in (object, Any):
            tp = AnyHandler
        elif origin in cls.origin_handlers:
            tp = cls.origin_handlers[origin]
        elif bound in cls.origin_handlers:
            tp = cls.origin_handlers[bound]
            bound = bound[(Any,) * len(bound.__parameters__)]
        elif type(bound) in cls.subclass_handlers:
            tp = cls.subclass_handlers[type(bound)]
        elif isinstance(bound, type):
            tp = TypeHandler
        else:
            raise TypeError('invalid type annotation: {!r}'.format(bound))

        instance = object.__new__(tp)
        instance.__init__(bound)
        return instance


class Handler(metaclass=HandlerMeta):
    def __init__(self, bound: Any) -> None:
        self.bound = bound

    @abc.abstractmethod
    def __call__(self, gen: Codegen, varname: str, desc: Optional[str]) -> None:
        pass

    @abc.abstractmethod
    def __str__(self) -> str:
        pass

    @property
    def args(self) -> Tuple[Any, ...]:
        if hasattr(self.bound, '__args__'):
            return self.bound.__args__
        return self.bound.__parameters__

    def compile(self) -> Callable[[Any], None]:
        gen = Codegen()
        var = gen.new_var()
        gen.write_line('def check({}):'.format(var))
        with gen.indent():
            self(gen, var, 'input')
        return gen.compile('check')

    @property
    def is_any(self):
        return False


class SingleArgumentHandler(Handler):
    def __init__(self, bound: Any) -> None:
        super().__init__(bound)
        self.handler = Handler(self.args[0])


class AnyHandler(Handler):
    def __call__(self, gen: Codegen, varname: str, desc: Optional[str]) -> None:
        gen.write_line('pass')

    def __str__(self) -> str:
        return 'Any'

    @property
    def is_any(self):
        return True


class TypeHandler(Handler):
    def __call__(self, gen: Codegen, varname: str, desc: Optional[str]) -> None:
        gen.check_type(varname, desc, self.bound)

    def __str__(self) -> str:
        return type_name(self.bound)


class DictHandler(Handler, origin=Dict):
    def __init__(self, bound: Any) -> None:
        super().__init__(bound)
        self.key_handler = Handler(self.args[0])
        self.value_handler = Handler(self.args[1])

    def __call__(self, gen: Codegen, varname: str, desc: Optional[str]) -> None:
        gen.check_type(varname, desc, dict)
        if not self.key_handler.is_any or not self.value_handler.is_any:
            var_k, var_v = gen.new_var(), gen.new_var()
            gen.write_line('for {}, {} in {}.items():'.format(var_k, var_v, varname))
            with gen.indent():
                self.key_handler(gen, var_k, None if desc is None else
                                 'key of {}'.format(desc))
                self.value_handler(gen, var_v, None if desc is None else
                                   'value at {{{}!r}} of {}'.format(var_k, desc))

    def __str__(self) -> str:
        if self.key_handler.is_any and self.value_handler.is_any:
            return 'dict'
        return 'Dict[{}, {}]'.format(self.key_handler, self.value_handler)


class ListHandler(SingleArgumentHandler, origin=List):
    def __call__(self, gen: Codegen, varname: str, desc: Optional[str]) -> None:
        gen.check_type(varname, desc, list)
        if not self.handler.is_any:
            gen.enumerate_and_check(varname, desc, self.handler)

    def __str__(self) -> str:
        if self.handler.is_any:
            return 'list'
        return 'List[{}]'.format(self.handler)


class UnionHandler(Handler, subclass=Union):
    def __init__(self, bound: Any) -> None:
        super().__init__(bound)
        self.all_handlers = [Handler(p) for p in bound.__union_params__]
        self.handlers = [h for h in self.all_handlers
                         if not isinstance(h, (AnyHandler, TypeHandler))]
        self.types = tuple(h.bound for h in self.all_handlers
                           if isinstance(h, TypeHandler))

    def __call__(self, gen: Codegen, varname: str, desc: Optional[str]) -> None:
        if not self.handlers and not self.types:
            gen.write_line('pass')
        elif len(self.handlers) == 1 and not self.types:
            self.handlers[0](gen, varname, desc)
        elif not self.handlers and self.types:
            gen.check_type(varname, desc, self.types)
        else:
            var = gen.new_var()
            gen.write_line('{} = True'.format(var))
            handlers = self.handlers
            if self.types:
                handlers = [self.types] + handlers
            for handler in handlers:
                if isinstance(handler, tuple):
                    gen.if_not_isinstance(varname, handler)
                else:
                    gen.write_line('try:')
                    with gen.indent():
                        handler(gen, varname, None)
                    gen.write_line('except TypeError:')
                gen.indent_level += 1
            gen.write_line('{} = False'.format(var))
            gen.indent_level -= len(handlers)
            gen.write_line('if not {}:'.format(var))
            expected = '{} or {}'.format(
                ', '.join(map(str, self.all_handlers[:-1])), self.all_handlers[-1])
            with gen.indent():
                gen.fail(desc, expected, varname)

    def __str__(self) -> str:
        return 'Union[{}]'.format(', '.join(map(str, self.all__handlers)))


class TupleHandler(Handler, subclass=Tuple):
    def __init__(self, bound: Any) -> None:
        super().__init__(bound)
        params = bound.__tuple_params__
        self.ellipsis = bound.__tuple_use_ellipsis__
        if self.ellipsis:
            self.handler = Handler(params[0])
        else:
            self.handlers = [Handler(p) for p in params]

    def __call__(self, gen: Codegen, varname: str, desc: Optional[str]) -> None:
        gen.check_type(varname, desc, tuple)
        if self.ellipsis:
            gen.enumerate_and_check(varname, desc, self.handler)
        else:
            n = len(self.handlers)
            var_n = gen.new_var()
            gen.write_line('{} = len({})'.format(var_n, varname))
            gen.write_line('if {} != {}:'.format(var_n, n))
            with gen.indent():
                gen.fail(desc, 'tuple of length {}'.format(n), varname,
                         got='tuple of length {{{}}}'.format(var_n))
            for i, handler in enumerate(self.handlers):
                handler(gen, '{}[{}]'.format(varname, i),
                        None if desc is None else 'item #{} of {}'.format(i, desc))

    def __str__(self) -> str:
        if self.ellipsis:
            if self.handler.is_any:
                return 'tuple'
            return 'Tuple[{}, ...]'.format(self.handler)
        return 'Tuple[{}]'.format(', '.join(map(str, self.handlers)))


class SequenceHandler(SingleArgumentHandler, origin=Sequence):
    def __call__(self, gen: Codegen, varname: str, desc: Optional[str]) -> None:
        gen.check_attrs_cached(varname, desc, 'sequence', 'v_cache_seq',
                               ['__iter__', '__getitem__', '__len__', '__contains__'])
        if not self.handler.is_any:
            gen.enumerate_and_check(varname, desc, self.handler)

    def __str__(self) -> str:
        if self.handler.is_any:
            return 'Sequence'
        return 'Sequence[{}]'.format(self.handler)


class MutableSequenceHandler(SingleArgumentHandler, origin=MutableSequence):
    def __call__(self, gen: Codegen, varname: str, desc: Optional[str]) -> None:
        gen.check_attrs_cached(varname, desc, 'mutable sequence', 'v_cache_mut_seq',
                               ['__iter__', '__getitem__', '__len__', '__contains__',
                                '__setitem__', '__delitem__'])
        if not self.handler.is_any:
            gen.enumerate_and_check(varname, desc, self.handler)

    def __str__(self) -> str:
        if self.handler.is_any:
            return 'MutableSequence'
        return 'MutableSequence[{}]'.format(self.handler)


class SetHandler(SingleArgumentHandler, origin=Set):
    def __call__(self, gen: Codegen, varname: str, desc: Optional[str]) -> None:
        gen.check_type(varname, desc, set)
        if not self.handler.is_any:
            gen.iter_and_check(varname, desc, self.handler)

    def __str__(self) -> str:
        if self.handler.is_any:
            return 'set'
        return 'Set[{}]'.format(self.handler)
