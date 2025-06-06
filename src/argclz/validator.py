from __future__ import annotations

import re
from collections.abc import Callable
from pathlib import Path
from typing import Any, TypeVar, Generic, final, overload, Collection

from typing_extensions import Self

T = TypeVar('T')


class ValidatorFailError(ValueError):
    """
    A special ValueError used in this module.
    """
    pass


class ValidatorFailOnTypeError(ValidatorFailError):
    """
    A special ValidatorFailError that is raised when type validation failure.
    It is used for :meth:`~argclz.validator.ValidatorBuilder.any()` to exclude some error message.
    """
    pass


class Validator:
    def __call__(self, value: Any) -> bool:
        """

        :param value: type-casted value.
        :return: True if *value* pass the validation.
        :raise ValueError: when *value* does not pass the validation.
        """
        return True

    def freeze(self) -> Self:
        """(internal use) return a copy of itself."""
        return self

    # TODO add feature? auto-casting, for example: (str|Path)->Path


class LambdaValidator(Validator, Generic[T]):
    """
    A simple validator that carries a failure message.
    """

    def __init__(self, validator: Callable[[T], bool],
                 message: str | Callable[[T], str] = None):
        """

        :param validator: callable
        :param message: failure message.
            It could be a str message that contains one %-formating expression (for example: '%s'),
            or a callable ``(T)->str``.
        """
        if isinstance(message, str):
            message = message.__mod__

        self._validator = validator
        self._message = message

    def __call__(self, value: T) -> bool:
        message = self._message
        try:
            success = self._validator(value)
        except ValidatorFailError:
            raise
        except BaseException as e:
            if message is None:
                raise ValidatorFailError('validate failure') from e
            else:
                raise ValidatorFailError(message(value)) from e
        else:
            if success is None or success:
                return True
            elif message is None:
                return False
            else:
                raise ValidatorFailError(message(value))

    def __and__(self, validator: Callable[[Any], bool]) -> AndValidatorBuilder:
        """``validator & validator``"""
        return AndValidatorBuilder(self) & validator

    def __or__(self, validator: Callable[[Any], bool]) -> OrValidatorBuilder:
        """``validator | validator``"""
        return OrValidatorBuilder(self) | validator

    def freeze(self) -> Self:
        if isinstance(validator := self._validator, Validator):
            validator = validator.freeze()

        return LambdaValidator(validator, self._message)


@final
class ValidatorBuilder:
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
    def tuple(self, element_type: int) -> TupleValidatorBuilder:
        pass

    @overload
    def tuple(self, *element_type: type[T]) -> TupleValidatorBuilder:
        pass

    # noinspection PyMethodMayBeStatic
    def tuple(self, *element_type) -> TupleValidatorBuilder:
        """a tuple validator

        overloading element_type example:

        * ``2``: 2-length tuple
        * ``type1, type2``: 2-length tuple with type1 at pos 0 and type2 at pos 1.
        * ``type1, None``: 2-length tuple with type1 at pos 0 and any type at pos 1.
        * ``type1, ...``: at-least-1-length tuple with type1 from pos 0 to remaining pos.

        """
        return TupleValidatorBuilder(element_type)

    # noinspection PyMethodMayBeStatic
    def list(self, element_type: type[T] = None) -> ListValidatorBuilder:
        """
        a list validator

        :param element_type: element type.
        :return:
        """
        return ListValidatorBuilder(element_type)

    @property
    def path(self):
        """a path validator"""
        return PathValidatorBuilder()

    @classmethod
    def all(cls, *validator: Callable[[T], bool]) -> AndValidatorBuilder:
        """
        return a validator that ensure all combined *validator* are satisfied.
        return an always-true validator if *validator* is empty.
        """
        return AndValidatorBuilder(*validator)

    @classmethod
    def any(cls, *validator: Callable[[T], bool]) -> OrValidatorBuilder:
        """
        return a validator that ensure at least one combined validator is satisfied.
        return an always-true validator if *validator* is empty.
        """
        return OrValidatorBuilder(*validator)

    @classmethod
    def optional(cls) -> Validator:
        """
        return a validator that pass the validation when the value is ``None``.
        """
        return LambdaValidator(lambda it: it is None)

    @classmethod
    def non_none(cls) -> Validator:
        return LambdaValidator(lambda it: it is not None)

    def __call__(self, validator: Callable[[Any], bool],
                 message: str | Callable[[Any], str] = None) -> LambdaValidator:
        """
        Create a validator with a failure message.

        :param validator: callable
        :param message: failure message.
            It could be a str message that contains one %-formating expression (for example: '%s'),
            or a callable ``(T)->str``.
        :return: a validator
        """
        return LambdaValidator(validator, message)


