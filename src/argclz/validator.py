from __future__ import annotations

import abc
import re
from collections.abc import Callable, Sequence, Iterable
from pathlib import Path
from types import EllipsisType
from typing import Any, TypeVar, Generic, final, overload, cast, TYPE_CHECKING, Literal

from typing_extensions import Self

from . import i18n

if TYPE_CHECKING:
    from .types import literal_type
    from .core import Argument

__all__ = [
    'argument_validating',
    'ValidatorFailError',
    'ValidatorFailOnTypeError',
    'ValidatorChangeValueRequest',
    'ValidatorFailOnIndexError',
    'Validator',
    'LambdaValidator',
    'ValidatorBuilder',
    'AbstractTypeValidatorBuilder',
    'StrValidatorBuilder',
    'IntValidatorBuilder',
    'FloatValidatorBuilder',
    'ListValidatorBuilder',
    'TupleValidatorBuilder',
    'DictValidatorBuilder',
    'PathValidatorBuilder',
    'ListItemValidator',
    'TupleItemValidator',
    'DictKeyValidator',
    'DictItemValidator',
    'NotValidatorBuilder',
    'OrValidatorBuilder',
    'AndValidatorBuilder',
]

T = TypeVar('T')
C = TypeVar('C')  # collection
K = TypeVar('K')  # collection key
CC = TypeVar('CC')  # collection backup


def check_import(name: str):
    try:
        return __import__(name)
    except ImportError:
        return None


@overload
def argument_validating(validator: Argument | Any, value: T, instance: Any = None) -> T:
    pass


@overload
def argument_validating(validator: Validator | Callable[[T], bool], value: T, instance: Any = None) -> T:
    pass


def argument_validating(validator, value: T, instance: Any = None) -> T:
    """
    Top level argument value validating function.

    :param instance:
    :param value: input value
    :param validator: validator.
    :return: validated input.
    :raise ValueError: when validation fail.
    """
    from .core import Argument
    if isinstance(validator, Argument):
        arg = validator
        if (validator := validator.validator) is None:
            raise RuntimeError(i18n.gettext('NoneType validator for attribute %s') % arg.attr)

    if not (isinstance(validator, Validator) or callable(validator)):
        raise TypeError(i18n.gettext('Not a callable nor validator'))

    try:
        fail = True

        while True:
            try:
                if isinstance(validator, Validator):
                    fail = not validator(instance, value)
                else:
                    fail = not validator(value)
                break
            except ValidatorChangeValueRequest as request:
                value = request.value
                continue

    except ValidatorFailError:
        raise
    except BaseException as e:
        raise ValueError(i18n.gettext('validation failed')) from e
    else:
        if fail:
            raise ValueError(i18n.gettext('validation failed'))

    return value


class ValidatorFailError(ValueError):
    """
    A special ValueError used in this module.
    """

    def __init__(self, *message: str | ValidatorFailError):
        if len(message) == 0:
            super().__init__(i18n.gettext('validation failed'))
        else:
            m = []
            for it in message:
                if isinstance(it, str):
                    m.append(it)
                elif isinstance(it, ValidatorFailError):
                    m.extend(it.args)
                else:
                    m.append(str(it))

            super().__init__(*m)


class ValidatorFailOnTypeError(ValidatorFailError):
    """
    A special ValidatorFailError that is raised when type validation failure.
    It is used for :meth:`~argclz.validator.ValidatorBuilder.any` to exclude some error message.
    """

    def __init__(self, value, expected_type, message: str = None):
        self.value = value
        self.expected_type = expected_type
        if message is None:
            name = expected_type.__name__ if isinstance(expected_type, type) else str(expected_type)
            message = i18n.gettext('not %s: %s') % (name, repr(value))
        super().__init__(message)

    def on_index(self, index: int | str | tuple[int | str, ...]):
        return ValidatorFailOnIndexError(index, self.args[0])


class ValidatorChangeValueRequest(ValidatorFailError):
    """
    A special ValidatorFailError that is used to change the input value.
    It is handled by :func:`argument_validating`.
    """

    def __init__(self, value):
        """
        :param value: new input value
        """
        self.value = value


class ValidatorFailOnIndexError(ValidatorFailError):
    """
    A special ValidatorFailError that carries the position information,
    likes index in sequence, and key in dictionary.
    """

    def __init__(self, index: int | str | tuple[int | str, ...], message: str = None):
        """

        :param index: index or key, use tuple to indicate a nested index.
        :param message: root cause message
        """
        if isinstance(index, int):
            index = (index,)
        self.index = index

        if message is None:
            message = i18n.gettext('validation failed')

        self.message = message

        if len(index) == 1:
            if isinstance(index[0], int):
                m = i18n.gettext('at index %s, %s') % (str(index[0]), message)
            else:
                m = i18n.gettext('at key %s, %s') % (str(index[0]), message)
        else:
            if all([isinstance(it, int) for it in index]):
                m = i18n.gettext('at index (%s), %s') % (', '.join(map(str, index)), message)
            else:
                m = i18n.gettext('at key (%s), %s') % (', '.join(map(str, index)), message)
        super().__init__(m)


