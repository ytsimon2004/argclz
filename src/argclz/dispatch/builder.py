import inspect
import warnings
from typing import Callable, TypeVar, Generic, get_origin, Literal

from .core import ARGCLZ_DISPATCH_COMMAND, DispatchCommand
from ..validator import Validator

__all__ = ['DispatchCommandBuilder']

T = TypeVar('T')
P = inspect.Parameter


class DispatchCommandBuilder:
    """
    (internal) Do not use this class directly.
    """
    def __init__(self, func):
        self.func = func
        self.signature = inspect.signature(func, eval_str=True)
        self.validators = {}

    @classmethod
    def of(cls, f):
        ret = getattr(f, ARGCLZ_DISPATCH_COMMAND, None)
        if ret is None:
            ret = DispatchCommandBuilder(f)
            setattr(f, ARGCLZ_DISPATCH_COMMAND, ret)
        elif isinstance(ret, DispatchCommandBuilder):
            pass
        elif isinstance(ret, DispatchCommand):
            raise RuntimeError(f'{f.__name__} already frozen')
        else:
            raise TypeError()
        return ret

    def validator_for(self, arg: str, caster: Callable[[str], T] | None = None, validator: Validator | None = None):
        try:
            p = self.signature.parameters[arg]
        except KeyError:
            warnings.warn(f'unknown parameter name : {arg} for function {self.func.__name__}', RuntimeWarning)
            return

        if caster is None:
            from .._types import caster_by_annotation
            if p.annotation is P.empty:
                raise RuntimeError(f'unknown parameter type : {arg} for function {self.func.__name__}')

            caster = caster_by_annotation(arg, p.annotation)  # pyright: ignore[reportAssignmentType]

        from ..types import literal_type
        if isinstance(caster, literal_type) and get_origin(p.annotation) is Literal:
            caster.set_candidate(p.annotation)

        self.validators[arg] = TypeCasterWithValidator(caster, validator)

    def build(self, command: str,
              aliases: tuple[str, ...],
              order: float = 5,
              group: str | None = None,
              usage: str | None = None,
              hidden=False) -> DispatchCommand:
        ret = DispatchCommand(group, command, aliases, order, usage, self.func, self.validators, hidden)
        setattr(self.func, ARGCLZ_DISPATCH_COMMAND, ret)
        return ret


class TypeCasterWithValidator(Generic[T]):
    """
    (internal) Do not use this class directly.
    """
    def __init__(self, caster: Callable[[str], T] | None,
                 validator: Callable[[T], bool] | None):
        self.caster = caster
        self.validator = validator

    def __call__(self, raw_value: str) -> T:
        result: T

        if self.caster is not None:
            try:
                result = self.caster(raw_value)
            except BaseException as e:
                if isinstance(self.caster, type):
                    raise ValueError(f'cannot cast "{raw_value}" to type {self.caster.__name__}') from e
                else:
                    raise ValueError(f'cannot cast "{raw_value}"') from e
        else:
            result = raw_value  # pyright: ignore[reportAssignmentType]

        if self.validator is not None:
            try:
                fail = not self.validator(result)
            except BaseException:
                raise
            else:
                if fail:
                    raise ValueError(f'fail validation : "{raw_value}"')

        return result