class AbstractTypeValidatorBuilder(Validator, Generic[T]):
    def __init__(self, value_type: type[T] | tuple[type[T], ...] = None):
        self._value_type = value_type
        self._validators: list[LambdaValidator[T]] = []
        self._allow_none = False

    def __call__(self, value: Any) -> bool:
        if value is None:
            if self._allow_none:
                return True
            else:
                raise ValidatorFailError('None')

        # noinspection PyTypeHints
        if self._value_type is not None and not isinstance(value, self._value_type):
            raise ValidatorFailOnTypeError(f'not instance of {self._value_type.__name__} : {value}')

        for validator in self._validators:
            if not validator(value):
                return False

        return True

    def freeze(self, *args, **kwargs) -> Self:
        ret = type(self)(*args, **kwargs)
        ret._validators = [it.freeze() for it in self._validators]
        ret._allow_none = self._allow_none
        return ret

    @overload
    def _add(self, validator: LambdaValidator[T]):
        pass

    @overload
    def _add(self, validator: Callable[[T], bool], message: str | Callable[[T], str] = None):
        pass

    def _add(self, validator, message=None):
        if not isinstance(validator, LambdaValidator):
            validator = LambdaValidator(validator, message)
        self._validators.append(validator)

    def optional(self) -> Self:
        self._allow_none = True
        return self

    def __and__(self, validator: Callable[[Any], bool]) -> AndValidatorBuilder:
        """``validator & validator``"""
        return AndValidatorBuilder(self) & validator

    def __or__(self, validator: Callable[[Any], bool]) -> OrValidatorBuilder:
        """``validator | validator``"""
        return OrValidatorBuilder(self) | validator


class StrValidatorBuilder(AbstractTypeValidatorBuilder[str]):
    """a str validator"""

    def __init__(self):
        super().__init__(str)

    def length_in_range(self, a: int | None, b: int | None, /) -> StrValidatorBuilder:
        """Enforce a string length range"""
        match (a, b):
            case (int(a), None):
                self._add(lambda it: a <= len(it), f'str length less than {a}: "%s"')
            case (None, int(b)):
                self._add(lambda it: len(it) <= b, f'str length over {b}: "%s"')
            case (int(a), int(b)):
                self._add(lambda it: a <= len(it) <= b, f'str length out of range [{a}, {b}]: "%s"')
            case _:
                raise TypeError()
        return self

    def match(self, r: str | re.Pattern) -> StrValidatorBuilder:
        """Check if string matches a regular expression"""
        if isinstance(r, str):
            r = re.compile(r)
        self._add(lambda it: r.match(it) is not None, f'str does not match to {r.pattern} : "%s"')
        return self

    def starts_with(self, prefix: str) -> StrValidatorBuilder:
        """Check if string values start with a substring"""
        self._add(lambda it: it.startswith(prefix), f'str does not start with {prefix}: "%s"')
        return self

    def ends_with(self, suffix: str) -> StrValidatorBuilder:
        """Check if string values end with a substring"""
        self._add(lambda it: it.endswith(suffix), f'str does not end with {suffix}: "%s"')
        return self

    def contains(self, *texts: str) -> StrValidatorBuilder:
        """Check if string values contain a substring"""
        if len(texts) == 0:
            raise ValueError('empty text list')

        self._add(lambda it: any([text in it for text in texts]), f'str does not contain one of {texts}: "%s"')
        return self

    def one_of(self, options: Collection[str]) -> StrValidatorBuilder:
        """Check if string is one of the allow options"""
        self._add(lambda it: it in options, f'str not in allowed set {options}: "%s"')
        return self


