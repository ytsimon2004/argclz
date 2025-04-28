from __future__ import annotations

import inspect
import textwrap
from collections.abc import Callable
from typing import NamedTuple, TypeVar, Any, Type, ParamSpec

from typing_extensions import Self

__all__ = [
    'DispatchCommand',
    'DispatchCommandNotFound',
    'dispatch_group',
    'Dispatch',
]

T = TypeVar('T')
P = ParamSpec('P')
R = TypeVar('R')

ARGCLZ_DISPATCH_COMMAND = '__argclz_dispatch_command__'


class DispatchCommand(NamedTuple):
    """
    The information of :func:`~argclz.dispatch.annotations.dispatch` function.
    Use :func:`~argclz.dispatch.annotations.dispatch` instead.
    Do not create this class directly.
    """

    group: str | None
    """dispatch group"""

    command: str
    """primary command"""

    aliases: tuple[str, ...]
    """secondary command"""

    order: float
    """order of this command shown in the help document"""

    usage: str | None
    """usage line of this command """

    func: Callable[P, R]
    """target function"""

    validators: dict[str, Callable[[str], Any]]
    """parameter validators"""

    hidden: bool = False
    """Is it hidden?"""

    @property
    def commands(self) -> list[str]:
        """all acceptable commands"""
        return [self.command, *self.aliases]

    def parameters(self) -> list[CommandParameter]:
        """information of command's parameters"""
        s = inspect.signature(self.func)
        return [CommandParameter.of(name, para) for i, (name, para) in enumerate(s.parameters.items()) if i > 0]

    @property
    def doc(self) -> str | None:
        """document of the command."""
        return self.func.__doc__

    def __call__(self, zelf: T, *args: P.args, **kwargs: P.kwargs) -> R:
        """
        invoke commands.

        **parameter pre-processing**

        If any argument in *args* is a str that matches `'name=value'` patterns,
        it will be parsed into a keyword argument. It allows use `key=value` pattern
        in commandline without knowing the position of the parameter.

        **parameter post-processing**

        If any argument has a validator (by :func:`~argclz.dispatch.annotations.validator_for`),
        the argument will be casted to desired type (if it is a str) and be validated.
        An `ValueError` will be raised when validation fail.

        :param zelf: instance of the target function
        :param args: positional arguments of the target function
        :param kwargs: keyword arguments of the target function
        :return: target function's return
        """
        _args = []
        _kwargs = dict(kwargs)

        for value in args:
            if isinstance(value, str):
                match value.partition('='):
                    case (value, '', ''):
                        _args.append(value)
                    case (k, '=', value):
                        _kwargs[k] = value
            else:
                _args.append(value)

        a = inspect.signature(self.func).bind_partial(zelf, *_args, **_kwargs)

        for par, validator in self.validators.items():
            try:
                val = a.arguments[par]
            except KeyError:
                continue

            try:
                new_value = validator(val)
            except (ValueError, TypeError, IndexError, KeyError) as e:
                raise ValueError(f'command {self.command} argument "{par}" : {e}') from e

            a.arguments[par] = new_value

        return self.func(*a.args, **a.kwargs)


class DispatchGroup(NamedTuple):
    """dispatch group."""

    group: str
    """group name"""

    def __call__(self, command: str,
                 *alias: str,
                 order: float = 5,
                 usage: str = None,
                 hidden=False):
        """
        A decorator that mark a function as a dispatch target function.

        All functions decorated in same dispatch group should have save
        function signature (at least for non-default parameters). For example:

        **Example**

        >>> class D(Dispatch):
        ...     command_group = dispatch_group('A')
        ...     @command_group('A')
        ...     def function_a(self, a, b, c=None):
        ...         pass

        :param command: primary command name
        :param alias: secondary command names
        :param order: order of this command shown in the :meth:`~argclz.dispatch.core.Dispatch.build_command_usages()`
        :param usage: usage line of this command shown in the :meth:`~argclz.dispatch.core.Dispatch.build_command_usages()`
        :param hidden: hide this command from :meth:`~argclz.dispatch.core.Dispatch.list_commands()`
        """
        from .annotations import dispatch
        return dispatch(command, *alias, group=self.group, order=order, usage=usage, hidden=hidden)

    def __set_name__(self, owner, name):
        if not issubclass(owner, Dispatch):
            raise TypeError('owner not Dispatch')

    def __get__(self, instance: Dispatch, owner: Type[Dispatch]) -> BoundDispatchGroup:
        if instance is None:
            return BoundDispatchGroup(owner, self.group)
        else:
            return BoundDispatchGroup(instance, self.group)


