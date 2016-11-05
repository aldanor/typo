# -*- coding: utf-8 -*-

import inspect
import functools

from typing import Any, Callable, Optional

from typo.codegen import Codegen
from typo.handlers import Handler


class KeywordArgsHandler(Handler):
    def __init__(self, bound: Any) -> None:
        super().__init__(bound)
        self.handler = Handler(bound)

    def __call__(self, gen: Codegen, varname: str, desc: Optional[str]) -> None:
        if not self.handler.is_any:
            var_k, var_v = gen.new_vars(2)
            gen.write_line('for {}, {}, in {}.items():'.format(var_k, var_v, varname))
            with gen.indent():
                self.handler(gen, var_v, None if desc is None else
                             'keyword argument `{{{}}}`'.format(var_k))

    def __str__(self) -> str:
        return 'KeywordArgs[{}]'.format(self.handler)


class PositionalArgsHandler(Handler):
    def __init__(self, bound: Any) -> None:
        super().__init__(bound)
        self.handler = Handler(bound)

    def __call__(self, gen: Codegen, varname: str, desc: Optional[str]) -> None:
        if not self.handler.is_any:
            gen.enumerate_and_check(varname, desc, self.handler)

    def __str__(self) -> str:
        return 'PositionalArgs[{}]'.format(self.handler)


def type_check(func: Callable) -> Callable:
    annotations = func.__annotations__

    # Extract function signature without type annotations -- this is because annotations
    # may contain user types, so we don't want to stringify them and instead pass the
    # annotations dict to the wrapped function as is.
    func.__annotations__ = {}
    signature = inspect.signature(func)
    func.__annotations__ = annotations

    # Build call arguments and type checking handlers for annotated arguments.
    return_handler = Handler(annotations.get('return', Any))
    call_args, handlers = [], {}
    for arg, param in signature.parameters.items():
        handler_type = Handler
        call_prefix = arg + '='
        if param.kind == inspect._VAR_KEYWORD:
            handler_type = KeywordArgsHandler
            call_prefix = '**'
        elif param.kind == inspect._VAR_POSITIONAL:
            handler_type = PositionalArgsHandler
            call_prefix = '*'
        call_args.append(call_prefix + arg)
        if arg in annotations:
            handlers[arg] = handler_type(annotations[arg])

    # Generate a set of all typevars used in the function signature.
    typevars = set.union(return_handler.typevars, *(h.typevars for h in handlers.values()))

    # Store the function itself in the codegen context (wrapper closure).
    gen = Codegen(typevars=typevars)
    return_var, func_var = gen.new_vars(2)
    gen.context[func_var] = func

    # Generate code for the function body.
    gen.write_line('def {}{}:'.format(func.__name__, str(signature)))
    with gen.indent():
        for arg in signature.parameters:
            if arg in handlers:
                handler = handlers[arg]
                var_desc = {
                    KeywordArgsHandler: 'keyword arguments',
                    PositionalArgsHandler: 'positional arguments'
                }.get(type(handler), '`{}`'.format(arg))
                handler(gen, arg, var_desc)
        gen.write_line('{} = {}({})'.format(return_var, func_var, ', '.join(call_args)))
        return_handler(gen, return_var, 'return value')
        gen.write_line('return {}'.format(return_var))

    # Compile the wrapper and reattach docstring, annotations, qualname, etc.
    compiled = gen.compile(func.__name__)
    wrapper = functools.wraps(func)(compiled)
    wrapper.wrapper_code = str(gen)

    return wrapper
