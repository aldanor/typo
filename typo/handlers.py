# -*- coding: utf-8 -*-

import abc
import collections

from typing import (
    Any, Dict, List, Tuple, Union, Optional, Callable, Sequence, MutableSequence, Set,
    TypeVar, _ForwardRef
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

        # Note that it should be possible to resolve forward references since they
        # store frames in which they were declared; would require a bit more work.
        if isinstance(bound, _ForwardRef):
            raise ValueError('forward references are not currently supported: {}'.format(bound))

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
        gen = Codegen(typevars=self.typevars)
        var = gen.new_var()
        gen.write_line('def check({}):'.format(var))
        with gen.indent():
            if self.typevars:
                gen.init_typevars()
            self(gen, var, 'input')
        return gen.compile('check')

    @property
    def is_any(self) -> bool:
        return False

    @property
    def typevars(self) -> Set[type(TypeVar)]:
        return set()

    @property
    def valid_typevar_bound(self) -> bool:
        return False

    def valid_typevar_constraint(self, typevar) -> bool:
        return self.valid_typevar_bound


class SingleArgumentHandler(Handler):
    def __init__(self, bound: Any) -> None:
        super().__init__(bound)
        self.handler = Handler(self.args[0])

    @property
    def typevars(self) -> Set[type(TypeVar)]:
        return self.handler.typevars


class AnyHandler(Handler):
    def __call__(self, gen: Codegen, varname: str, desc: Optional[str]) -> None:
        gen.write_line('pass')

    def __str__(self) -> str:
        return 'Any'

    @property
    def is_any(self) -> bool:
        return True

    @property
    def valid_typevar_bound(self) -> bool:
        return True


class TypeHandler(Handler):
    def __call__(self, gen: Codegen, varname: str, desc: Optional[str]) -> None:
        gen.check_type(varname, desc, self.bound)

    def __str__(self) -> str:
        return type_name(self.bound)

    @property
    def valid_typevar_bound(self) -> bool:
        return True


class TypeVarHandler(Handler, subclass=TypeVar('')):
    def __init__(self, bound: Any) -> None:
        super().__init__(bound)

        self.type_constraints = ()
        self.typevar_constraints = []
        if self.bound.__constraints__ is not None:
            handlers = [Handler(c) for c in self.bound.__constraints__]
            for h in handlers:
                if not isinstance(h, (TypeHandler, TypeVarHandler)):
                    raise ValueError('invalid typevar constraint: {}'.format(h))
                if self.bound in h.typevars:
                    raise ValueError('recursive typevar constraint: {}'.format(h))
            self.type_constraints = tuple(h.bound for h in handlers if isinstance(h, TypeHandler))
            self.typevar_constraints = [h for h in handlers if isinstance(h, TypeVarHandler)]

        self.bound_handler = None
        if self.bound.__bound__ is not None:
            self.bound_handler = Handler(self.bound.__bound__)
            if not self.bound_handler.valid_typevar_bound:
                raise ValueError('invalid typevar bound: {}'.format(self.bound_handler))

    @property
    def has_constraints(self) -> bool:
        return bool(self.type_constraints or self.typevar_constraints)

    @property
    def has_bound(self) -> bool:
        return self.bound_handler is not None

    def __call__(self, gen: Codegen, varname: str, desc: Optional[str]) -> None:
        # TODO: don't need outer list if there are no generic unions
        # TODO: can infer when the typevar has been definitely set
        # TODO: can infer when the typevar is definitely uninitialized
        # TODO: more efficient typevar processing for sequences
        # TODO: simplify indent/write_line, make them accept fmt args
        # TODO: List, Dict, Sequence, etc should be valid bounds
        # TODO: support forward references (_ForwardRef), care about recursion
        var_i, var_tv, var_tp, var_len, var_k = gen.new_vars(5)
        index = gen.typevar_id(self.bound)
        tv = '{}[{}]'.format(var_tv, index)
        gen.write_line('{} = type({})'.format(var_tp, varname))
        gen.write_line('{} = len(tv)'.format(var_len))

        # for all possible assignments to type variables
        gen.write_line('for {}, {} in enumerate(tv):'.format(var_i, var_tv))
        with gen.indent():
            gen.write_line('{} = {} + len(tv) - {}'.format(var_k, var_i, var_len))

            # if the type variable of interest is already set in this assignment
            gen.write_line('if {} is not None:'.format(tv))
            with gen.indent():
                # check if value type matches it exactly
                gen.write_line('if {} is not {}:'.format(tv, var_tp))
                with gen.indent():
                    # if not, the assignment is inconsistent, remove it
                    gen.write_line('tv.pop({})'.format(var_k))
                # and go on to the next assignment
                gen.write_line('continue')

            # otherwise, the type variable has not been bound; first, consider
            # the case where the type variable has a specified upper bound
            if self.has_bound:
                # try to run the bound handler
                gen.write_line('try:')
                with gen.indent():
                    self.bound_handler(gen, varname, desc)
                    # if it succeeds, bind the type variable to class of the value
                    gen.write_line('{} = {}'.format(tv, var_tp))
                gen.write_line('except TypeError:')
                with gen.indent():
                    # otherwise, the assignment is inconsistent, remove it
                    gen.write_line('tv.pop({})'.format(var_k))

            # second, if the type variable has invariant constraints
            elif self.has_constraints:
                # if there are simple class constraints, check them first
                if self.type_constraints:
                    types = ', '.join(gen.ref_type(tp) for tp in self.type_constraints) + ', '
                    # if the class of the value matches one of the constraints exactly
                    gen.write_line('if {} in ({}):'.format(var_tp, types))
                    with gen.indent():
                        # then bind the type variable to the class of the value and go on
                        gen.write_line('{} = {}'.format(tv, var_tp))
                        gen.write_line('continue')

                # if there are no simple class constraints or if they are not satisfied,
                # check if there are any generic constraints
                if self.typevar_constraints:
                    # this is complicated... (somewhat similar to union type)
                    var_old_tv, var_tv_init, var_tv_res = gen.new_vars(3)
                    gen.write_line('{} = [{}]'.format(var_tv_init, var_tv))
                    gen.write_line('{} = tv'.format(var_old_tv))
                    gen.write_line('tv.pop({})'.format(var_k))
                    for handler in self.typevar_constraints:
                        gen.write_line('tv = {}'.format(var_tv_init))
                        gen.write_line('try:')
                        with gen.indent():
                            handler(gen, varname, desc)
                            gen.write_line('for {} in tv:'.format(var_tv_res))
                            with gen.indent():
                                gen.write_line('{}.insert({}, {})'
                                               .format(var_old_tv, var_k, var_tv_res))
                        gen.write_line('except TypeError:')
                        with gen.indent():
                            gen.write_line('pass')
                    gen.write_line('tv = {}'.format(var_old_tv))

                # there are no generic constraints, and simple constraints failed
                else:
                    gen.write_line('tv.pop({})'.format(var_k))

            # there are no bounds nor constraints, just bind the type variable
            else:
                gen.write_line('{} = {}'.format(tv, var_tp))

        # if the list of valid assignments is now empty, it is a fail
        gen.write_line('if not tv:')
        with gen.indent():
            gen.fail_msg(desc, 'cannot assign {{tp}} to {}'.format(self), varname)

    def __str__(self) -> str:
        return self.bound.__name__

    @property
    def typevars(self) -> Set[type(TypeVar)]:
        return {self.bound}

    @property
    def valid_typevar_bound(self) -> bool:
        # Technically, this is possible but would require a bit more codegen work. The problem
        # is that in the current implementation running the bound handler would mutate the
        # current state of typevars the first time it sees the bound, i.e. in this example:
        #     class Int(int): ...
        #     T = TypeVar('T')
        #     U = TypeVar('U', bound=T)
        # and this signature:
        #     Tuple[U, T]
        # the following input would fail:
        #     (Int(1), 2)
        # although Int is a subclass of int, this should be accepted but it's not, because
        # T is erroneously set to Int; instead it should remember that Int is now a
        # *subclass* (lower bound) for type variable T.
        return False


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

    @property
    def typevars(self) -> Set[type(TypeVar)]:
        return self.key_handler.typevars | self.value_handler.typevars


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

    @property
    def typevars(self) -> Set[type(TypeVar)]:
        return set(t for h in self.handlers for t in h.typevars)


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

    @property
    def typevars(self) -> Set[type(TypeVar)]:
        if self.ellipsis:
            return self.handler.typevars
        return set(t for h in self.handlers for t in h.typevars)


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
