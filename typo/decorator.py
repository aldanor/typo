# -*- coding: utf-8 -*-

import inspect
import functools

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

    # TODO: proper handling of varargs / kwargs, like in mypy
    gen.write_line('def {}{}:'.format(func.__name__, str(signature)))
    with gen.indent():
        call_args = []
        arg_prefix = {ParamKind.POSITIONAL_ONLY: '*', ParamKind.VAR_KEYWORD: '**'}
        for arg, param in signature.parameters.items():
            if arg in handlers:
                handlers[arg](gen, arg, '`{}`'.format(arg))
            call_args.append(arg_prefix.get(param.kind, arg + '=') + arg)
        gen.write_line('{} = {}({})'.format(return_var, func_var, ', '.join(call_args)))
        return_handler(gen, return_var, 'return value')
        gen.write_line('return {}'.format(return_var))

    # Compile the wrapper and reattach docstring, annotations, qualname, etc.
    compiled = gen.compile(func.__name__)
    wrapper = functools.wraps(func)(compiled)
    wrapper.wrapper_code = str(gen)

    return wrapper
