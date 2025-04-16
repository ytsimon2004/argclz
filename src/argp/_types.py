from types import UnionType
from typing import TypeVar, Union, Literal, get_origin, get_args, Any

__all__ = [
    'caster_by_annotation',
]

T = TypeVar('T')


def caster_by_annotation(a_name: str, a_type):
    a_type_ori = get_origin(a_type)
    if a_type == Any:
        return None

    if a_type_ori == Literal:
        from .types import literal_type
        return literal_type(*get_args(a_type))

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
