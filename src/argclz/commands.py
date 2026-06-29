import argparse
import inspect
import sys
from typing import Type, TypeVar, overload, Any

from . import i18n
# noinspection PyProtectedMember
from .core import (
    AbstractParser,
    ArgumentParser,
    ArgumentParserInterrupt,
    set_options,
)
from .desp import ARGCLZ_NAMESPACE

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
        self.sub_parsers: dict[str, SubCommand] = {}

    @property
    def title(self) -> str | None:
        return self.kwargs.get('title', None)

    @property
    def description(self) -> str | None:
        return self.kwargs.get('description', None)

    @property
    def required(self) -> bool:
        return self.kwargs.get('required', False)

    def __set_name__(self, owner, name):
        if (prev := getattr(owner, ARGCLZ_SUB_COMMANDS, None)) is not None:
            assert isinstance(prev, SubCommandGroup)
            raise RuntimeError(i18n.gettext('cannot have multiple sub-commands groups: %s and %s') % (prev.attr, name))

        self.attr = name
        setattr(owner, ARGCLZ_SUB_COMMANDS, self)

    def __get__(self, instance, owner=None) -> Any:
        if instance is None:
            return self

        try:
            namespace = getattr(instance, ARGCLZ_NAMESPACE)
        except AttributeError:
            namespace = {}
            setattr(instance, ARGCLZ_NAMESPACE, namespace)

        try:
            return namespace[self.attr]
        except KeyError:
            pass

        raise AttributeError(self.attr)

    def __set__(self, instance, value):
        try:
            namespace = getattr(instance, ARGCLZ_NAMESPACE)
        except AttributeError:
            namespace = {}
            setattr(instance, ARGCLZ_NAMESPACE, namespace)

        namespace[self.attr] = value

    def __delete__(self, instance):
        try:
            namespace = getattr(instance, ARGCLZ_NAMESPACE)
            del namespace[self.attr]
        except (AttributeError, KeyError):
            pass

    def _add_parser(self, ap: argparse.ArgumentParser):
        """Add sub-commands into *ap*."""
        kwargs = dict(self.kwargs)
        kwargs['title'] = i18n.gettext(kwargs.pop('title', None))
        kwargs['description'] = i18n.gettext(kwargs.pop('description', None))

        sb = ap.add_subparsers(**kwargs)
        assert self.attr is not None
        for command in self.sub_parsers.values():
            # noinspection PyProtectedMember
            command._add_parser(ap, sb, main=self.attr)

    # noinspection PyOverloads
    @overload  # this overload is used to show the actual keyword arguments.
    def __call__(self,
                 command: str, *,
                 prog: str = None,
                 usage: str = None,
                 description: str = None,
                 epilog: str = None,
                 formatter_class: Type[argparse.HelpFormatter] = ...,
                 fromfile_prefix_chars: str = None,
                 add_help=True,
                 allow_abbrev=True,
                 ) -> argparse.ArgumentParser:
        # TODO python 3.14 add keyword color and suggest_on_error
        pass

    def __call__(self, command: str, **kwargs):
        def _sub_command(sub_parser: AbstractParser | Type[AbstractParser]):
            if isinstance(sub_parser, AbstractParser) or (isinstance(sub_parser, type) and issubclass(sub_parser, AbstractParser)):
                if command in self.sub_parsers:
                    raise RuntimeError(i18n.gettext("sub-command '%s' has been used.") % command)

                self.sub_parsers[command] = SubCommand(command, sub_parser, kwargs)
                return sub_parser
            else:
                if not isinstance(sub_parser, type):
                    sub_parser = type(sub_parser)
                raise TypeError(i18n.gettext('%s is not an AbstractParser') % sub_parser.__name__)

        return _sub_command


class SubCommand:
    def __init__(self, command: str, sub_parser: AbstractParser | Type[AbstractParser], kwargs: dict[str, Any] = None):
        self.command = command
        self.sub_parser = sub_parser
        self.kwargs = kwargs or {}

    def _add_parser(self, ap: ArgumentParser, sb, main='main'):
        """Add sub-commands into *sb*."""
        kwargs = dict(self.kwargs)
        kwargs.setdefault('fromfile_prefix_chars', ap.fromfile_prefix_chars)
        kwargs.setdefault('allow_abbrev', ap.allow_abbrev)
        kwargs.setdefault('add_help', ap.add_help)
        pp = self.sub_parser.new_parser(**kwargs)
        pp.set_defaults(**{main: self.sub_parser})

        kwargs.pop('usage', None)
        kwargs.pop('epilog', None)
        kwargs.pop('description', None)
        kwargs.pop('add_help', None)
        kwargs.setdefault('formatter_class', argparse.RawTextHelpFormatter)
        assert 'parents' not in kwargs

        sb.add_parser(
            self.command,
            help=pp.description,
            usage=pp.usage,
            epilog=pp.epilog,
            description=pp.description,
            parents=[pp],
            add_help=False,
            **kwargs
        )


