from __future__ import annotations

import argparse
from types import UnionType
from typing import TypeVar, Union, Literal, get_origin, get_args, Any, TYPE_CHECKING

if TYPE_CHECKING:
    from .core import Argument

__all__ = ['caster_by_annotation', 'complete_arg_kwargs']

T = TypeVar('T')


def caster_by_annotation(a_name: str, a_type):
    a_type_ori = get_origin(a_type)
    if a_type == Any:
        return None

    if a_type_ori == Literal:
        from .types import literal_type
        return literal_type(get_args(a_type))

    elif a_type_ori == Union or a_type_ori == UnionType:
        a_type_args = get_args(a_type)
        if len(a_type_args) == 2 and get_origin(a_type_args[0]) is Literal and a_type_args[1] == type(None):
            from .types import literal_type
            return literal_type([*get_args(a_type_args[0]), None])

        from .types import union_type
        return union_type(*get_args(a_type))

    elif a_type_ori is not None and (callable(a_type_ori) or isinstance(a_type_ori, type)):
        return a_type_ori

    elif callable(a_type) or isinstance(a_type, type):
        return a_type

    else:
        raise RuntimeError(f'{a_name} {a_type}')


def complete_arg_kwargs(self: Argument):
    if len(self.options) == 0:  # positional argument
        if 'default' not in self.kwargs:
            self.kwargs.setdefault('nargs', '?')

    if 'type' not in self.kwargs:
        # complete bool argument for action and default
        if self.attr_type == bool:
            _complete_arg_kwargs_for_bool(self)

        if get_origin(self.attr_type) is list:
            self.kwargs.setdefault('action', 'append')
        else:
            self.kwargs.setdefault('action', 'store')

        if self.kwargs['action'] in ('store', 'store_const'):  # value type
            _complete_arg_kwargs_for_value(self)

        elif self.kwargs['action'] in ('append', 'append_const', 'extend'):  # collection type
            _complete_arg_kwargs_for_collection(self)

    if get_origin(self.attr_type) is Literal:
        _complete_arg_kwargs_for_literal(self)

    _complete_arg_kwargs_help_with_default(self)


def _complete_arg_kwargs_for_bool(self: Argument):
    assert self.attr_type == bool

    if 'default' not in self.kwargs:
        if 'nargs' in self.kwargs:
            from .types import bool_type
            self.kwargs['type'] = bool_type
            self.kwargs['action'] = 'store'
        else:
            self.kwargs.setdefault('action', 'store_true')
            self.kwargs.setdefault('default', False)

    elif self.kwargs['default']:
        self.kwargs.setdefault('action', 'store_false')
        self.kwargs.setdefault('default', True)

    else:
        self.kwargs.setdefault('action', 'store_true')
        self.kwargs.setdefault('default', False)


def _complete_arg_kwargs_for_value(self: Argument):
    a_type_ori = get_origin(self.attr_type)
    if a_type_ori == Union or a_type_ori == UnionType:
        a_type_args = get_args(self.attr_type)
        if len(a_type_args) == 2 and a_type_args[1] == type(None):
            self.kwargs.setdefault('default', None)

    self.kwargs['type'] = caster_by_annotation(self.attr, self.attr_type)


def _complete_arg_kwargs_for_collection(self: Argument):
    self.kwargs.setdefault('default', get_origin(self.attr_type)())

    a_type_arg = get_args(self.attr_type)  # Coll[T]
    if len(a_type_arg) == 0:
        # XXX what kinds of collection it is?
        raise RuntimeError()
    elif len(a_type_arg) == 1:
        self.kwargs['type'] = caster_by_annotation(self.attr, a_type_arg[0])
    else:
        raise RuntimeError()


def _complete_arg_kwargs_for_literal(self: Argument):
    assert get_origin(self.attr_type) is Literal

    from .types import literal_type
    t: literal_type | None
    if isinstance(t := self.kwargs.get('type', None), literal_type):
        t.set_candidate(self.attr_type)

    literal_values = get_args(self.attr_type)
    literal_values = [it for it in literal_values if isinstance(it, str)]

    if isinstance(t := self.kwargs.get('type', None), literal_type):
        if not t.complete:
            self.kwargs.setdefault('choices', literal_values)
    else:
        self.kwargs.setdefault('choices', literal_values)

    self.kwargs.setdefault('metavar', '|'.join(literal_values))


def _complete_arg_kwargs_help_with_default(self: Argument):
    help_text: str
    if (help_text := self.kwargs.get('help', None)) not in (None, argparse.SUPPRESS):
        if (default_value := self.kwargs.get('default', argparse.SUPPRESS)) is not argparse.SUPPRESS:
            if '{DEFAULT}' in help_text:
                text = help_text.format(DEFAULT=repr(default_value))
            else:
                text = help_text + " (default: " + repr(default_value) + ")"
            self.kwargs['help'] = text