class Validator:
    """Base class for validators used by :func:`argclz.core.argument`.

    Subclasses return ``True`` for valid values, return ``False`` for generic
    validation failure, or raise :class:`ValidatorFailError` for a failure with
    a specific message.
    """

    def __call__(self, instance: Any, value: Any) -> bool:
        """

        :param value: type-casted value.
        :return: True if *value* pass the validation.
        :raise ValueError: when *value* does not pass the validation.
            It gives fail reason.
        """
        return True

    def freeze(self) -> Self:
        """(internal use) return a copy of itself."""
        return self

    def type_caster(self) -> Callable[[str], Any] | None:
        """Return a command-line string caster associated with this validator, if any."""
        return None

    def __invert__(self) -> Validator:
        return NotValidatorBuilder(self)

    def __and__(self, validator: Callable[[Any], bool]) -> Validator:
        """``validator & validator``"""
        return AndValidatorBuilder([self, validator])

    def __or__(self, validator: Callable[[Any], bool]) -> Validator:
        """``validator | validator``"""
        return OrValidatorBuilder([self, validator])


class LambdaValidator(Validator, Generic[T]):
    """
    A simple validator that carries a failure message.
    """

    def __init__(self, validator: Validator | Callable[[T], bool],
                 message: str | Callable[[T], str] | None = None):
        """

        :param validator: callable
        :param message: failure message.
            It could be a str message that contains one ``%``-formating expression (for example: ``%s``),
            or a callable ``(T)->str``.
        """
        if validator is None:
            raise TypeError(i18n.gettext('None validator'))
        self._validator = validator
        self._message = message

    def __call__(self, instance: Any, value: Any) -> bool:
        try:
            success = self._call_validator(instance, value)
        except ValidatorFailError:
            raise
        except BaseException as e:
            if self._message is None:
                raise ValidatorFailError() from e
            else:
                raise ValidatorFailError(self.__message(value)) from e
        else:
            if success is None or success:
                return True
            elif self._message is None:
                return False
            else:
                raise ValidatorFailError(self.__message(value))

    def _call_validator(self, instance: Any, value: Any) -> bool:
        if isinstance(self._validator, Validator):
            return self._validator(instance, value)
        else:
            return self._validator(value)

    def __message(self, value):
        message = self._message
        if isinstance(message, str):
            if '%' in message:
                return message % value
            elif '{}' in message:
                return message.format(value)
            else:
                return message
        if callable(message):
            return message(value)
        return str(message)  # fallback

    def freeze(self) -> Self:
        if isinstance(validator := self._validator, Validator):
            validator = validator.freeze()

        return type(self)(validator, self._message)


_int = int
_str = str


@final
class ValidatorBuilder:
    """Factory for fluent validator builders.

    Users normally access a shared instance as ``argclz.validator``.
    """

    @property
    def str(self) -> StrValidatorBuilder:
        """a str validator"""
        return StrValidatorBuilder()

    @property
    def int(self) -> IntValidatorBuilder:
        """a int validator"""
        return IntValidatorBuilder()

    @property
    def float(self) -> FloatValidatorBuilder:
        """a float validator"""
        return FloatValidatorBuilder()

    @overload
    def tuple(self, size: _int, element_type: type[T]) -> TupleValidatorBuilder:
        pass

    @overload
    def tuple(self, *element_type: _int | EllipsisType) -> TupleValidatorBuilder:
        pass

    @overload
    def tuple(self, *element_type: type[T] | EllipsisType | None) -> TupleValidatorBuilder:
        pass

    # noinspection PyMethodMayBeStatic
    def tuple(self, *element_type) -> TupleValidatorBuilder:
        """
        A tuple validator.

        overloading element_type example:

        * ``2``: 2-length tuple
        * ``2, type``: 2-length type-tuple
        * ``type1, type2``: 2-length tuple with type1 at pos 0 and type2 at pos 1.
        * ``type1, None``: 2-length tuple with type1 at pos 0 and any type at pos 1.
        * ``type1, ...``: at-least-1-length tuple with type1 from pos 0 to remaining pos.

        """
        return TupleValidatorBuilder(element_type)

    # noinspection PyMethodMayBeStatic
    def list(self, element_type: type[T] | None = None) -> ListValidatorBuilder:
        """
        A list validator.

        :param element_type: element type.
        :return:
        """
        return ListValidatorBuilder(element_type)

    # noinspection PyMethodMayBeStatic
    def dict(self, element_type: type[T] | None = None) -> DictValidatorBuilder:
        """
        A dict validator.

        :param element_type: element type
        :return:
        """
        return DictValidatorBuilder(element_type)

    @property
    def path(self):
        """a path validator"""
        return PathValidatorBuilder()

    @classmethod
    def not_(cls, *validator: Validator | Callable[[T], bool],
             message: _str | None = None) -> Validator:
        """Return a validator that passes when the given validators fail.

        Multiple validators are combined as ``any`` before negation.

        :param validator: validators to negate.
        :param message: optional failure message used when negation fails.
        :return: negated validator.
        """
        if len(validator) == 1:
            if message is None and isinstance(ret := validator[0], NotValidatorBuilder):
                return ~ret

            return NotValidatorBuilder(validator[0], message)
        else:
            return NotValidatorBuilder(OrValidatorBuilder(validator), message)

    @classmethod
    def all(cls, *validator: Validator | Callable[[T], bool]) -> Validator:
        """
        return a validator that ensure all combined *validator* are satisfied.
        return an always-true validator if *validator* is empty.
        """
        return AndValidatorBuilder(validator)

    @classmethod
    def any(cls, *validator: Validator | Callable[[T], bool]) -> Validator:
        """
        return a validator that ensure at least one combined validator is satisfied.
        return an always-true validator if *validator* is empty.
        """
        return OrValidatorBuilder(validator)

    @classmethod
    def optional(cls) -> Validator:
        """
        return a validator that pass the validation when the value is ``None``.
        """
        return LambdaValidator(lambda it: it is None)

    @classmethod
    def non_none(cls) -> Validator:
        """Return a validator that passes when the value is not ``None``."""
        return LambdaValidator(lambda it: it is not None)

    def __call__(self, validator: Callable[[Any], bool],
                 message: _str | Callable[[Any], _str] | None = None) -> LambdaValidator:
        """
        Create a validator with a failure message.

        :param validator: callable
        :param message: failure message.
            It could be a str message that contains one %-formating expression (for example: '%s'),
            or a callable ``(T)->str``.
        :return: a validator
        """
        if isinstance(validator, LambdaValidator):
            validator = validator.freeze()
            validator._message = message
            return validator
        else:
            return LambdaValidator(validator, message)

    if check_import('numpy'):
        @classmethod
        def numpy(cls, mode: Literal['r+', 'r', None] = None):
            """Return a NumPy array validator when NumPy is installed.

            :param mode: optional memory-map mode used by NumPy-backed loading.
            """
            from ._validators import _numpy
            return _numpy.NumpyArrayValidator(mode)

        # TODO npz support?


