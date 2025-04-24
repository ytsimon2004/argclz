from __future__ import annotations

import inspect
import textwrap
from collections.abc import Callable
from typing import NamedTuple, TypeVar, Any

from typing_extensions import Self

__all__ = [
    'DispatchCommand',
    'DispatchCommandNotFound',
    'Dispatch',
]

T = TypeVar('T')
R = TypeVar('R')

ARGCLZ_DISPATCH_GROUP = '__argclz_dispatch_group__'
ARGCLZ_DISPATCH_COMMAND = '__argclz_dispatch_command__'


class DispatchCommand(NamedTuple):
    host: type[T] | None
    group: str | None
    command: str
    aliases: tuple[str, ...]
    order: float
    usage: str | None
    func: Callable[..., R]  # target function
    validators: dict[str, Callable[[str], Any]]
    hidden: bool = False

    @property
    def commands(self) -> list[str]:
        return [self.command, *self.aliases]

    def parameters(self) -> list[CommandParameter]:
        s = inspect.signature(self.func)
        p = inspect.Parameter
        return [CommandParameter.of(name, para) for i, (name, para) in enumerate(s.parameters.items()) if i > 0]

    @property
    def doc(self) -> str | None:
        return self.func.__doc__

    def __call__(self, zelf: T, *args, **kwargs) -> R:
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
    @classmethod
    def list_commands(cls, group: str | None = ..., *, all: bool = False) -> list[DispatchCommand]:
        """list all dispatch-decorated function info in *host*.

        :param group: dispatch group.
        :param all: including hidden commands
        :return: list of DispatchCommand
        """
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
    def find_command(cls, command: str, group: str | None = ...) -> DispatchCommand | None:
        """find dispatch-decoratored function in *host* according to *command*.

        :param command: command or command alias
        :param group: dispatch group
        :return: found DispatchCommand
        """
        info: DispatchCommand

        for attr in dir(cls):
            attr_value = getattr(cls, attr)
            if (info := getattr(attr_value, ARGCLZ_DISPATCH_COMMAND, None)) is not None:
                if group is ... or group == info.group:
                    if command == info.command or command in info.aliases:
                        return info

        return None

    def invoke_command(self, command: str, *args, **kwargs) -> Any:
        """invoke a dispatch-decoratored function in default group.

        :param command: command or command alias
        :param args: dispatch-decoratored function positional arguments
        :param kwargs: dispatch-decoratored function keyword arguments
        :return: function return
        :raise DispatchCommandNotFound:
        """
        if (info := self.find_command(command, None)) is None:
            raise DispatchCommandNotFound(command)
        return info(self, *args, **kwargs)

    def invoke_group_command(self, group: str, command: str, *args, **kwargs) -> Any:
        """invoke a dispatch-decoratored function in certain group.

        :param group: dispatch group
        :param command: command or command alias
        :param args: dispatch-decoratored function positional arguments
        :param kwargs: dispatch-decoratored function keyword arguments
        :return: function return
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
