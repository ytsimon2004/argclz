import inspect
import sys
from typing import Callable, TypeVar, Generic

from .core import ARGCLZ_DISPATCH_COMMAND, DispatchCommand
from ..validator import Validator

__all__ = ['DispatchCommandBuilder']

T = TypeVar('T')
P = inspect.Parameter


class DispatchCommandBuilder:
    """
    (internal) Do not use class directly.
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

    def validator_for(self, arg: str, caster: Callable[[str], T] = None, validator: Validator = None):
        try:
            p = self.signature.parameters[arg]
        except KeyError:
            print(f'unknown arg name : {arg} for function {self.func.__name__}', file=sys.stderr)
            return

        if caster is None:
            from .._types import caster_by_annotation
            if p.annotation is P.empty:
                raise RuntimeError(f'missing type : {self.func.__name__}({arg})')

            caster = caster_by_annotation(arg, p.annotation)

        self.validators[arg] = TypeCasterWithValidator(caster, validator)

    def build(self, command: str,
              aliases: tuple[str, ...],
              order: float = 5,
              group: str = None,
              usage: str = None,
              hidden=False) -> DispatchCommand:
        ret = DispatchCommand(group, command, aliases, order, usage, self.func, self.validators, hidden)
        setattr(self.func, ARGCLZ_DISPATCH_COMMAND, ret)
        return ret


class TypeCasterWithValidator(Generic[T]):
    """
    (internal) Do not use class directly.
    """
    def __init__(self, caster: Callable[[str], T] | None,
                 validator: Callable[[T], bool]):
        self.caster = caster
        self.validator = validator

    def __call__(self, value: str) -> T:
        raw_value = value

        if self.caster is not None and isinstance(value, str):
            try:
                value = self.caster(value)
            except BaseException as e:
                # print(e)
                raise

        if self.validator is not None:
            try:
                fail = not self.validator(value)
            except BaseException as e:
                # print(e)
                raise
            else:
                if fail:
                    raise ValueError(f'fail validation : "{raw_value}"')

        return value