class AbstractTypeValidatorBuilder(Validator, Generic[T]):
    """Base class for type-specific fluent validators."""

    def __init__(self, value_type: type[T] | tuple[type[T], ...] | None = None):
        self._value_type = value_type
        self._validators: list[Validator] = []
        self._allow_none = False

    def __call__(self, instance: Any, value: Any) -> bool:
        if self._check_none(value):
            return True

        # noinspection PyTypeHints
        if self._value_type is not None and not isinstance(value, self._value_type):
            raise ValidatorFailOnTypeError(value, self._value_type)

        return self._call_validators(instance, value)

    def _check_none(self, value):
        if value is None:
            if self._allow_none:
                return True
            else:
                raise ValidatorFailError(i18n.gettext('None value'))
        return False

    def _call_validators(self, instance: Any, value: Any):
        for validator in self._validators:
            if not validator(instance, value):
                return False

        return True

    def freeze(self, *args, **kwargs) -> Self:
        ret = type(self)(*args, **kwargs)
        ret._validators = [it.freeze() for it in self._validators]
        ret._allow_none = self._allow_none
        return ret

    def type_caster(self) -> Callable[[str], T] | None:
        # We return None instead of _value_type,
        # because other functions are able to handle simple case,
        # and its subclasses have duty to handle complex case.
        # We do not want to guess where 'type' is introduced.
        return None
        # return self._value_type

    @overload
    def _add(self, validator: Validator) -> None:
        pass

    @overload
    def _add(self, validator: Callable[[T], bool], message: str | Callable[[T], str] | None = None) -> None:
        pass

    def _add(self, validator, message=None):
        if not isinstance(validator, Validator):
            validator = LambdaValidator(validator, message)
        self._validators.append(validator)

    def optional(self) -> Self:
        """Allow ``None`` to pass validation."""
        self._allow_none = True
        return self


class StrValidatorBuilder(AbstractTypeValidatorBuilder[str]):
    """a str validator"""

    def __init__(self):
        super().__init__(str)

    def length_in_range(self, a: int | None, b: int | None, /) -> StrValidatorBuilder:
        """Enforce a string length range"""
        match (a, b):
            case (int(a), None):
                self._add(lambda it: a <= len(it), i18n.gettext("str length less than %d: '%%s'") % a)
            case (None, int(b)):
                self._add(lambda it: len(it) <= b, i18n.gettext("str length over %d: '%%s'") % b)
            case (int(a), int(b)):
                self._add(lambda it: a <= len(it) <= b, i18n.gettext("str length out of range [%d, %d]: '%%s'") % (a, b))
            case _:
                raise TypeError()
        return self

    def match(self, r: str | re.Pattern) -> StrValidatorBuilder:
        """Check if string matches a regular expression"""
        if isinstance(r, str):
            r = re.compile(r)

        rx: re.Pattern = r
        self._add(lambda it: rx.match(it) is not None, i18n.gettext("str does not match to r'%s': '%%s'") % r.pattern)
        return self

    def starts_with(self, prefix: str) -> StrValidatorBuilder:
        """Check if string values start with a substring"""
        self._add(lambda it: it.startswith(prefix), i18n.gettext("str does not start with '%s': '%%s'") % prefix)
        return self

    def ends_with(self, suffix: str) -> StrValidatorBuilder:
        """Check if string values end with a substring"""
        self._add(lambda it: it.endswith(suffix), i18n.gettext("str does not end with '%s': '%%s'") % suffix)
        return self

    def contains(self, *texts: str) -> StrValidatorBuilder:
        """Check if string values contain a substring"""
        if len(texts) == 0:
            raise ValueError(i18n.gettext('empty text list'))

        self._add(lambda it: any([text in it for text in texts]),
                  i18n.gettext("str does not contain one of %s: '%%s'") % repr(list(texts)))
        return self

    def one_of(self, options: Sequence[str]) -> StrValidatorBuilder:
        """Check if string is one of the allow options"""
        self._add(lambda it: it in options, i18n.gettext("str not in allowed set %s: '%%s'") % repr(list(options)))
        return self

    def upper(self, transform: bool = True) -> StrValidatorBuilder:
        """
        Check the string is in UPPER case.

        :param transform: transform the string into UPPER case instead of raising ValueError.
        :return:
        """

        def to_upper(value: str) -> bool:
            u = value.upper()
            if u == value:
                return True

            if transform:
                raise ValidatorChangeValueRequest(u)
            else:
                return False

        self._add(to_upper, i18n.gettext("not in UPPER case : '%s'"))
        return self

    def lower(self, transform: bool = True) -> StrValidatorBuilder:
        """
        Check the string is in lower case.

        :param transform: transform the string into lower case instead of raising ValueError.
        :return:
        """

        def to_lower(value: str) -> bool:
            u = value.lower()
            if u == value:
                return True

            if transform:
                raise ValidatorChangeValueRequest(u)
            else:
                return False

        self._add(to_lower, i18n.gettext("not in lower case : '%s'"))
        return self


