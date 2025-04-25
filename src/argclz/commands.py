import argparse
import inspect
import sys
from typing import Type, TypeVar, overload

from .core import AbstractParser, new_parser, ArgumentParser, set_options, ArgumentParserInterrupt

__all__ = [
    'sub_command_group',
    'new_command_parser',
    'parse_command_args',
    'get_sub_command_group'
]

T = TypeVar('T')
ARGCLZ_SUB_COMMANDS = '__argclz_sub_commands__'


class SubCommandGroup:
    def __init__(self, **kwargs):
        self.attr = None
        self.kwargs = kwargs
        self.sub_parsers: list[SubCommand] = []

    def __set_name__(self, owner, name):
        if hasattr(owner, ARGCLZ_SUB_COMMANDS):
            raise RuntimeError('cannot have multiple sub-commands group')

        self.attr = name
        setattr(owner, ARGCLZ_SUB_COMMANDS, self)

    def __get__(self, instance, owner=None):
        if instance is None:
            return self

        try:
            return instance.__dict__[f'__{self.attr}']
        except KeyError:
            pass

        raise AttributeError(self.attr)

    def __set__(self, instance, value):
        instance.__dict__[f'__{self.attr}'] = value

    def __delete__(self, instance):
        try:
            del instance.__dict__[f'__{self.attr}']
        except KeyError:
            pass

    def add_parser(self, ap: argparse.ArgumentParser):
        sb = ap.add_subparsers(**self.kwargs)
        for command in self.sub_parsers:
            command.add_parser(sb, main=self.attr)

    def __call__(self, command: str):
        def _sub_command(clz: Type[AbstractParser]):
            if not issubclass(clz, AbstractParser):
                raise TypeError()

            self.sub_parsers.append(SubCommand(command, clz))
            return clz

        return _sub_command


class SubCommand:
    def __init__(self, command: str, sub_parser: Type[AbstractParser]):
        self.command = command
        self.sub_parser = sub_parser

    def add_parser(self, sb, main='main'):
        pp = new_parser(self.sub_parser, reset=True)
        pp.set_defaults(**{main: self.sub_parser})

        description = self.sub_parser.DESCRIPTION
        if callable(description):
            description = description()

        sb.add_parser(self.command, help=description, parents=[pp], add_help=False)


@overload
def sub_command_group(*, title: str = ...,
                      description: str = ...,
                      required: bool = ...):
    pass


def sub_command_group(**kwargs):
    """
    Create a sub-commands group.

    >>> class Example(AbstractParser):
    ...     command_group = sub_command_group()
    ...     @command_group('a')
    ...     class SubCommand(AbstractParser):
    ...         ...

    The type of ``sub_command_group()`` as an instance-attribute is ``Type[AbstractParser]|None``, and
    its value is handled by :func:`~argclz.core.set_options()` when paring the command-line arguments.

    **Sub command class**

    When parsing successful (especially when ``parse_only=False`` case), sub-command class
    (e.g. ``SubCommand`` in above example) will be initialized. The ``__init__`` could have two
    different signature, there are

    .. code-block:: python

        def __init__(self): ... # no-arg init
        def __init__(self, parent: AbstractParser): ... # one-arg init

    where the parameter ``parent`` refer to its outer ``AbstractParser`` (e.g. ``Example`` in above example).


    """
    return SubCommandGroup(**kwargs)


def get_sub_command_group(instance) -> SubCommandGroup | None:
    """(internal function)"""
    if not isinstance(instance, type):
        instance = type(instance)

    return getattr(instance, ARGCLZ_SUB_COMMANDS, None)


def init_sub_command(p: AbstractParser) -> AbstractParser:
    """(internal function)"""
    if (sub := get_sub_command_group(p)) is None:
        return p

    try:
        pp = sub.__get__(p)
    except AttributeError:
        return p

    if pp is None:
        return p

    if not isinstance(pp, type):
        return pp

    s = inspect.signature(pp.__init__)
    if len(s.parameters) == 1:
        return pp()
    else:
        return pp(p)


def new_command_parser(parsers: dict[str, AbstractParser | Type[AbstractParser]],
                       usage: str = None,
                       description: str = None,
                       **kwargs) -> ArgumentParser:
    """A convenient way to create an ArgumentParser with sub-commands.

    :param parsers: dict of command to :class:`~argclz.core.AbstractParser`.
    :param usage: parser usage
    :param description: parser description
    :return:
    """
    ap = ArgumentParser(
        usage=usage,
        description=description,
        formatter_class=argparse.RawDescriptionHelpFormatter,
        **kwargs
    )

    group = SubCommandGroup(title='commands')
    group.attr = 'main'
    group.sub_parsers = [SubCommand(cmd, pp) for cmd, pp in parsers.items()]
    group.add_parser(ap)

    return ap


def parse_command_args(parsers: ArgumentParser | dict[str, AbstractParser | Type[AbstractParser]],
                       args: list[str] = None,
                       usage: str = None,
                       description: str = None,
                       parse_only=False,
                       system_exit: Type[BaseException] = SystemExit) -> AbstractParser:
    """
    A convenient way to run an ArgumentParser with sub-commands.

    :param parsers: dict of command to :class:`~argclz.core.AbstractParser`.
    :param args: List of strings representing the command-line input (e.g. `sys.argv[1:]`). If ``None``, defaults to current process args
    :param usage: Optional usage string to override the auto-generated help
    :param description: Optional description for the main parser
    :param system_exit: exit when commandline parsed fail.
    :return: The parser instance that handled the command (or an :class:`ArgumentParsingResult` if ``parse_only`` or ``system_exit=False``)
    """
    if isinstance(parsers, ArgumentParser):
        parser = parsers
    else:
        parser = new_command_parser(parsers, usage, description)

    try:
        result = parser.parse_args(args)
    except ArgumentParserInterrupt as e:
        exit_status = e.status
        exit_message = e.message
        pp = None
    else:
        exit_status = None
        exit_message = None

        pp: AbstractParser = getattr(result, 'main', None)
        if isinstance(pp, type):
            pp = pp()

        if pp is not None:
            set_options(pp, result)

    if parse_only:
        return pp

    if exit_status is not None:
        if system_exit is SystemExit:
            if exit_status != 0:
                parser.print_usage(sys.stderr)
                print(exit_message, file=sys.stderr)
            sys.exit(exit_status)
        elif issubclass(system_exit, BaseException):
            raise system_exit(exit_status)
        else:
            sys.exit(exit_status)

    if pp is not None:
        pp.run()

    return pp
