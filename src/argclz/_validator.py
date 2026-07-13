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

    *Limitation of parameter type hint*

    When it is a simple type (including str, int, float, Path), collection type (tuple, list, dict),
    and an optional type of above (likes `str|None`). The generated validator will do a simple type
    checking before invoking the method. Otherwise, the generated validator will pass the value to the
    method (a warning will be raised of course).

    For optional type, the ``None`` will be passed into the method.

    :param arg: one or more :func:`argclz.core.argument` descriptors to validate with the decorated method.
    :return: decorator that attaches the method (could be static or class method) as an assignment-time validator.
    """
    import inspect
    from .core import Argument

    if any([not isinstance(it, Argument) for it in arg]):
        raise TypeError(i18n.gettext('Not an argument'))

    def _validate_decorator(f: Method | staticmethod | classmethod) -> Method:
        if isinstance(f, staticmethod):
            s = inspect.signature(f)
            if len(s.parameters) != 1:
                raise RuntimeError(i18n.gettext("the signature of validate static method '%s' not (value)") % f.__name__)

            p_name, *_ = s.parameters

        elif isinstance(f, classmethod):
            s = inspect.signature(f.__func__)
            if len(s.parameters) != 2:
                raise RuntimeError(i18n.gettext("the signature of validate class method '%s' not (cls, value)") % f.__name__)

            self_name, p_name = s.parameters

        else:
            s = inspect.signature(f)
            if len(s.parameters) != 2:
                raise RuntimeError(i18n.gettext("the signature of validate method '%s' not (self, value)") % f.__name__)

            self_name, p_name = s.parameters

        p = s.parameters[p_name]
        p_type = p.annotation
        v = _para_type_to_validator(p_type)

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


def _para_type_to_validator(p_type, strict=False) -> AbstractTypeValidatorBuilder | None:
    import inspect
    from pathlib import Path
    from types import UnionType
    from typing import Any, Union, get_origin, get_args

    if p_type is inspect.Parameter.empty or p_type is Any:
        v = AbstractTypeValidatorBuilder()  # any type
        v.optional(bypass=True)
        return v
    elif p_type is str:
        return validator.str
    elif p_type is int:
        return validator.int
    elif p_type is float:
        return validator.float
    elif p_type is Path:
        return validator.path

    c_type = get_origin(p_type)
    if c_type is tuple:
        return validator.tuple()
    elif c_type is list:
        return validator.list()
    elif c_type is dict:
        return validator.dict()
    elif not strict and (c_type is UnionType or c_type is Union):
        a_types = get_args(p_type)
        if len(a_types) == 2 and type(None) in a_types:
            a_type = a_types[0] if a_types[0] != type(None) else a_types[1]
            v = _para_type_to_validator(a_type, strict=True)
            if v is not None:
                v.optional(bypass=True)
            return v

    if not strict:
        warnings.warn(i18n.gettext('Unsupported parameter type : %s') % str(p_type), RuntimeWarning)

    return None


class MethodValidator(Validator):
    def __init__(self, method: Method):
        self._method = method

    def freeze(self) -> Self:
        return MethodValidator(self._method)

    def __call__(self, instance: Any, value: Any) -> bool:
        try:
            if isinstance(self._method, staticmethod):
                success = self._method(value)
            elif isinstance(self._method, classmethod):
                if instance is None:
                    success = self._method.__func__(None, value)
                else:
                    success = self._method(type(instance), value)
            else:
                success = self._method(instance, value)
        except BaseException as e:
            raise ValidatorFailError(str(e)) from e
        else:
            if success:
                return True
            else:
                raise ValidatorFailError(i18n.gettext('%s validation failed') % self._method.__name__)