class IntValidatorBuilder(AbstractTypeValidatorBuilder[int]):
    """An int validator"""

    def __init__(self):
        super().__init__(int)
        self._round = False

    def round(self, value: bool = True) -> Self:
        """Round the input"""
        self._round = value
        return self

    def freeze(self) -> Self:
        ret = super().freeze()
        ret._round = self._round
        return ret

    def in_range(self, a: int | None, b: int | None, /) -> IntValidatorBuilder:
        """Enforce a numeric range for int values"""
        match (a, b):
            case (int(a), None):
                self._add(lambda it: a <= it, i18n.gettext("value less than %d: %%d") % a)
            case (None, int(b)):
                self._add(lambda it: it <= b, i18n.gettext("value over %d: %%d") % b)
            case (int(a), int(b)):
                self._add(lambda it: a <= it <= b, i18n.gettext("value out of range [%d, %d]: %%d") % (a, b))
            case _:
                raise TypeError()

        return self

    def positive(self, include_zero=True):
        """Check if an int value is positive or non-negative"""
        if include_zero:
            self._add(lambda it: it >= 0, i18n.gettext('not a non-negative value : %d'))
        else:
            self._add(lambda it: it > 0, i18n.gettext('not a positive value : %d'))
        return self

    def negative(self, include_zero=True):
        """Check if an int value is negative or non-positive."""
        if include_zero:
            self._add(lambda it: it <= 0, i18n.gettext('not a non-positive value : %d'))
        else:
            self._add(lambda it: it < 0, i18n.gettext('not a negative value : %d'))
        return self

    def __call__(self, instance: Any, value: Any) -> bool:
        if self._check_none(value):
            return True

        if isinstance(value, float) and self._round:
            raise ValidatorChangeValueRequest(int(value))

        if not isinstance(value, int):
            if (np := check_import('numpy')) is not None and isinstance(value, np.integer):
                raise ValidatorChangeValueRequest(int(value))

            raise ValidatorFailOnTypeError(value, int)

        return self._call_validators(instance, value)


class FloatValidatorBuilder(AbstractTypeValidatorBuilder[float]):
    """a float validator"""

    def __init__(self):
        super().__init__((int, float))
        self._allow_nan = False

    def allow_nan(self, allow: bool = True) -> Self:
        """Allow or disallow NaN (not a number) as a valid float"""
        self._allow_nan = allow
        return self

    def freeze(self) -> Self:
        ret = super().freeze()
        ret._allow_nan = self._allow_nan
        return ret

    def in_range(self, a: float | None, b: float | None, /) -> Self:
        """Enforce an open-interval numeric range (a < value < b)"""
        a = None if a is None else float(a) if isinstance(a, (int, float)) else a
        b = None if b is None else float(b) if isinstance(b, (int, float)) else b

        match (a, b):
            case (float(a), None):
                self._add(lambda it: a < it, i18n.gettext("value less than %d: %%f") % a)
            case (None, float(b)):
                self._add(lambda it: it < b, i18n.gettext("value over %d: %%f") % b)
            case (float(a), float(b)):
                self._add(lambda it: a < it < b, i18n.gettext("value out of range (%d, %d): %%f") % (a, b))
            case _:
                raise TypeError()

        return self

    def in_range_closed(self, a: float | None, b: float | None, /) -> Self:
        """ Enforce a closed-interval numeric range (a <= value <= b)"""
        a = None if a is None else float(a) if isinstance(a, (int, float)) else a
        b = None if b is None else float(b) if isinstance(b, (int, float)) else b

        match (a, b):
            case (float(a), None):
                self._add(lambda it: a <= it, i18n.gettext("value less than %d: %%f") % a)
            case (None, float(b)):
                self._add(lambda it: it <= b, i18n.gettext("value over %d: %%f") % b)
            case (float(a), float(b)):
                self._add(lambda it: a <= it <= b, i18n.gettext("value out of range [%d, %d]: %%f") % (a, b))
            case _:
                raise TypeError()
        return self

    def positive(self, include_zero=True) -> Self:
        """Check if a float value is positive or non-negative"""
        if include_zero:
            self._add(lambda it: it >= 0, i18n.gettext('not a non-negative value: %f'))
        else:
            self._add(lambda it: it > 0, i18n.gettext('not a positive value: %f'))
        return self

    def negative(self, include_zero=True) -> Self:
        """Check if a float value is negative or non-positive"""
        if include_zero:
            self._add(lambda it: it <= 0, i18n.gettext('not a non-positive value : %f'))
        else:
            self._add(lambda it: it < 0, i18n.gettext('not a negative value : %f'))
        return self

    def __call__(self, instance: Any, value: Any) -> bool:
        if self._check_none(value):
            return True

        if isinstance(value, int):
            raise ValidatorChangeValueRequest(float(value))

        if not isinstance(value, float):
            if (np := check_import('numpy')) is not None and isinstance(value, np.floating):
                raise ValidatorChangeValueRequest(float(value))

            raise ValidatorFailOnTypeError(value, float)

        if value != value:  # is NaN
            if self._allow_nan:
                return True
            else:
                raise ValidatorFailError(i18n.gettext('NaN'))

        return self._call_validators(instance, value)


