# -*- coding: utf-8 -*-

__all__ = ('compile',)


def compile(bound):
    from typo.handlers import Handler
    return Handler(bound).compile()