def sub_command_group(title: str = None, description: str = None, *, required: bool = False, **kwargs):
    """
    Create a sub-commands group.

    The type of ``sub_command_group()`` as an instance-attribute is ``Type[AbstractParser]|None``, and
    its value is handled by :func:`~argclz.core.set_options()` when parsing the command-line arguments.

    **Sub command class**

    When parsing successful (especially when ``parse_only=False`` case), sub-command class
    (e.g. ``SubCommand`` in above example) will be initialized. The ``__init__`` could have two
    different signature, there are

    .. code-block:: python

        def __init__(self): ... # no-arg init
        def __init__(self, parent: AbstractParser): ... # one-arg init

    where the parameter ``parent`` refer to its outer ``AbstractParser`` (e.g. ``Example`` in above example).

    **Parser properties**

    The subparser will be created via Sub command class's :meth:`~argclz.core.AbstractParser.new_parser`.
    Additionally, sub-parser's properties will inherit from parent parser's properties, including
    ``add_help``, ``fromfile_prefix_chars`` and ``allow_abbrev``. Unless user want sub-parser specific behavior that
    is different from parent parser, user has to override sub-parser's :meth:`~argclz.core.AbstractParser.new_parser`.

    **Command line parsing**

    When :meth:`~argclz.core.AbstractParser.main` is invoked and sub command is called,
    the method will return instance of the corresponding sub command and the command group
    (``command_group`` in above example) will be set to the class of the corresponding sub command.

    :param title: group title
    :param description: group description
    :param required: is sub command required?
    :param kwargs: other keyword parameters pass to :meth:`~argclz.core.AbstractParser.new_parser`.
    """
    return SubCommandGroup(title=title, description=description, required=required, **kwargs)


def get_sub_command_group(instance) -> SubCommandGroup | None:
    """(internal function) Return the sub-command group descriptor defined on ``instance`` or its class."""
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

    pp_cls: Type[AbstractParser] = pp
    s = inspect.signature(pp_cls.__init__)
    if len(s.parameters) == 1:
        # def __init__(self):
        return pp_cls()
    else:
        # def __init__(self, parent):
        return pp_cls(p)


def new_command_parser(parsers: dict[str, AbstractParser | Type[AbstractParser]],
                       usage: str | None = None,
                       description: str | None = None,
                       **kwargs) -> ArgumentParser:
    """A convenient way to create an ArgumentParser with sub-commands.

    :param parsers: dict of command to :class:`~argclz.core.AbstractParser`.
    :param usage: parser usage
    :param description: parser description
    :param kwargs: additional keyword arguments passed to :class:`argparse.ArgumentParser`.
    :return: configured parser with one subparser for each command in ``parsers``.
    """
    ap = ArgumentParser(
        usage=i18n.gettext(usage),
        description=i18n.gettext(description),
        formatter_class=argparse.RawDescriptionHelpFormatter,
        **kwargs
    )

    group = SubCommandGroup(title=i18n.gettext('commands'))
    group.attr = 'main'
    group.sub_parsers = {cmd: SubCommand(cmd, pp) for cmd, pp in parsers.items()}
    # noinspection PyProtectedMember
    group._add_parser(ap)

    return ap


def parse_command_args(parsers: ArgumentParser | dict[str, AbstractParser | Type[AbstractParser]],
                       args: list[str] | None = None,
                       usage: str | None = None,
                       description: str | None = None,
                       parse_only=False,
                       system_exit: Type[BaseException] = SystemExit) -> AbstractParser | None:
    """
    A convenient way to run an ArgumentParser with sub-commands.

    :param parsers: dict of command to :class:`~argclz.core.AbstractParser`.
    :param args: List of strings representing the command-line input (e.g. `sys.argv[1:]`). If ``None``, defaults to current process args
    :param usage: Optional usage string to override the auto-generated help
    :param description: Optional description for the main parser
    :param parse_only: parse command-line arguments only, do not raise parsing errors and do not invoke :meth:`~argclz.core.AbstractParser.run`
    :param system_exit: exception type raised when command-line parsing fails. Defaults to ``SystemExit``.
    :return: parser itself. If it has sub command, return sub parser when used.
    """
    if isinstance(parsers, ArgumentParser):
        parser = parsers
    else:
        parser = new_command_parser(parsers, usage, description)

    pp: AbstractParser | None
    try:
        result = parser.parse_args(args)
    except ArgumentParserInterrupt as e:
        error = e
        pp = None
    else:
        error = None

        pp = getattr(result, 'main', None)
        if isinstance(pp, type):
            pp = pp()

        if pp is not None:
            set_options(pp, result)

    if parse_only:
        return pp

    if error is not None:
        if system_exit is SystemExit:
            if error.status != 0:
                parser.print_usage(sys.stderr)
                print(error.message, file=sys.stderr)
            sys.exit(error.status)
        elif issubclass(system_exit, BaseException):
            raise system_exit(error.message) from error
        else:
            sys.exit(error.status)

    if pp is not None:
        pp.run()

    return pp