class ListValidatorBuilder(AbstractTypeValidatorBuilder[list[T]]):
    """a list validator"""

    def __init__(self, element_type: type[T] | None = None):
        if element_type is not None and not isinstance(element_type, type):
            raise TypeError(i18n.gettext('not a type: %s') % str(element_type))

        super().__init__()
        self._element_type = element_type
        self._allow_empty = True
        self._auto_casting = False

    def allow_empty(self, allow: bool = True) -> Self:
        """Allow or disallow empty lists."""
        self._allow_empty = allow
        return self

    def auto_casting(self, value: bool = True) -> Self:
        """Allow the validator try to cast input into tuple first."""
        self._auto_casting = value
        return self

    def freeze(self) -> Self:
        ret = super().freeze()
        ret._element_type = self._element_type
        ret._allow_empty = self._allow_empty
        ret._auto_casting = self._auto_casting
        return ret

    def type_caster(self) -> Callable[[str], T] | None:
        if self._element_type is not None:
            from .types import list_type
            return list_type(self._element_type)
        else:
            return None

    def length_in_range(self, a: int | None, b: int | None, /) -> Self:
        """Enforce a length range for lists"""
        match (a, b):
            case (int(a), None):
                self._add(lambda it: a <= len(it),
                          lambda it: i18n.gettext("list length less than %d: %d") % (a, len(it)))
            case (None, int(b)):
                self._add(lambda it: len(it) <= b,
                          lambda it: i18n.gettext("list length over %d: %d") % (b, len(it)))
            case (int(a), int(b)):
                self._add(lambda it: a <= len(it) <= b,
                          lambda it: i18n.gettext("list length out of range [%d, %d]: %d") % (a, b, len(it)))
            case _:
                raise TypeError()

        return self

    def on_item(self, validator: Callable[[Any], bool]) -> Self:
        """Apply an additional validator to each item in the list

        :param validator: A callable that validates each item
        """
        self._add(ListItemValidator(validator))
        return self

    def __call__(self, instance: Any, value: Any) -> bool:
        if self._check_none(value):
            return True

        if not isinstance(value, list):
            if self._auto_casting:
                raise ValidatorChangeValueRequest(list(value))
            else:
                raise ValidatorFailOnTypeError(value, list)

        if not self._allow_empty and len(value) == 0:
            raise ValidatorFailError(i18n.gettext('empty list : %s') % str(value))

        if (element_type := self._element_type) is not None:
            for i, element in enumerate(value):
                if not element_isinstance(element, element_type):
                    raise ValidatorFailOnTypeError(element, element_type).on_index(i)

        return self._call_validators(instance, value)


class TupleValidatorBuilder(AbstractTypeValidatorBuilder[tuple]):
    """a tuple validator"""

    def __init__(self, element_type: tuple[Any, ...]):
        super().__init__()

        modified_element_type: tuple[Any, ...]
        match element_type:
            case ():
                modified_element_type = (...,)
            case (int(length), ):  # exact length
                modified_element_type = (None,) * length
            case (int(length), type() as t):
                modified_element_type = (t,) * length
            case (int(length), e) if e is ...:  # at least length
                modified_element_type = (None,) * length + (...,)
            case _:
                modified_element_type = element_type

        for et in modified_element_type:
            if et is not None and et is not ... and not isinstance(et, type):
                raise TypeError(i18n.gettext('not a type: %s') % str(element_type))

        self._element_type: tuple[Any, ...] = modified_element_type
        self._auto_casting = False

    def auto_casting(self, value: bool = True) -> Self:
        """Allow the validator try to cast input into tuple first."""
        self._auto_casting = value
        return self

    def freeze(self) -> Self:
        ret = super().freeze(self._element_type)
        ret._auto_casting = self._auto_casting
        return ret

    def type_caster(self) -> Callable[[str], T] | None:
        from .types import tuple_type
        if self._element_type == (...,):
            return None
        else:
            return tuple_type(*self._element_type)

    def length_in_range(self, a: int | None, b: int | None, /) -> Self:
        """Enforce a length range for tuple.

        It only allows to be used in ``validator.tuple()`` and ``validator.tuple(...)`` forms.

        """
        if self._element_type != (...,):
            raise RuntimeError(i18n.gettext('not a vary-length tuple type'))

        match (a, b):
            case (int(a), None):
                self._add(lambda it: a <= len(it),
                          lambda it: i18n.gettext("tuple length less than %d: %d") % (a, len(it)))
            case (None, int(b)):
                self._add(lambda it: len(it) <= b,
                          lambda it: i18n.gettext("tuple length over %d: %d") % (b, len(it)))
            case (int(a), int(b)):
                self._add(lambda it: a <= len(it) <= b,
                          lambda it: i18n.gettext("tuple length out of range [%d, %d]: %d") % (a, b, len(it)))
            case _:
                raise TypeError()

        return self

    def on_item(self, item: int | list[int] | None, validator: Callable[[Any], bool]) -> Self:
        """Apply a validator to specific tuple positions

        :param item: A single index, a list of indices, or None for all indices
        :param validator: The validation callable to apply
        """
        self._add(TupleItemValidator(item, validator))
        return self

    def __call__(self, instance: Any, value: Any) -> bool:
        if self._check_none(value):
            return True

        if not isinstance(value, tuple):
            if self._auto_casting:
                raise ValidatorChangeValueRequest(tuple(value))
            else:
                raise ValidatorFailOnTypeError(value, tuple)

        if len(element_type := self._element_type) > 0:
            if element_type[-1] is ...:
                at_least_length = len(element_type) - 1
                if len(value) < at_least_length:
                    raise ValidatorFailError(i18n.gettext('length less than %d: %s') % (at_least_length, repr(value)))

                for i, e, t in zip(range(at_least_length), value, element_type):
                    if t is not None and not element_isinstance(e, t):
                        raise ValidatorFailOnTypeError(e, element_type).on_index(i)

                if at_least_length > 0:
                    if (last_element_type := element_type[at_least_length - 1]) is not None:
                        for i, e in zip(range(at_least_length, len(value)), value[at_least_length:]):
                            if not element_isinstance(e, last_element_type):
                                raise ValidatorFailOnTypeError(e, last_element_type).on_index(i)

            else:
                if len(value) != len(element_type):
                    raise ValidatorFailError(i18n.gettext('length not match to %d : %s') % (len(element_type), repr(value)))

                for i, e, t in zip(range(len(element_type)), value, element_type):
                    if t is not None and not element_isinstance(e, t):
                        raise ValidatorFailOnTypeError(e, t).on_index(i)

        return self._call_validators(instance, value)

    def _call_validators(self, instance: Any, value: Any):
        index_errors = []
        for validator in self._validators:
            if isinstance(validator, TupleItemValidator):
                try:
                    if not validator(instance, value):
                        return False
                except ValidatorChangeValueRequest:
                    raise
                except ValidatorFailError as e:
                    index_errors.append(e)

            elif not validator(instance, value):
                return False

        if len(index_errors):
            if len(index_errors) == 1:
                raise index_errors[0]
            raise ValidatorFailError(*index_errors)

        return True


