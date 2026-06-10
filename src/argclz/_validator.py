import inspect
from collections.abc import Callable
from typing import Any, ParamSpec, TypeVar, TypeAlias, get_origin, get_args, TYPE_CHECKING

from .validator import ValidatorBuilder

__all__ = ['validator', 'validate']

if TYPE_CHECKING:
    P = ParamSpec("P")
    R = TypeVar('R')
    F = TypeVar('F', bound=Callable)
    Method: TypeAlias = Callable[P, R]
    Decorator: TypeAlias = Callable[[Method], Method]

validator = ValidatorBuilder()


def validate(arg: Any) -> Decorator:
    from .core import Argument

    if not isinstance(arg, Argument):
        raise TypeError('Not an argument')

    # arg = cast(Argument, arg)
    if arg.validator is not None:
        raise RuntimeError('Argument already has a validator')

    def _validate_decorator(f: Method) -> Method:
        s = inspect.signature(f)
        if len(s.parameters) != 2:
            raise RuntimeError(f"the signature of validate method '{f.__name__}' not (self, value)")

        self_name, p_name = s.parameters
        p = s.parameters[p_name]
        p_type = p.annotation
        if p_type is inspect.Parameter.empty or p_type is str:
            arg.validator = validator.str
        elif p_type is int:
            arg.validator = validator.int
        elif p_type is float:
            arg.validator = validator.float
        else:
            p_type = get_origin(p_type)
            if p_type is tuple:
                arg.validator = validator.tuple(*get_args(p.annotation))
            elif p_type is list:
                e_type = get_args(p.annotation)[0]
                arg.validator = validator.list(e_type)
            elif p_type is dict:
                k_type, e_type = get_args(p.annotation)
                if k_type is not str:
                    raise RuntimeError(f"the parameter type of validate method '{f.__name__}': dict key type not str")
                arg.validator = validator.dict(e_type)
            else:
                raise RuntimeError(f"unknown support parameter type for validate method '{f.__name__}'")

        arg.validator._add(f)

        return f

    return _validate_decorator
