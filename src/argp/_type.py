from types import UnionType
from typing import TypeVar, Callable, Union, overload, Literal, get_origin, get_args, Any

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
    'caster_by_annotation',
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


def tuple_type(*value_type: Callable[[str], T] | Ellipsis):
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
        value = list(map(value_type, arg.split(split)))

        if arg.startswith('+') and prepend is not None:
            return [*prepend, *value]
        else:
            return list(value)

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


def dict_type(default: dict[str, T], value_type: Callable[[str], T] = None):
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

    @overload
    def __init__(self, candidate: type[Literal], *, complete: bool = False):
        pass

    @overload
    def __init__(self, *candidate: str, complete: bool = False):
        pass

    @overload
    def __init__(self, *, complete: bool = False):
        pass

    def __init__(self, *candidate, complete: bool = False):
        if len(candidate) == 1 and not isinstance(candidate[0], str) and get_origin(candidate[0]) == Literal:
            candidate = get_args(candidate[0])

        self.candidate = candidate
        self.complete = complete

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


def caster_by_annotation(a_name: str, a_type):
    a_type_ori = get_origin(a_type)
    if a_type == Any:
        return None
    if a_type_ori == Literal:
        return literal_type(get_args(a_type))
    elif a_type_ori == Union or a_type_ori == UnionType:
        return union_type(get_args(a_type))
    elif a_type_ori is not None and (callable(a_type_ori) or isinstance(a_type_ori, type)):
        return a_type_ori
    elif callable(a_type) or isinstance(a_type, type):
        return a_type
    else:
        raise RuntimeError(f'{a_name} {a_type}')