class DictValidatorBuilder(AbstractTypeValidatorBuilder[dict[str, T]]):
    """a dict validator"""

    def __init__(self, element_type: type[T] | None = None):
        if element_type is not None and not isinstance(element_type, type):
            raise TypeError(i18n.gettext('not a type: %s') % str(element_type))

        super().__init__()
        self._element_type = element_type
        self._key_type: literal_type | None = None
        self._drop_key = False
        self._allow_empty = True

    def freeze(self) -> Self:
        ret = super().freeze()
        ret._element_type = self._element_type
        ret._key_type = self._key_type
        ret._drop_key = self._drop_key
        ret._allow_empty = self._allow_empty
        return ret

    def type_caster(self) -> Callable[[str], T] | None:
        from .types import dict_type
        return dict_type(self._element_type)

    def allow_empty(self, allow: bool = True) -> Self:
        """Allow or disallow empty dictionaries."""
        self._allow_empty = allow
        return self

    def allow_keys(self, keys: list[str] | None = None, *,
                   complete: bool = False,
                   case_sensitive: bool = True,
                   drop_key: bool = False) -> Self:
        """
        Set an allowing key for this dict.

        When *complete* or *case_sensitive* is ``True``, this validator will remap the key
        based on the *key*. When *drop_key* is ``True``, this validator will drop the unexpected
        keys, which they are not in the *keys*.

        :param keys: a list of str or a :class:`typing.Literal`.
            Use ``None`` to keep previous allowing keyset (to overwrite other settings).
        :param complete: enable unique prefix completion for keys.
        :param case_sensitive: match keys case-sensitively.
        :param drop_key: drop the unexpected keys (not in the *keys*)
        :return: this validator
        """
        from .types import literal_type

        if keys is None:
            if self._key_type is None:
                raise ValueError(i18n.gettext('keys not set'))
            keys = self._key_type.candidate
            if keys is None:
                raise ValueError(i18n.gettext('keys not set'))

        key_type = literal_type(keys, complete=complete, case_sensitive=case_sensitive)
        if key_type.candidate is None or len(key_type.candidate) == 0:
            raise ValueError(i18n.gettext('empty keys'))
        if key_type.optional:
            raise ValueError(i18n.gettext('None key'))  # some bad key

        if self._key_type is None:
            self._key_type = key_type
            self._drop_key = drop_key
            return self
        else:
            ret = self.freeze()
            ret._key_type = key_type
            ret._drop_key = drop_key
            return ret

    def on_key(self, validator: Callable[[str], bool]) -> Self:
        """Apply an additional validator to every key."""
        self._add(DictKeyValidator(validator))
        return self

    def on_value(self, validator: Callable[[T], bool]) -> Self:
        """Apply an additional validator to every value."""
        self._add(DictItemValidator(validator))
        return self

    def __call__(self, instance: Any, value: Any) -> bool:
        if self._check_none(value):
            return True

        if not isinstance(value, dict):
            raise ValidatorFailOnTypeError(value, dict)

        if not self._allow_empty and len(value) == 0:
            raise ValidatorFailError(i18n.gettext('empty dict: %s') % str(value))

        # check and remap keys
        if (key_type := self._key_type) is not None:
            backup = None
            for k in list(value):
                try:
                    n = key_type(k)
                except ValueError as e:
                    if self._drop_key:
                        if backup is None:
                            backup = dict(value)
                        backup.pop(k)
                    else:
                        raise ValidatorFailError(i18n.gettext("key '%s' is not allowed") % k) from e
                else:
                    assert n is not None
                    if n != k:
                        if n in value:
                            raise ValidatorFailError(i18n.gettext("duplicated key: '%s' and '%s'") % (k, n))
                        if backup is None:
                            backup = dict(value)
                        backup.pop(k)
                        backup[n] = value[k]

            if backup is not None:
                raise ValidatorChangeValueRequest(backup)

        if (element_type := self._element_type) is not None:
            for k, element in value.items():
                if not element_isinstance(element, element_type):
                    raise ValidatorFailOnTypeError(element, element_type).on_index(k)

        return self._call_validators(instance, value)


