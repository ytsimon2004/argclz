from __future__ import annotations

from typing import Callable, TypeVar, overload, ParamSpec, TypeAlias, TYPE_CHECKING

from .. import i18n
from ..validator import Validator

if TYPE_CHECKING:
    from .core import DispatchGroup

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
             group: str | DispatchGroup | None = None,
             order: float = 5,
             usage: str | None = None,
             hidden=False) -> Decorator:
    """
    A decorator that mark a function as a dispatch target function.

    Functions decorated in the same dispatch group should have compatible
    signatures, at least for required parameters. For example:

    **Example**

    >>> class D(Dispatch):
    ...     @dispatch('A')
    ...     def function_a(self, a, b, c=None):
    ...         pass
    ...     @dispatch('B')
    ...     def function_b(self, a, b, d=None):
    ...         pass
    ...     def run_function(self, a, b):
    ...         self.invoke_command('A', a, b)

    :param command: primary command name
    :param alias: secondary command names
    :param group: command group
    :param order: order of this command shown in the :meth:`~argclz.dispatch.core.Dispatch.build_command_usages()`
    :param usage: usage line of this command shown in the :meth:`~argclz.dispatch.core.Dispatch.build_command_usages()`
    :param hidden: hide this command from :meth:`~argclz.dispatch.core.Dispatch.list_commands()`
    """

    if len(command) == 0:
        raise ValueError(i18n.gettext('empty command string'))

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
    ...     @validator_for('a') # indicating to cast 'a' to int from command-line input
    ...     def run_cmd(self, a: int):
    ...         assert isinstance(a, int)

    **Type (caster)**

    The parameter ``caster`` usually can be inferred via the annotation of target parameter,
    like the `a: int` in above example.

    :param arg: name of the parameter.
    :param caster: type caster with the signature ``(str) -> R``.
    :param validator: validator with the signature ``(R) -> bool``.
    :return: decorator that attaches conversion and validation to a dispatch function parameter.
    :raise RuntimeError: if any parameter is not annotated its type.
    :raise RuntimeWarning: if ``arg`` does not match to any parameter.
    """
    if isinstance(caster, Validator) and validator is None:
        caster, validator = None, caster

    def _validator_for(f: Method) -> Method:
        from .builder import DispatchCommandBuilder
        DispatchCommandBuilder.of(f).validator_for(arg, caster, validator)  # pyright: ignore[reportArgumentType]
        return f

    return _validator_for
