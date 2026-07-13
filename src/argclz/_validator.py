from __future__ import annotations

import warnings
from typing import TYPE_CHECKING

from . import i18n
from .validator import argument_validating, ValidatorBuilder, Validator, ValidatorFailError, AbstractTypeValidatorBuilder

__all__ = ['validator', 'validate', 'argument_validating']

if TYPE_CHECKING:
    from typing import Any, TypeAlias, Self
    from collections.abc import Callable

    Method: TypeAlias = Callable[[Any, Any], bool]
    Decorator: TypeAlias = Callable[[Method], Method]

validator = ValidatorBuilder()
"""Default fluent validator builder. """


def validate(*arg: Any) -> Decorator:
    """
    A decorator to add additional predicate as arguments' validator.

    >>> class Opt:
    ...     a: str = argument('-a')
    ...     @validate(a)
    ...     def check_a(self, value: str):
    ...         # validating logic
    ...         return True # *value* passed the validation

    :param arg: one or more :func:`argclz.core.argument` descriptors to validate with the decorated method.
    :return: decorator that attaches the method as an assignment-time validator.
    """
    import inspect
    from pathlib import Path
    from .core import Argument

    if any([not isinstance(it, Argument) for it in arg]):
        raise TypeError(i18n.gettext('Not an argument'))

    def _validate_decorator(f: Method) -> Method:
        s = inspect.signature(f)
        if len(s.parameters) != 2:
            raise RuntimeError(i18n.gettext("the signature of validate method '%s' not (self, value)") % f.__name__)

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
                a.validator = v
            else:
                a.validator = validator.all(a.validator, v)

        return f

    return _validate_decorator


class MethodValidator(Validator):
    def __init__(self, method: Method):
        self._method = method

    def freeze(self) -> Self:
        return MethodValidator(self._method)

    def __call__(self, instance: Any, value: Any) -> bool:
        try:
            success = self._method(instance, value)
        except BaseException as e:
            raise ValidatorFailError(str(e)) from e
        else:
            if success:
                return True
            else:
                raise ValidatorFailError(i18n.gettext('%s validation failed') % self._method.__name__)
