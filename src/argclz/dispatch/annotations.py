from typing import Callable, TypeVar, overload, ParamSpec, TypeAlias

from ..validator import Validator

__all__ = [
    'dispatch',
    'validator_for'
]

P = ParamSpec("P")
R = TypeVar('R')
F = TypeVar('F', bound=Callable)
Method: TypeAlias = Callable[P, R]
Decorator: TypeAlias = Callable[[Method], Method]

def dispatch(command: str,
             *alias: str,
             group: str | None = None,
             order: float = 5,
             usage: str | None = None,
             hidden=False) -> Decorator:
    """
    A decorator that mark a function as a dispatch target function.

    All functions decorated in same dispatch group should have save
    function signature (at least for non-default parameters). For example:

    **Example**

    >>> class D(Dispatch):
    ...     @dispatch('A')
    ...     def function_a(self, a, b, c=None):
    ...         pass
    ...     @dispatch('B')
    ...     def function_b(self, a, b, d=None):
    ...         pass
    ...     def run_function(self):
    ...         self.invoke_command(self, 'A', a, b)

    :param command: primary command name
    :param alias: secondary command names
    :param group: command group
    :param order: order of this command shown in the :meth:`~argclz.dispatch.core.Dispatch.build_command_usages()`
    :param usage: usage line of this command shown in the :meth:`~argclz.dispatch.core.Dispatch.build_command_usages()`
    :param hidden: hide this command from :meth:`~argclz.dispatch.core.Dispatch.list_commands()`
    """

    if len(command) == 0:
        raise ValueError('empty command string')

    def _dispatch(f: Method) -> Method:
        from .builder import DispatchCommandBuilder
        DispatchCommandBuilder.of(f).build(command, alias, order, group, usage, hidden)
        return f

    return _dispatch


@overload
def validator_for(arg: str) -> Decorator:
    pass


@overload
def validator_for(arg: str, caster: Callable[[str], R] | Validator) -> Decorator:
    pass


@overload
def validator_for(arg: str, caster: Callable[[str], R], validator: Validator) -> Decorator:
    pass


def validator_for(arg: str, caster: Callable[[str], R] | None = None, validator: Validator | None = None) -> Decorator:
    """
    A decorator that do the caster and validation on dispatch arguments.

    **Example**

    >>> class D(Dispatch):
    ...     @dispatch('cmd')
    ...     @validator_for('a') # indicating to cast 'a' to int from command parameter
    ...     def run_cmd(self, a: int):
    ...         assert isinstance(a, int)

    **Type (caster)**

    The parameter ``caster`` usually can be inferred via the annotation of target parameter,
    like the `a: int` in above example.

    :param arg: name of the parameter.
    :param caster: type caster with the signature ``(str) -> R``.
    :param validator: validator with the signature ``(R) -> bool``.
    """
    if isinstance(caster, Validator) and validator is None:
        caster, validator = None, caster

    def _validator_for(f: Method) -> Method:
        from .builder import DispatchCommandBuilder
        DispatchCommandBuilder.of(f).validator_for(arg, caster, validator)  # pyright: ignore[reportArgumentType]
        return f

    return _validator_for
