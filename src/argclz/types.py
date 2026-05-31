from __future__ import annotations

import argparse
from types import EllipsisType
from typing import TypeVar, Callable, Literal, get_origin, get_args, Type, Any

__all__ = [
    'literal_value_type',
    'bool_type',
    'try_int_type',
    'try_float_type',
    'int_tuple_type',
    'str_tuple_type',
    'float_tuple_type',
    'tuple_type',
    'list_type',
    'union_type',
    'dict_type',
    'slice_type',
    'literal_type',
]

T = TypeVar('T')


def literal_value_type(arg: str) -> bool | int | float | str:
    """Parse a string into its literal Python value"""
    if not isinstance(arg, str):
        raise TypeError()

    if arg.upper() == 'TRUE':
        return True
    elif arg.upper() == 'FALSE':
        return False
    try:
        return int(arg)
    except ValueError:
        pass

    try:
        return float(arg)
    except ValueError:
        pass

    return arg


def bool_type(value: str) -> bool:
    """Convert a string to a boolean.

    An attribute with a ``bool`` type implicit using ``bool_type``.

    >>> class Example:
    ...     value: bool = argument(...) # using ``type=bool_type``.

    :param value: the input string to evaluate
    :return: False for ('-', '0', 'f', 'false', 'n', 'no', 'x'), True for ('', '+', '1', 't', 'true', 'yes', 'y')
    :raises ValueError: if the string is not recognized as a boolean
    """
    if not isinstance(value, str):
        raise TypeError()

    value = value.lower()
    if value in ('-', '0', 'f', 'false', 'n', 'no', 'x', 'off', 'disable'):
        return False
    elif value in ('+', '1', 't', 'true', 'yes', 'y', 'on', 'enable'):
        return True
    else:
        raise ValueError()


def tuple_type(*value_type: Type[T] | Callable[[str], T] | EllipsisType, split: str = ','):
    """Create a caster that splits a comma-separated string into a tuple of typed values.

    :param value_type: converter functions for each tuple position; use ``...`` to repeat last
    :param split: value splitter
    :return: a function that converts a comma-separated string into a typed tuple
    """
    if len(value_type) == 0:
        raise ValueError('empty tuple')

    try:
        ellipsis_index = value_type.index(...)
    except ValueError:
        ellipsis_index = None
    else:
        if ellipsis_index == 0 or ellipsis_index != len(value_type) - 1:
            raise ValueError('`...` does not put at last.')

    def _type(arg: str) -> tuple[T, ...]:
        ret: list[T] = []

        if len(arg):
            last_type: Type[T] | Callable[[str], T] | None = None
            for i, a in enumerate(arg.split(split)):
                if last_type is not None:
                    ret.append(last_type(a))
                else:
                    try:
                        t = value_type[i]
                    except IndexError as e:
                        raise ValueError(f'not a {len(value_type)}-lengthed tuple') from e

                    if t is ...:
                        assert ellipsis_index is not None and ellipsis_index == i
                        last_type = value_type[ellipsis_index - 1]
                        ret.append(last_type(a))
                    else:
                        ret.append(t(a))

        if ellipsis_index is None:
            if len(ret) != len(value_type):
                raise ValueError(f'not a {len(value_type)}-lengthed tuple')

        return tuple(ret)

    return _type


str_tuple_type = tuple_type(str, ...)
"""tuple[str, ...]"""
int_tuple_type = tuple_type(int, ...)
"""tuple[int, ...]"""
float_tuple_type = tuple_type(float, ...)
"""tuple[float, ...]"""


def list_type(value_type: Type[T] | Callable[[str], T] = str, *, split=',', prepend: list[T] | None = None):
    """Caster which converts a delimited string into a list of typed values

    :param value_type: function to convert each element (default: str)
    :param split: delimiter character (default: ',')
    :param prepend: list of values to prepend when string starts with '+' + split
    :return: function that converts a delimited string into a list
    """
    if len(split) != 1:
        raise ValueError()

    def _cast(arg: str) -> list[T]:
        if len(arg) == 0:
            return []
        elif arg.startswith('+') and prepend is not None:
            if arg.startswith('+' + split):
                arg = arg[2:]
            else:
                arg = arg[1:]

            if len(arg):
                value = list(map(value_type, arg.split(split)))
                return [*prepend, *value]
            else:
                return list(prepend)
        else:
            return list(map(value_type, arg.split(split)))

    return _cast


def union_type(*t: Callable[[str], T]):
    """
    Caster that tries multiple converters in order until one succeeds.

    :param t: converter functions to attempt
    :return: function that returns first successful conversion
    :raises TypeError: if all converters fail
    """
    none_type = type(None)

    def _type(arg: str):
        for _t in t:
            if _t is not none_type:
                try:
                    return _t(arg)
                except (TypeError, ValueError):
                    pass
        raise ValueError

    return _type


