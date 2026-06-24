import functools
from types import EllipsisType
from typing import Any, NoReturn, overload, Literal
from typing_extensions import Self

import numpy as np

from .. import i18n
from ..validator import AbstractTypeValidatorBuilder, ValidatorChangeValueRequest, ValidatorFailOnTypeError, ValidatorFailError


class NumpyArrayValidator(AbstractTypeValidatorBuilder[np.ndarray]):

    def __init__(self, mode: Literal['r+', 'r', None] = None):
        """

        :param mode: memmap mode. It only affects the type caster that is used to read a numpy file from the disk.
        """
        super().__init__()
        self._auto_casting = False
        self._dtype: np.dtype | None = None
        self._ndim: int | None = None
        self._shape: tuple[int | str | tuple[str, ...] | list[str] | EllipsisType | None, ...] | None = None
        self._mode = mode
        self._binary = None

    def auto_casting(self, value: bool = True) -> Self:
        """Allow the validator try to cast input into tuple first."""
        self._auto_casting = value
        return self

    def dtype(self, t: np.dtype) -> Self:
        self._dtype = t
        return self

    def ndim(self, n: int) -> Self:
        self._ndim = n
        return self

    @overload
    def shape(self, shape: tuple[int, ...] | list[int]) -> Self:
        pass

    @overload
    def shape(self, *shape: int | str | tuple[str, ...] | list[str] | EllipsisType | None) -> Self:
        pass

    def shape(self, *shape: int | str | tuple[str, ...] | list[str] | EllipsisType | None) -> Self:
        if len(shape) == 1 and isinstance(shape[0], (tuple, list)):
            shape = tuple(shape[0])

        self._shape = shape

        try:
            i = shape.index(...)
        except ValueError:
            pass
        else:
            try:
                shape.index(..., i + 1)
            except ValueError:
                pass
            else:
                raise ValueError(i18n.gettext('multiple ...: %s') % str(shape))

        if len(shape):
            self._check_shape(None)

        return self

    # noinspection PyOverloads,SpellCheckingInspection
    @overload  # this overload is used to show the actual keyword arguments.
    def binary(self, offset: int = 0, order: Literal['C', 'F'] = 'C') -> Self:
        pass

    # noinspection SpellCheckingInspection
    def binary(self, **kwargs) -> Self:
        """
        Allow this validator to create a type caster to read a path of binary file into a numpy memmap array.
        The *kwargs* are pass to :func:`numpy.memmap` except ``dtype`` (given by :meth:`dtype`), ``shape``
        (given by :meth:`shape`) and ``mode`` (given by :meth:`__init__`).

        In order to read binary file as memmap array. ``shape`` is restricted. ``...`` is not allowed. Only one
        ``None`` and label (``str``) is allowed.

        :param kwargs:
        :return:
        """
        self._binary = kwargs
        return self

    def freeze(self) -> Self:
        ret = super().freeze(self._mode)
        ret._auto_casting = self._auto_casting
        ret._dtype = self._dtype
        ret._ndim = self._ndim
        ret._shape = self._shape
        ret._binary = dict(self._binary) if self._binary is not None else None
        return ret

    # noinspection SpellCheckingInspection
    def type_caster(self):
        if self._binary is None:
            # TODO allow_pickle?
            # TODO fix_imports?
            return functools.partial(np.load, mmap_mode=self._mode)
        else:
            mode = self._mode if self._mode is not None else 'r+'
            dtype = self._dtype if self._dtype is not None else np.uint8
            shape = self._fix_shape()

            if shape is None:
                return functools.partial(np.memmap, mode=mode, dtype=dtype, shape=shape, **self._binary)

            else:
                total = 1
                for length in shape:
                    total *= length

                if total > 0:
                    return functools.partial(np.memmap, mode=mode, dtype=dtype, shape=shape, **self._binary)
                else:
                    neg_index = shape.index(-1)

                    def memmap(file):
                        ret = np.memmap(file, mode=mode, dtype=dtype, shape=None, **self._binary)
                        _shape = list(shape)
                        _total = -total
                        _shape[neg_index] = ret.size // _total
                        return ret.reshape(_shape)

                    return memmap

    def __call__(self, instance: Any, value: Any) -> bool:
        if self._check_none(value):
            return True

        if not isinstance(value, (np.ndarray, np.memmap)):
            if self._auto_casting:
                raise ValidatorChangeValueRequest(np.asarray(value, self._dtype))
            else:
                raise ValidatorFailOnTypeError(value, np.ndarray)

        if self._ndim is not None:
            if value.ndim != self._ndim:
                raise ValidatorFailError(i18n.gettext('ndim is not %d, but shape : %s') % (self._ndim, str(value.shape)))

        if self._shape is not None:
            self._check_shape(value)

        return self._call_validators(value, value)

    def _fix_shape(self) -> tuple[int, ...] | None:
        shape = self._shape
        if shape is None:
            return None

        ret = []
        neg_count = 0

        for i, length in enumerate(shape):
            match length:
                case None | str():
                    if neg_count == 0:
                        ret.append(-1)
                        neg_count += 1
                    else:
                        raise ValueError(i18n.gettext('unspecific length at shape[%d]: %s') % (i, str(shape)))
                case int(length):
                    assert length >= 0
                    ret.append(length)
                case tuple(labels) | list(labels):
                    ret.append(len(labels))
                case e if e is ...:
                    raise ValueError(i18n.gettext('unspecific dimension at shape[%d]: %s') % (i, str(shape)))
                case _:
                    raise ValueError(i18n.gettext('illegal length expression in shape[%d] : %s') % (i, str(shape[i])))

        return tuple(ret)

    def _check_shape(self, arr: np.ndarray | None):
        assert self._shape is not None
        shape = self._shape

        if len(shape) == 0:
            if arr is None:
                return
            if len(arr.shape) != 0:
                raise ValidatorFailError(i18n.gettext('not a scalar'))

        else:
            index = (0, 0)
            arr_shape = None if arr is None else arr.shape
            while index != (None, None):
                index = self._check_shape_at(arr_shape, index[0], shape, index[1])

    def _check_shape_at(self, shape: tuple[int] | None, i: int, test: tuple, j: int) -> tuple[int, int] | tuple[None, None]:
        assert j < len(test)

        match test[j]:
            case None | str():
                if shape is not None:
                    try:
                        shape[i]
                    except IndexError as e:
                        self._raise_ndim_not_enough(shape, test, e)

            case int(expect_length):
                if expect_length < 0:
                    raise ValueError(i18n.gettext('negative length at shape[%d]: %s') % (j, str(test)))

                if shape is not None:
                    try:
                        actual_length = shape[i]
                    except IndexError as e:
                        self._raise_ndim_not_enough(shape, test, e)

                    if actual_length != expect_length:
                        raise ValidatorFailError(i18n.gettext('shape[%d] != %d: %s') % (i, expect_length, str(shape)))

            case tuple(labels) | list(labels):
                if not all([isinstance(it, str) for it in labels]):
                    raise ValueError(i18n.gettext('labels should be list[str] or tuple[str,...]'))

                if shape is not None:
                    try:
                        actual_length = shape[i]
                    except IndexError as e:
                        self._raise_ndim_not_enough(shape, test, e)

                    if actual_length != len(labels):
                        raise ValidatorFailError(i18n.gettext('shape[%d] != %d: %s') % (i, len(labels), str(shape)))

            case e if e is ...:
                if shape is not None:
                    remaining = len(test) - j - 1
                    next_i = len(shape) - remaining - 1
                    if next_i + 1 < i:
                        raise ValidatorFailError(i18n.gettext('ndim < %d: %s') % (len(test) - 1, str(shape)))
                    i = next_i

            case _:
                raise ValueError(i18n.gettext('illegal length expression in shape[%d] : %s') % (j, str(test[j])))

        if shape is None:
            if j + 1 < len(test):
                return i + 1, j + 1
            else:
                return None, None

        if i + 1 == len(shape) and j + 1 == len(test):
            return None, None
        elif j + 1 < len(test):
            return i + 1, j + 1

        assert j + 1 == len(test), f'{j+1=}, {test=}'
        raise ValidatorFailError(i18n.gettext('ndim != %d: %s') % (len(test), str(shape)))

    @classmethod
    def _raise_ndim_not_enough(cls, shape: tuple[int], test: tuple[int], e: IndexError) -> NoReturn:
        try:
            test.index(...)
        except ValueError:
            at_least = False
        else:
            at_least = True  # found ...

        if at_least:
            raise ValidatorFailError(i18n.gettext('ndim < %d: %s') % (len(test) - 1, str(shape))) from e
        else:
            raise ValidatorFailError(i18n.gettext('ndim != %d: %s') % (len(test), str(shape))) from e