class BoundDispatchGroup(NamedTuple):
    zelf: Dispatch | Type[Dispatch]
    group: str

    def list_commands(self, *,
                      all: bool = False) -> list[DispatchCommand]:
        """list all :func:`~argclz.dispatch.annotations.dispatch` info in this group.

        :param all: including hidden commands
        :return: list of DispatchCommand
        """
        return self.zelf.list_commands(self.group, all=all)

    def find_command(self, command: str) -> DispatchCommand | None:
        """find :func:`~argclz.dispatch.annotations.dispatch` function according to *command* in this group.

        :param command:  command or one of command's aliases
        :return: found DispatchCommand
        """
        return self.zelf.find_command(command, group=self.group)

    def invoke_command(self, command: str, *args, **kwargs) -> Any:
        """invoke a :func:`~argclz.dispatch.annotations.dispatch` function in this group.

        :param command:  command or one of command's aliases
         :param args: positional arguments of the target function
        :param kwargs: keyword arguments of the target function
        :return: function's return
        :raise DispatchCommandNotFound:
        """
        if isinstance(self.zelf, type):
            raise TypeError()

        if (info := self.find_command(command)) is None:
            raise DispatchCommandNotFound(command, self.group)
        return info(self.zelf, *args, **kwargs)


def dispatch_group(group: str) -> DispatchGroup:
    """
    Create a dispatch group.

    **Example**

        >>> class D(Dispatch):
        ...     command_group = dispatch_group('A')
        ...     @command_group('A')
        ...     def function_a(self, a, b, c=None):
        ...         pass

    dispatch_group can be assign inside a :class:`Dispatch` (like example above) or
    at the global level.

    :param group: group name.
    :return:
    :raise TypeError: If it is assigned in a non- :class:`Dispatch` class.
    """
    return DispatchGroup(group)


class CommandParameter(NamedTuple):
    name: str
    optional: bool
    kind: inspect._ParameterKind

    @classmethod
    def of(cls, name: str, para: inspect.Parameter) -> Self:
        optional = para.default is not inspect.Parameter.empty
        return CommandParameter(name, optional, para.kind)

    def usage(self):
        name = self.name.upper()
        match self.kind:
            case inspect.Parameter.VAR_KEYWORD:
                return f'**{name}'
            case inspect.Parameter.VAR_POSITIONAL:
                return f'*{name}'
            case inspect.Parameter.KEYWORD_ONLY:
                ret = f'{name}='
            case _:
                ret = name

        if self.optional:
            return f'[{ret}]'
        else:
            return ret


class DispatchCommandNotFound(RuntimeError):
    def __init__(self, command: str, group: str | None = None):
        if group is None:
            message = f'command {command} not found'
        else:
            message = f'command {group}:{command} not found'

        super().__init__(message)


class CommandHelps(NamedTuple):
    commands: list[str]
    order: float
    usage: str | None
    params: list[CommandParameter]
    doc: str

    @classmethod
    def of(cls, command: DispatchCommand) -> Self:
        return CommandHelps(command.commands, command.order, command.usage, command.parameters(), command.doc or '')

    def build_command_usage(self, show_para: bool = False) -> str:
        if self.usage is not None:
            return self.usage

        match self.commands:
            case [command]:
                ret = command
            case [command, *aliases]:
                ret = command + ' (' + ', '.join(aliases) + ')'
            case _:
                raise RuntimeError()

        if not show_para:
            return ret

        return ret + ' ' + ' '.join([it.usage() for it in self.params])

    def brief_doc(self) -> str:
        contents = textwrap.dedent(self.doc).split('\n')

        ret = []
        for content in contents:
            content = content.strip()
            if content == '':
                if len(ret):
                    break
                else:
                    continue

            if content.endswith('.'):
                ret.append(content)
                break

            try:
                i = content.index('. ')
            except ValueError:
                pass
            else:
                ret.append(content[:i + 1])
                break

            ret.append(content)

        return ' '.join(ret)