# noinspection PyPep8Naming
class dict_type:
    """Caster that accumulates key-value pairs from 'key=value' strings.
    """

    def __init__(self, value_type: Type[T] | Callable[[str], T] | None = str, *,
                 kv_split: str = '=',
                 split: str | None = None,
                 default: dict[str, T] | None = None):
        """

        :param value_type: function to convert values (default: str)
        :param kv_split: the splitter of key and value.
        :param split: the splitter that allow dict_type accept a list of key-value pairs.
        :param default: initial dict to populate (default: new dict)
        """
        if len(kv_split) == 0:
            raise ValueError('empty kv_split')

        if split is not None:
            if len(split) == 0:
                raise ValueError('empty split')
            if split in kv_split:
                raise ValueError('split reused in kv_split')

        if default is None:
            default = {}

        self._value_type = value_type
        self._kv_split = kv_split
        self._split = split
        self._default_dict = dict(default)

    def __call__(self, arg: str) -> dict[str, T]:
        ret = dict(self._default_dict)

        if len(arg):
            if self._split is None:
                self.__add(arg, ret)
            else:
                for a in arg.split(self._split):
                    if len(a):
                        self.__add(a, ret)

        return ret

    def __add(self, arg: str, ret: dict[str, T]):
        if self._kv_split in arg:
            k, _, v = arg.partition(self._kv_split)
            if self._value_type is not None:
                v = self._value_type(v)
            ret[k] = v
        elif self._value_type is None:
            ret[arg] = None
        else:
            ret[arg] = self._value_type("")

    class Action(argparse.Action):
        def __init__(self,
                     option_strings,
                     dest: str,
                     type: dict_type,
                     required: bool = False,
                     help: str = None,
                     metavar: str | tuple[str, str] = ('Key', 'Value')):
            if not isinstance(type, dict_type):
                raise TypeError('type should be dict_type')

            self._dict_type = type

            match metavar:
                case str():
                    pass
                case (str(m_key), str(m_value)):
                    if type._split is None:
                        metavar = f'{m_key}{type._kv_split}{m_value}'
                    else:
                        metavar = f'{m_key}{type._kv_split}{m_value}{type._split}...'
                case _:
                    raise TypeError('illegal metavar')

            super().__init__(
                option_strings=option_strings,
                dest=dest,
                nargs=1,
                default={},
                required=required,
                help=help,
                metavar=metavar)

        def __call__(self,
                     parser: argparse.ArgumentParser,
                     namespace: argparse.Namespace,
                     values: str,
                     option_string: str | None = None) -> None:
            coll = getattr(namespace, self.dest, {})
            if coll is None:
                coll = {}

            coll.update(self._dict_type(values[0]))
            setattr(namespace, self.dest, coll)


def slice_type(arg: str) -> slice:
    """Convert a 'start:end' string into a slice object.

    :param arg: string in 'start:end' format
    :return: slice(start, end)
    :raises ValueError: if format is invalid or parts are not integers
    """
    start, _, remaining = arg.partition(':')
    end, _, step = remaining.partition(':')
    s = int(start) if len(start) else None
    e = int(end) if len(end) else None
    t = int(step) if len(step) else None
    return slice(s, e, t)


def try_int_type(arg: str) -> int | str | None:
    """Attempt to convert a string to int, returning original or None on failure.

    :param arg: the input string
    :return: int if parsing succeeds, original string if fails, or None if empty"""
    if len(arg) == 0:
        return None
    try:
        return int(arg)
    except ValueError:
        return arg


def try_float_type(arg: str) -> float | str | None:
    """Attempt to convert a string to float, returning original or None on failure.

    :param arg: the input string
    :return: float if parsing succeeds, original string if fails, or None if empty"""
    if len(arg) == 0:
        return None
    try:
        return float(arg)
    except ValueError:
        return arg


# noinspection PyPep8Naming
class literal_type:
    """Caster enforcing membership in a set of string literals with optional prefix matching.

    An attribute with a ``Literal`` type implicit using ``literal_type`` (no completion, case-sensitive).

    >>> class Example:
    ...     value: Literal['A', 'B', 'C'] = argument('-o') # using ``type=literal_type()``.

    If you want advance features from ``literal_type``, you do not need to repeat the restricted values.

    >>> class Example:
    ...     value: Literal['A', 'B', 'C'] = argument('-o', type=literal_type(complete=True, case_sensitive=False))

    """

    def __init__(self, candidate: Any = None, *,
                 complete: bool = False,
                 case_sensitive: bool = True):
        """

        :param candidate: restricted str literal list.
        :param complete: enable completion feature that support unique prefix matching.
        :param case_sensitive: is matching case-sensitive?
        """
        self.candidate: tuple[str, ...] | None = None
        self.optional = False
        self.complete = complete
        self.case_sensitive = case_sensitive

        if candidate is not None:
            self.set_candidate(candidate)

    def set_candidate(self, candidate: Any, force: bool = False):
        if get_origin(candidate) is Literal:
            candidate = get_args(candidate)

        for element in candidate:
            if element is not None and not isinstance(element, str):
                raise ValueError('not a str list')

        if force or self.candidate is None:
            self.optional = None in candidate
            if self.optional:
                candidate = [it for it in candidate if it is not None]

            self.candidate = tuple(candidate)

            # unique checking
            if self.case_sensitive:
                if len(candidate) != len(set(candidate)):
                    raise ValueError('candidate not unique')
            else:
                if len(candidate) != len(set([it.upper() for it in candidate])):
                    raise ValueError('candidate not unique')

    def __call__(self, arg: str) -> str | None:
        assert self.candidate is not None
        if arg in self.candidate:
            return arg

        up_arg = None
        if not self.case_sensitive:
            up_arg = arg.upper()
            found = [it for it in self.candidate if it.upper() == up_arg]
            if len(found):
                return self.__return_if_unique(arg, found)

        if len(arg) == 0 and self.optional:
            return None

        if not self.complete or len(arg) == 0:
            raise ValueError

        if self.case_sensitive:
            return self.__return_if_unique(arg, [it for it in self.candidate if it.startswith(arg)])
        else:
            assert up_arg is not None
            return self.__return_if_unique(arg, [it for it in self.candidate if it.upper().startswith(up_arg)])

    def __return_if_unique(self, arg: str, found: list[str]) -> str:
        match found:
            case []:
                raise ValueError()
            case [match]:
                return match
            case possible:
                raise ValueError(f"'{arg}' is confused for {possible}")

    def __str__(self):
        assert self.candidate is not None
        return 'Literal' + ('*' if self.complete else '') + '[' + ', '.join(self.candidate) + ']'

    __repr__ = __str__