class IntValidatorBuilder(AbstractTypeValidatorBuilder[int]):
    """a int validator"""

    def __init__(self):
        super().__init__(int)

    def in_range(self, a: int | None, b: int | None, /) -> IntValidatorBuilder:
        """Enforce a numeric range for int values"""
        match (a, b):
            case (int(a), None):
                self._add(lambda it: a <= it, f'value less than {a}: %d')
            case (None, int(b)):
                self._add(lambda it: it <= b, f'value over {b}: %d')
            case (int(a), int(b)):
                self._add(lambda it: a <= it <= b, f'value out of range [{a}, {b}]: %d')
            case _:
                raise TypeError()

        return self

    def positive(self, include_zero=True):
        """Check if an int value is positive or non-negative"""
        if include_zero:
            self._add(lambda it: it >= 0, 'not a non-negative value : %d')
        else:
            self._add(lambda it: it > 0, 'not a positive value : %d')
        return self

    def negative(self, include_zero=True):
        """Check if an int value is negative or non-positive."""
        if include_zero:
            self._add(lambda it: it <= 0, 'not a non-positive value : %d')
        else:
            self._add(lambda it: it < 0, 'not a negative value : %d')
        return self


class FloatValidatorBuilder(AbstractTypeValidatorBuilder[float]):
    """a float validator"""

    def __init__(self):
        super().__init__((int, float))
        self.__allow_nan = False

    def freeze(self) -> Self:
        ret = super().freeze()
        ret.__allow_nan = self.__allow_nan
        return ret

    def in_range(self, a: float | None, b: float | None, /) -> Self:
        """Enforce an open-interval numeric range (a < value < b)"""
        a = None if a is None else float(a) if isinstance(a, (int, float)) else a
        b = None if b is None else float(b) if isinstance(b, (int, float)) else b

        match (a, b):
            case (float(a), None):
                self._add(lambda it: a < it, f'value less than {a}: %f')
            case (None, float(b)):
                self._add(lambda it: it < b, f'value over {b}: %f')
            case (float(a), float(b)):
                self._add(lambda it: a < it < b, f'value out of range ({a}, {b}): %f')
            case _:
                raise TypeError()

        return self

    def in_range_closed(self, a: float | None, b: float | None, /) -> Self:
        """ Enforce a closed-interval numeric range (a <= value <= b)"""
        a = None if a is None else float(a) if isinstance(a, (int, float)) else a
        b = None if b is None else float(b) if isinstance(b, (int, float)) else b

        match (a, b):
            case (float(a), None):
                self._add(lambda it: a <= it, f'value less than {a}: %f')
            case (None, float(b)):
                self._add(lambda it: it <= b, f'value over {b}: %f')
            case (float(a), float(b)):
                self._add(lambda it: a <= it <= b, f'value out of range [{a}, {b}]: %f')
            case _:
                raise TypeError()
        return self

    def allow_nan(self, allow: bool = True) -> Self:
        """Allow or disallow NaN (not a number) as a valid float"""
        self.__allow_nan = allow
        return self

    def positive(self, include_zero=True) -> Self:
        """Check if a float value is positive or non-negative"""
        if include_zero:
            self._add(lambda it: it >= 0, 'not a non-negative value: %f')
        else:
            self._add(lambda it: it > 0, 'not a positive value: %f')
        return self

    def negative(self, include_zero=True) -> Self:
        """Check if a float value is negative or non-positive"""
        if include_zero:
            self._add(lambda it: it <= 0, 'not a non-positive value : %f')
        else:
            self._add(lambda it: it < 0, 'not a negative value : %f')
        return self

    def __call__(self, value: Any) -> bool:
        if value != value:  # is NaN
            if self.__allow_nan:
                return True
            else:
                raise ValidatorFailError('NaN')

        return super().__call__(value)


