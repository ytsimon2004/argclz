import inspect
from collections.abc import Callable
from typing import NamedTuple, TypeVar, Any

__all__ = [
    'ARGP_DISPATCH_GROUP',
    'ARGP_DISPATCH_COMMAND',
    'DispatchCommand',
    'DispatchCommandNotFound',
    'Dispatch',
]

T = TypeVar('T')
R = TypeVar('R')

ARGP_DISPATCH_GROUP = '__argp_dispatch_group__'
ARGP_DISPATCH_COMMAND = '__argp_dispatch_command__'


class DispatchCommand(NamedTuple):
    host: type[T] | None
    group: str | None
    command: str
    aliases: tuple[str, ...]
    order: float
    usage: list[str]
    func: Callable[..., R]  # target function
    validators: dict[str, Callable[[str], Any]]
    hidden: bool = False

    @property
    def commands(self) -> list[str]:
        return [self.command, *self.aliases]

    @property
    def doc(self) -> str | None:
        return self.func.__doc__

    def __call__(self, zelf: T, *args, **kwargs) -> R:
        a = inspect.signature(self.func).bind_partial(zelf, *args, **kwargs)

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


class DispatchCommandNotFound(RuntimeError):
    def __init__(self, command: str, group: str | None = None):
        if group is None:
            message = f'command {command} not found'
        else:
            message = f'command {group}:{command} not found'

        super().__init__(message)


class Dispatch:
    @classmethod
    def list_commands(cls, group: str | None = ...) -> list[DispatchCommand]:
        """list all dispatch-decoratored function info in *host*.

        :param group: dispatch group.
        :return: list of DispatchCommand
        """
        info: DispatchCommand

        ret = []
        for attr in dir(cls):
            attr_value = getattr(cls, attr)
            if (info := getattr(attr_value, ARGP_DISPATCH_COMMAND, None)) is not None:
                if group is ... or group == info.group:
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
            if (info := getattr(attr_value, ARGP_DISPATCH_COMMAND, None)) is not None:
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
    def build_command_usages(cls, group: str | None = None) -> str:
        from ._format import format_dispatch_commands
        return format_dispatch_commands(cls, group)