class PathValidatorBuilder(AbstractTypeValidatorBuilder[Path]):
    """a path validator"""

    def __init__(self):
        super().__init__(Path)

    def is_suffix(self, suffix: str | list[str] | tuple[str, ...]) -> Self:
        """Check path suffix or in a list of suffixes"""
        if isinstance(suffix, str):
            self._add(lambda it: it.suffix == suffix, i18n.gettext("not %s: %%s") % suffix)
        elif isinstance(suffix, (list, tuple)):
            self._add(lambda it: it.suffix in suffix, i18n.gettext("not one of %s: %%s") % list(repr(suffix)))
        else:
            raise TypeError('')

        return self

    def is_exists(self) -> Self:  # TODO rename to must_existed?
        """Check if path exists"""
        self._add(lambda it: it.exists(), i18n.gettext("path does not exist: %s"))
        return self

    def is_file(self) -> Self:
        """Check if path is a file"""
        self._add(lambda it: it.is_file(), i18n.gettext("path is not a file: %s"))
        return self

    def is_dir(self) -> Self:
        """Check if path is a directory"""
        self._add(lambda it: it.is_dir(), i18n.gettext("path is not a directory: %s"))
        return self

    def __call__(self, instance: Any, value: Any) -> bool:
        if self._check_none(value):
            return True

        if not isinstance(value, Path):
            raise ValidatorChangeValueRequest(Path(value))

        return self._call_validators(instance, value)


class CollectionElementValidatorBuilder(LambdaValidator, Generic[C, K, CC], metaclass=abc.ABCMeta):
    """Base class for validators that apply another validator to collection elements."""

    def __call__(self, instance: Any, value: Any) -> bool:
        backup = None
        index_errors = []

        for k in self._iter_coll(value):
            try:
                fail = not self._check_at(instance, value, k)
            except ValidatorChangeValueRequest as e:
                backup = self._change_at(value, k, e, backup)
                # skip this index, it will try again after we raise ValidatorChangeValueRequest
            except ValidatorFailOnIndexError as e:
                index_errors.append(ValidatorFailOnIndexError((k, *e.index), e.message))
            except ValidatorFailError as e:
                index_errors.append(ValidatorFailOnIndexError(k, str(e)))
            except BaseException as e:
                raise ValidatorFailOnIndexError(k, *e.args) from e
            else:
                if fail:
                    raise ValidatorFailOnIndexError(k, i18n.gettext('validation failed: %s') % str(value))

        if backup:
            raise ValidatorChangeValueRequest(self._freeze_changed(backup))

        if len(index_errors):
            if len(index_errors) == 1:
                raise index_errors[0]
            raise ValidatorFailError(*index_errors)

        return True

    @abc.abstractmethod
    def _iter_coll(self, value: C) -> Iterable[K]:
        pass

    @abc.abstractmethod
    def _check_at(self, instance: Any, value: C, index: K) -> bool:
        pass

    def _check_for(self, instance: Any, element: T) -> bool:
        return super().__call__(instance, element)

    @abc.abstractmethod
    def _change_at(self, value: C, index: K, e: ValidatorChangeValueRequest, backup: CC | None) -> CC:
        pass

    def _freeze_changed(self, backup: CC) -> C:
        return backup


class ListItemValidator(CollectionElementValidatorBuilder[list, int, list]):
    """Validator that applies another validator to each item in a list."""

    def __call__(self, instance: Any, value: Any) -> bool:
        assert isinstance(value, list)
        return super().__call__(instance, value)

    def _iter_coll(self, value: list) -> Iterable[K]:
        return range(len(value))

    def _check_at(self, instance, value: list, index: int) -> bool:
        return self._check_for(instance, value[index])

    def _change_at(self, value: list, index: int, e: ValidatorChangeValueRequest, backup: list | None) -> list:
        if backup is None:
            backup = list(value)
        backup[index] = e.value
        return backup