class ListValidatorBuilder(AbstractTypeValidatorBuilder[list[T]]):
    """a list validator"""

    def __init__(self, element_type: type[T] = None):
        super().__init__()
        self._element_type = element_type
        self._allow_empty = True

    def freeze(self) -> Self:
        ret = super().freeze()
        ret._element_type = self._element_type
        ret._allow_empty = self._allow_empty
        return ret

    def length_in_range(self, a: int | None, b: int | None, /) -> Self:
        """Enforce a length range for lists"""
        match (a, b):
            case (int(a), None):
                self._add(lambda it: a <= len(it),
                          lambda it: f'list length less than {a}: {len(it)}')
            case (None, int(b)):
                self._add(lambda it: len(it) <= b,
                          lambda it: f'list length over {b}: {len(it)}')
            case (int(a), int(b)):
                self._add(lambda it: a <= len(it) <= b,
                          lambda it: f'list length out of range [{a}, {b}]: {len(it)}')
            case _:
                raise TypeError()

        return self

    def allow_empty(self, allow: bool = True) -> Self:
        """Allow or disallow empty lists"""
        self._allow_empty = allow
        return self

    def on_item(self, validator: Callable[[Any], bool]) -> Self:
        """Apply an additional validator to each item in the list

        :param validator: A callable that validates each item
        """
        self._add(ListItemValidatorBuilder(validator))
        return self

    def __call__(self, value: Any) -> bool:
        if not isinstance(value, (tuple, list)):
            raise ValidatorFailOnTypeError(f'not a list : {value}')

        if not self._allow_empty and len(value) == 0:
            raise ValidatorFailError(f'empty list : {value}')

        if (element_type := self._element_type) is not None:
            for i, element in enumerate(value):
                if not element_isinstance(element, element_type):
                    raise ValidatorFailError(f'wrong element type at {i} : {element}')

        return super().__call__(value)


class TupleValidatorBuilder(AbstractTypeValidatorBuilder[tuple]):
    """a tuple validator"""

    def __init__(self, element_type: tuple[int] | tuple[type[T], ...]):
        super().__init__()

        match element_type:
            case ():
                # XXX does validate for empty tuple meaningful?
                #  No, so it will be interpreted as ...
                element_type = (...,)
            case (int(length), ):
                element_type = (None,) * length
            case (int(length), e) if e is ...:
                element_type = (None,) * length + (...,)

        self._element_type = element_type

    def freeze(self) -> Self:
        return super().freeze(self._element_type)

    def on_item(self, item: int | list[int] | None, validator: Callable[[Any], bool]) -> Self:
        """Apply a validator to specific tuple positions

        :param item: A single index, a list of indices, or None for all indices
        :param validator: The validation callable to apply
        """
        self._add(TupleItemValidatorBuilder(item, validator))
        return self

    def __call__(self, value: Any) -> bool:
        if not isinstance(value, tuple):
            raise ValidatorFailOnTypeError(f'not a tuple : {value}')

        if len(element_type := self._element_type) > 0:
            if element_type[-1] is ...:
                at_least_length = len(element_type) - 1
                if len(value) < at_least_length:
                    raise ValidatorFailError(f'length less than {at_least_length} : {value}')

                for i, e, t in zip(range(at_least_length), value, element_type):
                    if t is not None and not element_isinstance(e, t):
                        raise ValidatorFailError(f'wrong element type at {i} : {e}')

                if at_least_length > 0:
                    if (last_element_type := element_type[at_least_length - 1]) is not None:
                        for i, e in zip(range(at_least_length, len(value)), value[at_least_length:]):
                            if not element_isinstance(e, last_element_type):
                                raise ValidatorFailError(f'wrong element type at {i} : {e}')

            else:
                if len(value) != len(element_type):
                    raise ValidatorFailError(f'length not match to {len(element_type)} : {value}')

                for i, e, t in zip(range(len(element_type)), value, element_type):
                    if t is not None and not element_isinstance(e, t):
                        raise ValidatorFailError(f'wrong element type at {i} : {e}')

        return super().__call__(value)


class PathValidatorBuilder(AbstractTypeValidatorBuilder[Path]):
    """a path validator"""

    def __init__(self):
        super().__init__(Path)

    def is_suffix(self, suffix: str | list[str] | tuple[str, ...]) -> Self:
        """Check path suffix or in a list of suffixes"""
        if isinstance(suffix, str):
            self._add(lambda it: it.suffix == suffix, f'suffix != {suffix}: %s')
        elif isinstance(suffix, (list, tuple)):
            self._add(lambda it: it.suffix in suffix, f'suffix not in {suffix}: %s')
        else:
            raise TypeError('')

        return self

    def is_exists(self) -> Self:
        """Check if path exists"""
        self._add(lambda it: it.exists(), f'path does not exist: %s')
        return self

    def is_file(self) -> Self:
        """Check if path is a file"""
        self._add(lambda it: it.is_file(), f'path is not a file: %s')
        return self

    def is_dir(self) -> Self:
        """Check if path is a directory"""
        self._add(lambda it: it.is_dir(), f'path is not a directory: %s')
        return self


