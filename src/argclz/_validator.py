from __future__ import annotations

from typing import get_origin, TYPE_CHECKING

from .validator import ValidatorBuilder, LambdaValidator, ValidatorFailError, AbstractTypeValidatorBuilder

__all__ = ['validator', 'validate']

if TYPE_CHECKING:
    from typing import Any, TypeAlias, Self
    from collections.abc import Callable

    Method: TypeAlias = Callable[[Any, Any], bool]
    Decorator: TypeAlias = Callable[[Method], Method]

validator = ValidatorBuilder()


def validate(*arg: Any) -> Decorator:
    """
    A decorator to add additional predicate as arguments' validator.

    >>> class Opt:
    ...     a: str = argument('-a')
    ...     @validate(a)
    ...     def check_a(self, value: str): return True

    :param arg:
    :return:
    """
    import inspect
    from pathlib import Path
    from .core import Argument

    if any([not isinstance(it, Argument) for it in arg]):
        raise TypeError('Not an argument')

    def _validate_decorator(f: Method) -> Method:
        s = inspect.signature(f)
        if len(s.parameters) != 2:
            raise RuntimeError(f"the signature of validate method '{f.__name__}' not (self, value)")

        self_name, p_name = s.parameters
        p = s.parameters[p_name]
        p_type = p.annotation
        v = None
        if p_type is inspect.Parameter.empty or p_type is str:
            v = validator.str
        elif p_type is int:
            v = validator.int
        elif p_type is float:
            v = validator.float
        elif p_type is Path:
            v = validator.path
        else:
            p_type = get_origin(p_type)
            if p_type is tuple:
                v = validator.tuple()
            elif p_type is list:
                v = validator.list()
            elif p_type is dict:
                v = validator.dict()

        if v is None:
            v = MethodValidator(f)
        else:
            assert isinstance(v, AbstractTypeValidatorBuilder)
            v._add(MethodValidator(f))

        for a in arg:
            if a.validator is None:
                a.validator = v.freeze()
            else:
                a.validator = validator.all(a.validator, v)

        return f

    return _validate_decorator


class MethodValidator(LambdaValidator):
    def __init__(self, method: Method):
        super().__init__(self, None)
        self._method = method

    def freeze(self) -> Self:
        return MethodValidator(self._method)

    def _call_validator(self, instance: Any, value: Any) -> bool:
        try:
            success = self._method(instance, value)
        except BaseException as e:
            raise ValidatorFailError(str(e)) from e
        else:
            if success:
                return True
            else:
                raise ValidatorFailError(f'{self._method.__name__} validation failed')
