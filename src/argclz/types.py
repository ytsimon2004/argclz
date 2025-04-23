from types import EllipsisType
from typing import TypeVar, Callable, Union, Literal, get_origin, get_args, Type

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
    value = value.lower()
    if value in ('-', '0', 'f', 'false', 'n', 'no', 'x'):
        return False
    elif value in ('+', '1', 't', 'true', 'yes', 'y'):
        return True
    else:
        raise ValueError()


def tuple_type(*value_type: Type[T] | Callable[[str], T] | EllipsisType):
    """Create a caster that splits a comma-separated string into a tuple of typed values.

    :param value_type: converter functions for each tuple position; use EllipsisType to repeat last
    :return: a function that converts a comma-separated string into a typed tuple
    """
    try:
        i = value_type.index(...)
    except ValueError:
        pass
    else:
        if i == 0 or i != len(value_type) - 1:
            raise RuntimeError()

    def _type(arg: str) -> tuple[T, ...]:
        ret = []
        remain = ...
        for i, a in enumerate(arg.split(',')):
            if remain is not ...:
                ret.append(remain(a))
            else:
                t = value_type[i]
                if t is ...:
                    remain = value_type[i - 1]
                    ret.append(remain(a))
                else:
                    ret.append(t(a))

        return tuple(ret)

    return _type


str_tuple_type = tuple_type(str, ...)
"""tuple[str, ...]"""
int_tuple_type = tuple_type(int, ...)
"""tuple[int, ...]"""
float_tuple_type = tuple_type(float, ...)
"""tuple[float, ...]"""


def list_type(value_type: Type[T] | Callable[[str], T] = str, *, split=',', prepend: list[T] = None):
    """Caster which converts a delimited string into a list of typed values

    :param value_type: function to convert each element (default: str)
    :param split: delimiter character (default: ',')
    :param prepend: list of values to prepend when string starts with '+' + split
    :return: function that converts a delimited string into a list
    """

    def _cast(arg: str) -> list[T]:
        if arg.startswith(remove := ('+' + split)) and prepend is not None:
            value = list(map(value_type, arg[len(remove):].split(split)))
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
        raise TypeError

    return _type


def dict_type(value_type: Callable[[str], T] = str, default: dict[str, T] = None):
    """Caster that accumulates key-value pairs from 'key:value' or 'key=value' strings.

    :param value_type: function to convert values (default: str)
    :param default: initial dict to populate (default: new dict)
    :return: function that updates and returns the dict
    """
    if default is None:
        default = {}

    def _type(arg: str) -> dict[str, T]:
        if ':' in arg:
            i = arg.index(':')
            value = arg[i + 1:]
            if value_type is not None:
                value = value_type(value)
            default[arg[:i]] = value
        elif '=' in arg:
            i = arg.index('=')
            value = arg[i + 1:]
            if value_type is not None:
                value = value_type(value)
            default[arg[:i]] = value
        elif value_type is None:
            default[arg] = None
        else:
            default[arg] = value_type("")
        return default

    return _type


def slice_type(arg: str) -> slice:
    """Convert a 'start:end' string into a slice object.

    :param arg: string in 'start:end' format
    :return: slice(start, end)
    :raises ValueError: if format is invalid or parts are not integers
    """
    i = arg.index(':')
    v1 = int(arg[:i])
    v2 = int(arg[i + 1:])
    return slice(v1, v2)


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

    def __init__(self, candidate: type[Literal] | tuple[str, ...] = None, *,
                 complete: bool = False):
        self.candidate = None
        self.optional = False
        self.complete = complete

        if candidate is not None:
            self.set_candidate(candidate)

    def set_candidate(self, candidate: type[Literal] | tuple[str, ...], overwrite: bool = False):
        if get_origin(candidate) is Literal:
            candidate = get_args(candidate)

        if overwrite or self.candidate is None:
            self.optional = None in candidate
            if self.optional:
                candidate = [it for it in candidate if it is not None]

            self.candidate = tuple(candidate)

    def __call__(self, arg: str):
        if arg in self.candidate:
            return arg

        if not self.complete:
            raise ValueError

        match [it for it in self.candidate if it.startswith(arg)]:
            case []:
                raise ValueError()
            case [match]:
                return match
            case possible:
                raise ValueError(f'confused {possible}')

    def __str__(self):
        return 'Literal' + ('*' if self.complete else '') + '[' + ', '.join(self.candidate) + ']'

    __repr__ = __str__
