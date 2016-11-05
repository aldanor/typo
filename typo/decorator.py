# -*- coding: utf-8 -*-

import inspect
from inspect import _ParameterKind as ParamKind

from typing import Any, Callable

from typo.codegen import Codegen
from typo.handlers import Handler


def type_check(func: Callable) -> Callable:
    # Create handlers for all annotated arguments and the return value.
    annotations = func.__annotations__
    handlers = {k: Handler(v) for k, v in annotations.items() if k != 'return'}
    return_handler = Handler(annotations.get('return', Any))

    # Generate a set of all typevars used in the function signature.
    typevars = set.union(return_handler.typevars, *(h.typevars for h in handlers.values()))

    # Store the function itself in the codegen context (wrapper closure).
    gen = Codegen(typevars=typevars)
    return_var, func_var = gen.new_vars(2)
    gen.context[func_var] = func

    # Extract function signature without type annotations -- this is because annotations
    # may contain user types, so we don't want to stringify them and instead pass the
    # annotations dict to the wrapped function as is.
    func.__annotations__ = {}
    signature = inspect.signature(func)
    func.__annotations__ = annotations

    gen.write_line('def {}{}:'.format(func.__name__, str(signature)))
    with gen.indent():
        for arg, handler in handlers.items():
            handler(gen, arg, '`{}`'.format(arg))
        arg_prefix = {ParamKind.POSITIONAL_ONLY: '*', ParamKind.VAR_KEYWORD: '**'}
        call_args = ', '.join(arg_prefix.get(param.kind, arg + '=') + arg
                              for arg, param in signature.parameters.items())
        gen.write_line('{} = {}({})'.format(return_var, func_var, call_args))
        return_handler(gen, return_var, 'return value')
        gen.write_line('return {}'.format(return_var))

    # Compile the wrapper, reattach the docstring and type annotations.
    wrapped = gen.compile(func.__name__)
    wrapped.generated_code = str(gen)
    wrapped.__annotations__ = annotations
    wrapped.__doc__ = func.__doc__

    return wrapped
