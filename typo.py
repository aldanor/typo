# -*- coding: utf-8 -*-

from abc import ABCMeta, abstractmethod
import collections
from typing import Any, Dict, List, Union, Tuple, Callable

NameType = Union[str, Callable[[Any], str]]


def type_name(tp: type) -> str:
    if tp.__module__ in ('builtins', 'abc', 'typing'):
        return tp.__name__
    return tp.__module__ + '.' + getattr(tp, '__qualname__', tp.__name__)


class HandlerMeta(ABCMeta):
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

    def __call__(cls, name: NameType, bound) -> None:
        origin = getattr(bound, '__origin__', None)

        if bound is Any:
            tp = AnyHandler
        elif origin in cls.origin_handlers:
            tp = cls.origin_handlers[origin]
        elif type(bound) in cls.subclass_handlers:
            tp = cls.subclass_handlers[type(bound)]
        elif isinstance(bound, type):
            tp = TypeHandler
        else:
            raise TypeError('invalid type annotation: {!r}'.format(tp))

        instance = object.__new__(tp)
        instance.__init__(name, bound)
        return instance


class Handler(metaclass=HandlerMeta):
    def __init__(self, name: NameType, bound) -> None:
        self.name = name if isinstance(name, collections.Callable) else lambda: name
        self.bound = bound

    @abstractmethod
    def __call__(self, value, *args) -> None:
        pass

    @abstractmethod
    def __str__(self) -> str:
        pass

    @property
    def args(self) -> Tuple:
        if hasattr(self.bound, '__args__'):
            return self.bound.__args__
        return self.bound.__parameters__

    def check_type(self, value, tp, *args) -> None:
        if not isinstance(value, tp):
            self.fail('wrong type for {name}: expected {}, got {}',
                      type_name(tp), type_name(type(value)), args=args)

    def fail(self, msg, *fmt, args=()) -> None:
        raise TypeError(msg.format(*fmt, name=self.name(*args)))


class AnyHandler(Handler):
    def __call__(self, value, *args) -> None:
        pass

    def __str__(self):
        return 'Any'


class TypeHandler(Handler):
    def __call__(self, value, *args) -> None:
        self.check_type(value, self.bound, *args)

    def __str__(self):
        return type_name(self.bound)


class DictHandler(Handler, origin=Dict):
    def __init__(self, name: NameType, bound) -> None:
        super().__init__(name, bound)
        k, v = self.args
        self.key_handler = Handler(
            lambda *args: 'dict key of {}'.format(self.name(*args)), k)
        self.value_handler = Handler(
            lambda k, *args: 'dict value at {!r} of {}'.format(k, self.name(*args)), v)

    def __call__(self, value, *args) -> None:
        self.check_type(value, dict, *args)
        for k, v in value.items():
            self.key_handler(k, *args)
            self.value_handler(v, k, *args)

    def __str__(self):
        return 'Dict[{}, {}]'.format(self.key_handler, self.value_handler)


class ListHandler(Handler, origin=List):
    def __init__(self, name: NameType, bound) -> None:
        super().__init__(name, bound)
        self.item_handler = Handler(lambda i, *args:
                                    'list item #{} of {}'.format(i, self.name(*args)), self.args[0])

    def __call__(self, value, *args) -> None:
        self.check_type(value, list, *args)
        for i, item in enumerate(value):
            self.item_handler(item, i, *args)

    def __str__(self):
        return 'List[{}]'.format(self.item_handler)


class UnionHandler(Handler, subclass=Union):
    def __init__(self, name: NameType, bound) -> None:
        super().__init__(name, bound)
        self.handlers = [Handler(self.name, p) for p in bound.__union_params__]

    def __call__(self, value, *args) -> None:
        for handler in self.handlers:
            try:
                return handler(value, *args)
            except:
                pass
        self.fail('wrong type for {name}: expected {}, got {}',
                  self, type_name(type(value)), args=args)

    def __str__(self):
        return 'Union[{}]'.format(', '.join(str(handler) for handler in self.handlers))


class TupleHandler(Handler, subclass=Tuple):
    def __init__(self, name: NameType, bound) -> None:
        super().__init__(name, bound)
        params = bound.__tuple_params__
        self.flexible = bound.__tuple_use_ellipsis__
        if self.flexible:
            self.item_handler = Handler(lambda i, *args:
                                        'tuple item #{} of {}'.format(i, self.name(*args)), params[0])
        else:
            self.item_handlers = [Handler(lambda *args:
                                          'tuple item #{} of {}'.format(i, self.name(*args)), p)
                                  for i, p in enumerate(params)]

    def __call__(self, value, *args) -> None:
        self.check_type(value, tuple, *args)
        if self.flexible:
            for i, item in enumerate(value):
                self.item_handler(item, i, *args)
        else:
            if len(value) != len(self.item_handlers):
                self.fail('wrong tuple length for {name}: expected {}, got {}',
                          len(self.item_handlers), len(value), args=args)
            for item, handler in zip(value, self.item_handlers):
                handler(item, *args)

    def __str__(self):
        if self.flexible:
            return 'Tuple[{}, ...]'.format(self.item_handler)
        return 'Tuple[{}]'.format(', '.join(map(str, self.item_handlers)))
