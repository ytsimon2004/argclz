from types import EllipsisType
from typing import TypeVar, Callable, Union, Literal, get_origin, get_args

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
    value = value.lower()
    if value in ('-', '0', 'f', 'false', 'n', 'no', 'x'):
        return False
    elif value in ('', '+', '1', 't', 'true', 'yes', 'y'):
        return True
    else:
        raise ValueError()


def tuple_type(*value_type: Callable[[str], T] | EllipsisType):
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
int_tuple_type = tuple_type(int, ...)
float_tuple_type = tuple_type(float, ...)


def list_type(value_type: Callable[[str], T] = str, *, split=',', prepend: list[T] = None):
    """:attr:`arg.type` caster which convert comma ',' spread string into list.

    :param split: split character
    :param value_type: value type converter
    :param prepend: prepend list
    :return: type caster.
    """

    def _cast(arg: str) -> list[T]:
        if arg.startswith(remove := ('+' + split)) and prepend is not None:
            value = list(map(value_type, arg[len(remove):].split(split)))
            return [*prepend, *value]
        else:
            return list(map(value_type, arg.split(split)))

    return _cast


def union_type(*t: Callable[[str], T]):
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
    """Dict arg value.

    :param default: default dict content
    :param value_type: type of dict value
    :return: type converter
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
    i = arg.index(':')
    v1 = int(arg[:i])
    v2 = int(arg[i + 1:])
    return slice(v1, v2)


def try_int_type(arg: str) -> Union[int, str, None]:
    """for argparse (i.e., plane_index)"""
    if len(arg) == 0:
        return None
    try:
        return int(arg)
    except ValueError:
        return arg


def try_float_type(arg: str) -> Union[float, str, None]:
    if len(arg) == 0:
        return None
    try:
        return float(arg)
    except ValueError:
        return arg


class literal_type:

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
