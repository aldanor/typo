# -*- coding: utf-8 -*-

import abc

from typing import Any, Dict, List, Tuple, Union, Optional, Callable

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
        origin = getattr(bound, '__origin__', None)

        bound = {
            List: list,
            Tuple: tuple
        }.get(bound, bound)

        if bound is Any:
            tp = AnyHandler
        elif origin in cls.origin_handlers:
            tp = cls.origin_handlers[origin]
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


class AnyHandler(Handler):
    def __call__(self, gen: Codegen, varname: str, desc: Optional[str]) -> None:
        gen.write_line('pass')

    def __str__(self) -> str:
        return 'Any'


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
        var_k, var_v = gen.new_var(), gen.new_var()
        gen.write_line('for {}, {} in {}.items():'.format(var_k, var_v, varname))
        with gen.indent():
            self.key_handler(gen, var_k, None if desc is None else
                             'key of {}'.format(desc))
            self.value_handler(gen, var_v, None if desc is None else
                               'value at {{{}!r}} of {}'.format(var_k, desc))

    def __str__(self) -> str:
        return 'Dict[{}, {}]'.format(self.key_handler, self.value_handler)


class ListHandler(Handler, origin=List):
    def __init__(self, bound: Any) -> None:
        super().__init__(bound)
        self.item_handler = Handler(self.args[0])

    def __call__(self, gen: Codegen, varname: str, desc: Optional[str]) -> None:
        gen.check_type(varname, desc, list)
        var_i, var_v = gen.new_var(), gen.new_var()
        gen.write_line('for {}, {} in enumerate({}):'.format(var_i, var_v, varname))
        with gen.indent():
            self.item_handler(gen, var_v, None if desc is None else
                              'item #{{{}}} of {}'.format(var_i, desc))

    def __str__(self) -> str:
        return 'List[{}]'.format(self.item_handler)


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
            self.item_handler = Handler(params[0])
        else:
            self.item_handlers = [Handler(p) for p in params]

    def __call__(self, gen: Codegen, varname: str, desc: Optional[str]) -> None:
        gen.check_type(varname, desc, tuple)
        if self.ellipsis:
            var_i, var_v = gen.new_var(), gen.new_var()
            gen.write_line('for {}, {} in enumerate({}):'
                           .format(varname, var_i, var_v))
            with gen.indent():
                self.item_handler(gen, var_v, None if desc is None else
                                  'item #{{{}}} of {}'.format(var_i, desc))
        else:
            n = len(self.item_handlers)
            var_n = gen.new_var()
            gen.write_line('{} = len({})'.format(var_n, varname))
            gen.write_line('if {} != {}:'.format(var_n, n))
            with gen.indent():
                gen.fail(desc, 'tuple of length {}'.format(n), varname,
                         got='tuple of length {{{}}}'.format(var_n))
            for i, item_handler in enumerate(self.item_handlers):
                item_handler(gen, '{}[{}]'.format(varname, i),
                             None if desc is None else 'item #{} of {}'.format(i, desc))

    def __str__(self) -> str:
        if self.ellipsis:
            return 'Tuple[{}, ...]'.format(self.item_handler)
        return 'Tuple[{}]'.format(', '.join(map(str, self.item_handlers)))
