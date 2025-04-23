from typing import Callable, TypeVar, overload

from ..validator import Validator

__all__ = [
    'dispatch',
    'validator_for'
]

T = TypeVar('T')


def dispatch(command: str,
             *alias: str,
             group: str = None,
             order: float = 5,
             usage: list[str] = None,
             hidden=False):
    """A decorator that mark a function a dispatch target function.

    All functions decorated in same dispatch group should have save
    function signature (at least for non-default parameters). For example:

    >>> class D(Dispatch):
    ...     @dispatch('A')
    ...     def function_a(self, a, b, c=None):
    ...         pass
    ...     @dispatch('B')
    ...     def function_b(self, a, b, d=None):
    ...         pass
    ...     def run_function(self):
    ...         self.invoke_command(self, 'A', a, b)


    """

    if len(command) == 0:
        raise ValueError('empty command string')

    def _dispatch(f):
        from .builder import DispatchCommandBuilder
        DispatchCommandBuilder.of(f).build(command, alias, order, group, usage, hidden)
        return f

    return _dispatch


@overload
def validator_for(arg: str):
    pass


@overload
def validator_for(arg: str, caster: Callable[[str], T] | Validator):
    pass


@overload
def validator_for(arg: str, caster: Callable[[str], T], validator: Validator):
    pass


def validator_for(arg: str, caster=None, validator=None):
    if isinstance(caster, Validator) and validator is None:
        caster, validator = None, caster

    def _validator_for(f):
        from .builder import DispatchCommandBuilder
        DispatchCommandBuilder.of(f).validator_for(arg, caster, validator)
        return f

    return _validator_for