class TupleItemValidator(CollectionElementValidatorBuilder[tuple, int, list]):
    """Validator that applies another validator to selected tuple items."""

    def __init__(self, item: int | list[int] | None, validator: Callable[[Any], bool]):
        super().__init__(validator)
        self._item = item

    def __call__(self, instance: Any, value: Any) -> bool:
        assert isinstance(value, tuple)
        return super().__call__(instance, value)

    def _iter_coll(self, value: tuple) -> Iterable[int]:
        if self._item is None:
            index_seq = range(len(value))
        elif isinstance(self._item, int):
            index_seq = [self._item]
        else:
            index_seq = self._item

        return index_seq

    def _check_at(self, instance: Any, value: tuple, index: int) -> bool:
        try:
            element = value[index]
        except IndexError as e:
            raise ValidatorFailError(i18n.gettext('out of size %d') % len(value)) from e

        return self._check_for(instance, element)

    def _change_at(self, value: tuple, index: int, e: ValidatorChangeValueRequest, backup: list | None) -> list:
        if backup is None:
            backup = list(value)
        backup[index] = e.value
        return backup

    def _freeze_changed(self, backup: list) -> tuple:
        return tuple(backup)

    def freeze(self) -> Self:
        if isinstance(validator := self._validator, Validator):
            validator = validator.freeze()

        return TupleItemValidator(self._item, validator)


class DictKeyValidator(CollectionElementValidatorBuilder[dict, str, dict]):
    """Validator that applies another validator to each dictionary key."""

    def __call__(self, instance: Any, value: Any) -> bool:
        assert isinstance(value, dict)
        return super().__call__(instance, value)

    def _iter_coll(self, value: dict) -> Iterable[str]:
        return value.keys()

    def _check_at(self, instance: Any, value: dict, index: str) -> bool:
        return self._check_for(instance, index)

    def _change_at(self, value: dict, index: str, e: ValidatorChangeValueRequest, backup: dict | None) -> dict:
        if backup is None:
            backup = dict(value)

        n = str(e.value)
        if n in backup:
            raise ValidatorFailOnIndexError(index, i18n.gettext("duplicated keys: '%s'") % n) from e

        backup[n] = backup.pop(index)
        return backup


class DictItemValidator(CollectionElementValidatorBuilder[dict, str, dict]):
    """Validator that applies another validator to each dictionary value."""

    def __call__(self, instance: Any, value: Any) -> bool:
        assert isinstance(value, dict)
        return super().__call__(instance, value)

    def _iter_coll(self, value: dict) -> Iterable[str]:
        return value.keys()

    def _check_at(self, instance: Any, value: dict, index: str) -> bool:
        return self._check_for(instance, value[index])

    def _change_at(self, value: dict, index: str, e: ValidatorChangeValueRequest, backup: dict | None) -> dict:
        if backup is None:
            backup = dict(value)

        backup[index] = e.value
        return backup


class NotValidatorBuilder(LambdaValidator):
    """Validator that negates another validator."""

    def _call_validator(self, instance: Any, value: Any) -> bool:
        try:
            return not super()._call_validator(instance, value)
        except ValidatorFailError:
            return True

    def __invert__(self) -> Validator:
        validator = self._validator
        if isinstance(validator, NotValidatorBuilder):
            return validator
        else:
            return NotValidatorBuilder(self)


class OrValidatorBuilder(Validator):
    """Validator that passes when any child validator passes."""

    def __init__(self, validators: list[Callable[[Any], bool] | Validator]):
        self.__validators: list[Validator] = []
        for v in validators:
            if isinstance(v, OrValidatorBuilder):
                self.__validators.extend([it.freeze() for it in v.__validators])
            elif isinstance(v, Validator):
                self.__validators.append(v.freeze())
            else:
                self.__validators.append(LambdaValidator(v))

    def __call__(self, instance: Any, value: Any) -> bool:
        if len(self.__validators) == 0:
            return True

        coll = []
        for validator in self.__validators:
            try:
                if validator(instance, value):
                    return True
            except ValidatorChangeValueRequest:
                raise
            except ValidatorFailOnTypeError:
                pass
            except BaseException as e:
                if len(e.args):
                    coll.append(e.args[0])

        raise ValidatorFailError(*coll)

    def freeze(self) -> Self:
        return cast(Self, OrValidatorBuilder(self.__validators))

    def __and__(self, validator: Callable[[Any], bool]) -> Validator:
        return AndValidatorBuilder([self, validator])

    def __or__(self, validator: Callable[[Any], bool]) -> Validator:
        if isinstance(validator, OrValidatorBuilder):
            self.__validators.extend(validator.__validators)
        elif isinstance(validator, Validator):
            self.__validators.append(validator)
        else:
            self.__validators.append(LambdaValidator(validator))
        return self


class AndValidatorBuilder(Validator):
    """Validator that passes only when all child validators pass."""

    def __init__(self, validators: list[Callable[[Any], bool] | Validator]):
        self.__validators: list[Validator] = []
        for v in validators:
            if isinstance(v, AndValidatorBuilder):
                self.__validators.extend([it.freeze() for it in v.__validators])
            elif isinstance(v, Validator):
                self.__validators.append(v.freeze())
            else:
                self.__validators.append(LambdaValidator(v))

    def __call__(self, instance: Any, value: Any) -> bool:
        if len(self.__validators) == 0:
            return True

        for validator in self.__validators:
            if not validator(instance, value):
                raise ValidatorFailError()

        return True

    def freeze(self) -> Self:
        return cast(Self, AndValidatorBuilder(self.__validators))

    def __and__(self, validator: Callable[[Any], bool]) -> Validator:
        if isinstance(validator, AndValidatorBuilder):
            self.__validators.extend(validator.__validators)
        elif isinstance(validator, Validator):
            self.__validators.append(validator)
        else:
            self.__validators.append(LambdaValidator(validator))
        return self

    def __or__(self, validator: Callable[[Any], bool]) -> Validator:
        return OrValidatorBuilder([self, validator])


def element_isinstance(e, t) -> bool:
    return isinstance(t, type) and isinstance(e, t)
