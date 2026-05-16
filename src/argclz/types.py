from __future__ import annotations

from types import EllipsisType
from typing import TypeVar, Callable, Union, Literal, get_origin, get_args, Type, Any

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

    :param value: the input string to evaluate
    :return: False for ('-', '0', 'f', 'false', 'n', 'no', 'x'), True for ('', '+', '1', 't', 'true', 'yes', 'y')
    :raises ValueError: if the string is not recognized as a boolean
    """
    if not isinstance(value, str):
        raise TypeError()

    value = value.lower()
    if value in ('-', '0', 'f', 'false', 'n', 'no', 'x'):
        return False
    elif value in ('+', '1', 't', 'true', 'yes', 'y'):
        return True
    else:
        raise ValueError()


def tuple_type(*value_type: Type[T] | Callable[[str], T] | EllipsisType):
    """Create a caster that splits a comma-separated string into a tuple of typed values.

    :param value_type: converter functions for each tuple position; use ``...`` to repeat last
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
            for i, a in enumerate(arg.split(',')):
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
            value = list(map(value_type, arg[1:].split(split)))
            return [*prepend, *value]
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


class dict_type:
    """Caster that accumulates key-value pairs from 'key:value' or 'key=value' strings.
    """

    def __init__(self, value_type: Type[T] | Callable[[str], T] | None = str, default: dict[str, T] | None = None):
        """

        :param value_type: function to convert values (default: str)
        :param default: initial dict to populate (default: new dict)
        """
        if default is None:
            default = {}

        self._value_type = value_type
        self._default_dict = dict(default)
        self._current_dict: dict[str, T] | None = None

    def __call__(self, arg: str) -> dict[str, T]:
        if self._current_dict is None:
            self._current_dict = dict(self._default_dict)

        if ':' in arg:
            i = arg.index(':')
            value = arg[i + 1:]
            if self._value_type is not None:
                value = self._value_type(value)
            self._current_dict[arg[:i]] = value
        elif '=' in arg:
            i = arg.index('=')
            value = arg[i + 1:]
            if self._value_type is not None:
                value = self._value_type(value)
            self._current_dict[arg[:i]] = value
        elif self._value_type is None:
            self._current_dict[arg] = None
        else:
            self._current_dict[arg] = self._value_type("")

        return self._current_dict

    def _clone(self) -> dict_type:
        """create a copy of dict_type to avoid from sharing."""
        return dict_type(self._value_type, self._default_dict)

    def _clear(self):
        """clear current cache dict"""
        self._current_dict = None


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


def try_int_type(arg: str) -> Union[int, str, None]:
    """Attempt to convert a string to int, returning original or None on failure.

    :param arg: the input string
    :return: int if parsing succeeds, original string if fails, or None if empty"""
    if len(arg) == 0:
        return None
    try:
        return int(arg)
    except ValueError:
        return arg


def try_float_type(arg: str) -> Union[float, str, None]:
    """Attempt to convert a string to float, returning original or None on failure.

    :param arg: the input string
    :return: float if parsing succeeds, original string if fails, or None if empty"""
    if len(arg) == 0:
        return None
    try:
        return float(arg)
    except ValueError:
        return arg


class literal_type:
    """Caster enforcing membership in a set of string literals with optional prefix matching"""

    def __init__(self, candidate: Any = None, *,
                 complete: bool = False):
        self.candidate: tuple[str, ...] | None = None
        self.optional = False
        self.complete = complete

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

    def __call__(self, arg: str):
        assert self.candidate is not None
        if arg in self.candidate:
            return arg

        if len(arg) == 0 and self.optional:
            return None

        if not self.complete or len(arg) == 0:
            raise ValueError

        match [it for it in self.candidate if it.startswith(arg)]:
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