class ListItemValidatorBuilder(LambdaValidator):
    def __call__(self, value: Any) -> bool:
        for i, element in enumerate(value):
            try:
                fail = not super().__call__(element)
            except BaseException as e:
                raise ValidatorFailError(f'at index {i}, ' + e.args[0]) from e
            else:
                if fail:
                    raise ValidatorFailError(f'at index {i}, validate fail : {value}')
        return True

    def _on_element(self, value: Any) -> bool:
        return super().__call__(value)

    def freeze(self) -> Self:
        if isinstance(validator := self._validator, Validator):
            validator = validator.freeze()

        return ListItemValidatorBuilder(validator, self._message)


class TupleItemValidatorBuilder(LambdaValidator):
    def __init__(self, item: int | list[int] | None, validator: Callable[[Any], bool]):
        super().__init__(validator)
        self._item = item

    def __call__(self, value: Any) -> bool:
        if self._item is None:
            for index in range(len(value)):
                if not self.__call_on_index__(index, value):
                    return False
            return True
        elif isinstance(self._item, int):
            return self.__call_on_index__(self._item, value)
        else:
            for index in self._item:
                if not self.__call_on_index__(index, value):
                    return False
            return True

    def __call_on_index__(self, index: int, value: Any) -> bool:
        try:
            element = value[index]
        except IndexError as e:
            raise ValidatorFailError(f'index {index} out of size {len(value)}') from e

        try:
            return super().__call__(element)
        except BaseException as e:
            raise ValidatorFailError(f'at index {index}, ' + e.args[0]) from e

    def freeze(self) -> Self:
        if isinstance(validator := self._validator, Validator):
            validator = validator.freeze()

        return TupleItemValidatorBuilder(self._item, validator)


class OrValidatorBuilder(Validator):
    def __init__(self, *validator: Callable[[Any], bool]):
        self.__validators = [it.freeze() if isinstance(it, Validator) else it for it in validator]

    def __call__(self, value: Any) -> bool:
        if len(self.__validators) == 0:
            return True

        coll = []
        for validator in self.__validators:
            try:
                if validator(value):
                    return True
            except ValidatorFailOnTypeError:
                pass
            except BaseException as e:
                if len(e.args):
                    coll.append(e.args[0])

        raise ValidatorFailError('; '.join(coll))

    def freeze(self) -> Self:
        return OrValidatorBuilder(*self.__validators)

    def __and__(self, validator: Callable[[Any], bool]) -> AndValidatorBuilder:
        return AndValidatorBuilder(self, validator)

    def __or__(self, validator: Callable[[Any], bool]) -> OrValidatorBuilder:
        if isinstance(validator, OrValidatorBuilder):
            self.__validators.extend(validator.__validators)
        else:
            self.__validators.append(validator)
        return self


class AndValidatorBuilder(Validator):
    def __init__(self, *validator: Callable[[Any], bool]):
        self.__validators = [it.freeze() if isinstance(it, Validator) else it for it in validator]

    def __call__(self, value: Any) -> bool:
        if len(self.__validators) == 0:
            return True

        for validator in self.__validators:
            if not validator(value):
                raise ValidatorFailError()

        return True

    def freeze(self) -> Self:
        return AndValidatorBuilder(*self.__validators)

    def __and__(self, validator: Callable[[Any], bool]) -> AndValidatorBuilder:
        if isinstance(validator, AndValidatorBuilder):
            self.__validators.extend(validator.__validators)
        else:
            self.__validators.append(validator)
        return self

    def __or__(self, validator: Callable[[Any], bool]) -> OrValidatorBuilder:
        return OrValidatorBuilder(self, validator)


def element_isinstance(e, t) -> bool:
    if isinstance(t, type):
        return isinstance(e, t)

    if t is Any:
        return True

    if callable(t):
        try:
            return True if t(e) else False
        except TypeError:
            return False

    print(f'NotImplementedError(element_isinstance(..., {t}))')
    return False