class Dispatch:
    """
    A :func:`~argclz.dispatch.annotations.dispatch` functions container that
    it is able to find and run the target function by corresponding name (``command`` here).

    **Example**

    >>> from argclz.dispatch import Dispatch, dispatch
    ...     class Main(Dispatch):
    ...         @dispatch('A')
    ...         def run_a(self): ...
    ... Main().invoke_command('A')
    """

    @classmethod
    def list_commands(cls, group: str | DispatchGroup | BoundDispatchGroup | None = ..., *,
                      all: bool = False) -> list[DispatchCommand]:
        """list all :func:`~argclz.dispatch.annotations.dispatch` functions.

        :param group: dispatch group.
        :param all: including hidden commands
        :return: list of DispatchCommand
        """
        if isinstance(group, (DispatchGroup, BoundDispatchGroup)):
            group = group.group

        info: DispatchCommand

        ret = []
        for attr in dir(cls):
            attr_value = getattr(cls, attr)
            if (info := getattr(attr_value, ARGCLZ_DISPATCH_COMMAND, None)) is not None:
                if group is ... or group == info.group:
                    if all or not info.hidden:
                        ret.append(info)

        return ret

    @classmethod
    def find_command(cls, command: str,
                     group: str | DispatchGroup | BoundDispatchGroup | None = ...) -> DispatchCommand | None:
        """find :func:`~argclz.dispatch.annotations.dispatch` function according to *command*.

        :param command: command or one of command's aliases
        :param group: dispatch group
        :return: found :class:`DispatchCommand`
        """
        if isinstance(group, (DispatchGroup, BoundDispatchGroup)):
            group = group.group

        info: DispatchCommand

        for attr in dir(cls):
            attr_value = getattr(cls, attr)
            if (info := getattr(attr_value, ARGCLZ_DISPATCH_COMMAND, None)) is not None:
                if group is ... or group == info.group:
                    if command == info.command or command in info.aliases:
                        return info

        return None

    def invoke_command(self, command: str, *args, **kwargs) -> Any:
        """invoke a :func:`~argclz.dispatch.annotations.dispatch` function in the default group.

        :param command: command or one of command's aliases
        :param args: positional arguments of the target function
        :param kwargs: keyword arguments of the target function
        :return: target function's return
        :raise DispatchCommandNotFound:
        """
        if (info := self.find_command(command, None)) is None:
            raise DispatchCommandNotFound(command)
        return info(self, *args, **kwargs)

    def invoke_group_command(self, group: str | DispatchGroup | BoundDispatchGroup, command: str, *args, **kwargs) -> Any:
        """invoke a :func:`~argclz.dispatch.annotations.dispatch` function in a certain group.

        :param group: dispatch group
        :param command: command or one of command's aliases
        :param args: positional arguments of the target function
        :param kwargs: keyword arguments of the target function
        :return: target function's return
        :raise DispatchCommandNotFound:
        """
        if (info := self.find_command(command, group)) is None:
            raise DispatchCommandNotFound(command, group)
        return info(self, *args, **kwargs)

    @classmethod
    def build_command_usages(cls, group: str | None = None, *,
                             show_para: bool = False,
                             width: int = 120,
                             doc_indent: int = 20) -> str:
        """
        Build a help document for :func:`~argclz.dispatch.annotations.dispatch` functions
        in this class.

        :param group: for functions in the group.
        :param show_para: show parameters.
        :param width: text-wrap width.
        :param doc_indent: description indent.
        :return: help document.
        """
        ret = []

        commands = cls.list_commands(group)
        commands.sort(key=lambda it: it.order)

        for info in commands:
            info = CommandHelps.of(info)

            header = info.build_command_usage(show_para=show_para)
            content = info.brief_doc()

            if len(header) < doc_indent:
                content = header + ' ' * (doc_indent - len(header)) + content
                ret.extend(textwrap.wrap(content, width,
                                         subsequent_indent=' ' * doc_indent,
                                         break_long_words=True,
                                         break_on_hyphens=True))
            else:
                ret.append(header)
                ret.extend(textwrap.wrap(content, width,
                                         initial_indent=' ' * doc_indent,
                                         subsequent_indent=' ' * doc_indent,
                                         break_long_words=True,
                                         break_on_hyphens=True))

        return '\n'.join(ret)
