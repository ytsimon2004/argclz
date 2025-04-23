from __future__ import annotations

import abc
import argparse
import collections
import sys
from collections.abc import Sequence, Iterable, Callable
from typing import Type, TypeVar, Union, Literal, overload, Any, Optional, get_type_hints, TextIO, NamedTuple

from typing_extensions import Self

__all__ = [
    # parser
    'AbstractParser',
    'new_parser',
    'new_command_parser',
    'parse_args',
    'parse_command_args',
    # argument
    'Argument',
    'argument',
    'pos_argument',
    'var_argument',
    'aliased_argument',
    'as_argument',
    # utilities
    'foreach_arguments',
    'with_defaults',
    'set_options',
    'copy_argument',
    'print_help',
    'as_dict'
]

T = TypeVar('T')
Nargs = Literal[
    '*', '+', '?', '...'
]
Actions = Literal[
    'store',
    'store_const',
    'store_true',
    'store_false',
    'append',
    'append_const',
    'extend',
    'count',
    'help',
    'version',
        #
    'boolean'
]


class ArgumentParser(argparse.ArgumentParser):
    exit_status: int = 0
    exit_message: str | None = None

    def exit(self, status: int = 0, message: str = None):
        self.exit_status = status
        self.exit_message = message

    def error(self, message: str):
        self.exit_status = 2
        self.exit_message = message


class ArgumentParsingResult(NamedTuple):
    exit_status: int
    exit_message: str | None

    def __bool__(self):
        return self.exit_status == 0

    def __int__(self):
        return self.exit_status

    def __str__(self):
        return self.exit_message

    @classmethod
    def success(cls) -> ArgumentParsingResult:
        return ArgumentParsingResult(0, None)

    @classmethod
    def of(cls, parser: ArgumentParser) -> ArgumentParsingResult:
        return ArgumentParsingResult(parser.exit_status, parser.exit_message)


class AbstractParser(metaclass=abc.ABCMeta):
    USAGE: str | list[str] = None
    """parser usage."""

    DESCRIPTION: str = None
    """parser description."""

    EPILOG: str = None
    """parser epilog. Could be override as a method if its content is dynamic-generated."""

    def __new__(cls, *args, **kwargs):
        obj = object.__new__(cls)
        with_defaults(obj)
        return obj

    @classmethod
    def new_parser(cls, **kwargs) -> ArgumentParser:
        """create an ``argparse.ArgumentParser``.

        class variable: ``USAGE``, ``DESCRIPTION`` and ``EPILOG`` are used when creation.

        >>> class A(AbstractParser):
        ...     @classmethod
        ...     def new_parser(cls, **kwargs) -> argparse.ArgumentParser:
        ...         return super().new_parser(**kwargs)

        :param kwargs: keyword parameters to ArgumentParser
        :return: an ArgumentParser.
        """
        return new_parser(cls, **kwargs)

    def main(self, args: list[str] | None = None, *,
             parse_only=False,
             system_exit: bool | Type[BaseException] = True) -> ArgumentParsingResult:
        """parsing the commandline input *args* and set the argument attributes,
        then call :meth:`.run()`.

        :param args: command-line arguments
        :param parse_only: parse command-line arguments only, do not invoke ``run()``
        :param system_exit: exit when commandline parsed fail.
        :return: parsing result.
        """
        parser = self.new_parser(reset=True)
        result = parser.parse_args(args)
        set_options(self, result)

        ret = ArgumentParsingResult.of(parser)
        if parse_only:
            return ret

        if not ret:
            if system_exit is True:
                if ret.exit_status != 0:
                    parser.print_usage(sys.stderr)
                    print(ret.exit_message, file=sys.stderr)
                sys.exit(ret.exit_status)
            elif system_exit is False:
                return ret
            elif issubclass(system_exit, BaseException):
                raise system_exit(ret.exit_status)
            else:
                sys.exit(ret.exit_status)

        self.run()
        return ret

    def run(self):
        """called when all argument attributes are set"""
        pass

    def __str__(self):
        return type(self).__name__

    def __repr__(self):
        """key value pair content"""
        self_type = type(self)
        ret = []
        for a_name in dir(self_type):
            a_value = getattr(self_type, a_name)
            if isinstance(a_value, Argument) and not a_name.startswith('_'):
                try:
                    ret.append(f'{a_name} = {a_value.__get__(self, self_type)}')
                except:
                    ret.append(f'{a_name} = <error>')
            elif isinstance(a_value, property):
                try:
                    ret.append(f'{a_name} = {a_value.__get__(self, self_type)}')
                except:
                    ret.append(f'{a_name} = <error>')

        return '\n'.join(ret)


class Argument(object):
    """Descriptor (https://docs.python.org/3/glossary.html#term-descriptor).
    Carried the arguments pass to ``argparse.ArgumentParser.add_argument``.

    **Creation**

    Use :func:`~argp.core.argument()`.

    >>> class Example:
    ...     a: str = argument('-a')

    """

    def __init__(self, *options,
                 validator: Callable[[T], bool] = None,
                 validate_on_set: bool = None,
                 group: str = None,
                 ex_group: str = None,
                 hidden: bool = False,
                 **kwargs):
        """

        :param options: options
        :param group: argument group.
        :param ex_group: mutually exclusive group.
        :param kwargs:
        """
        from .validator import Validator
        if len(options) > 0 and isinstance(options[-1], Validator):
            if validator is not None:
                raise RuntimeError()
            validator = options[-1]
            options = options[:-1]

        self.attr = None
        self.attr_type = Any
        self.group = group
        self.ex_group = ex_group
        self.validator = validator
        self.validate_on_set = validate_on_set
        self.options = options
        self.hidden = hidden
        self.kwargs = kwargs

    @property
    def default(self):
        try:
            return self.kwargs['default']
        except KeyError:
            pass

        if self.attr_type == bool:
            return self.kwargs.get('action', 'store_true') != 'store_true'

        if self.kwargs.get('action', None) in ('append', 'extend', 'append_const'):
            return []

        raise ValueError

    @property
    def const(self):
        try:
            return self.kwargs['const']
        except KeyError:
            pass

        if self.attr_type == bool:
            return self.kwargs.get('action', 'store_true') == 'store_true'

        raise ValueError

    @property
    def metavar(self) -> Optional[str]:
        return self.kwargs.get('metavar', None)

    @property
    def choices(self) -> Optional[tuple[str, ...]]:
        return self.kwargs.get('choices', None)

    @property
    def required(self) -> bool:
        return self.kwargs.get('required', False)

    @property
    def type(self) -> type | Callable[[str], T]:
        try:
            return self.kwargs['type']
        except KeyError:
            pass

        attr_type = self.attr_type
        if attr_type == bool:
            from .types import bool_type
            return bool_type
        elif attr_type in (str, int, float):
            return attr_type
        else:
            from ._types import caster_by_annotation
            return caster_by_annotation(self.attr, attr_type)

    @property
    def help(self) -> Optional[str]:
        return self.kwargs.get('help', None)

    def __set_name__(self, owner: Type, name: str):
        if self.attr is not None:
            raise RuntimeError('reuse Argument')

        self.attr = name
        self.attr_type = get_type_hints(owner).get(name, Any)

        if self.validate_on_set is None:
            if name.startswith('_'):
                self.validate_on_set = False
            else:
                self.validate_on_set = True

        from ._types import complete_arg_kwargs
        complete_arg_kwargs(self)

        if (type_validator := self.validator) is not None:
            from ._types import TypeCasterWithValidator

            type_caster = self.kwargs.get('type', None)
            if isinstance(type_caster, TypeCasterWithValidator):
                self.kwargs['type'] = TypeCasterWithValidator(type_caster.caster, type_validator)
            else:
                self.kwargs['type'] = TypeCasterWithValidator(type_caster, type_validator)

        if self.hidden:
            self.kwargs['help'] = argparse.SUPPRESS

    def __get__(self, instance, owner=None):
        if instance is None:
            if owner is not None:  # ad-hoc for the document building
                self.__doc__ = self.help
            return self
        try:
            return instance.__dict__[f'__{self.attr}']
        except KeyError:
            pass

        raise AttributeError(self.attr)

    def __set__(self, instance, value):
        if self.validate_on_set and (validator := self.validator) is not None:
            from .validator import ValidatorFailError
            try:
                fail = not validator(value)
            except ValidatorFailError:
                raise
            except BaseException as e:
                raise ValueError('validator fail') from e
            else:
                if fail:
                    raise ValueError('validator fail')

        instance.__dict__[f'__{self.attr}'] = value

    def __delete__(self, instance):
        try:
            del instance.__dict__[f'__{self.attr}']
        except KeyError:
            pass

    def add_argument(self, ap: ArgumentParser, instance):
        """Add this into `argparse.ArgumentParser`.

        :param ap:
        :param instance:
        :return:
        """
        try:
            return ap.add_argument(*self.options, **self.kwargs, dest=self.attr)
        except TypeError as e:
            if isinstance(instance, type):
                name = instance.__name__
            else:
                name = type(instance).__name__
            raise RuntimeError(f'{name}.{self.attr} : ' + repr(e)) from e

    @overload
    def with_options(self,
                     option: Union[str, dict[str, str]] = None,
                     *options: str,
                     action: Actions = None,
                     nargs: Union[int, Nargs] = None,
                     const: T = None,
                     default: T = None,
                     type: Union[Type, Callable[[str], T]] = None,
                     validator: Callable[[T], bool] = None,
                     validate_on_set: bool = None,
                     choices: Sequence[str] = None,
                     required: bool = None,
                     hidden: bool = None,
                     help: str = None,
                     group: str = None,
                     metavar: str = None) -> Self:
        pass

    def with_options(self, *options, **kwargs) -> Self:
        """Modify or update keyword parameter and return a new argument.

        option flags update rule:

        1. ``()`` : do not update options
        2. ``('-a', '-b')`` : replace options
        3. ``(..., '-c')`` : append options
        4. ``({'-a': '-A'})`` : rename options
        5. ``({'-a': '-A'}, ...)`` : rename options, keep options if not in the dict.

        general form:

            ``() | (dict?, ...?, *str)``

        :param options: change option flags
        :param kwargs: change keyword parameters, use `...` to unset parameter
        :return:
        """
        kw = dict(self.kwargs)
        kw['group'] = self.group
        kw['ex_group'] = self.ex_group
        kw['validator'] = self.validator
        kw['validate_on_set'] = self.validate_on_set
        kw['hidden'] = self.hidden
        kw.update(kwargs)

        for k in list(kw.keys()):
            if kw[k] is ...:
                del kw[k]

        cls = type(self)

        if len(self.options) > 0:
            match options:
                case ():
                    return cls(*self.options, **kw)
                case (e, *o) if e is ...:
                    return cls(*self.options, *o, **kw)
                case (dict(d), ):
                    return cls(*self._map_options(d, False), **kw)
                case (dict(d), e) if e is ...:
                    return cls(*self._map_options(d, True), **kw)
                case (dict(d), e, *o) if e is ...:
                    return cls(*self._map_options(d, True), *o, **kw)
                case (dict(d), *o):
                    return cls(*self._map_options(d, False), *o, **kw)
                case _:
                    return cls(*options, **kw)
        else:
            if len(options) > 0:
                raise RuntimeError('cannot change positional argument to optional')

            return cls(**kw)

    def _map_options(self, mapping: dict[str, str], keep: bool) -> list[str]:
        new_opt = []
        for old_opt in self.options:
            try:
                new_opt.append(mapping[old_opt])
            except KeyError:
                if keep:
                    new_opt.append(old_opt)
        return new_opt


@overload
def argument(*options: str,
             action: Actions = ...,
             nargs: Union[int, Nargs] = ...,
             const: T = ...,
             default: T = ...,
             type: Type | Callable[[str], T] = ...,
             validator: Callable[[T], bool] = ...,
             validate_on_set: bool = True,
             choices: Sequence[str] = ...,
             required: bool = False,
             hidden: bool = False,
             help: str = ...,
             group: str = None,
             ex_group: str = None,
             metavar: str = ...) -> T:
    pass


def argument(*options: str, **kwargs):
    """create an argument attribute

    :param kwargs: Please see ``argparse.ArgumentParser.add_argument`` for detailed.
    """
    if not all([it.startswith('-') for it in options if isinstance(it, str)]):
        raise RuntimeError(f'options should startswith "-". {options}')
    return Argument(*options, **kwargs)


@overload
def pos_argument(option: str, *,
                 nargs: Nargs = None,
                 action: Actions = ...,
                 const=...,
                 default=...,
                 type: Type | Callable[[str], T] = ...,
                 validator: Callable[[T], bool] = ...,
                 validate_on_set: bool = True,
                 choices: Sequence[str] = ...,
                 required: bool = False,
                 help: str = ..., ) -> T:
    pass


def pos_argument(option: str, *, nargs=None, **kwargs):
    """create a positional (non-flag) command-line argument attribute

    :param option: The name for the positional argument shown in usage messages
    :param kwargs: Please see ``argparse.ArgumentParser.add_argument`` for detailed.
    """
    return Argument(metavar=option, nargs=nargs, **kwargs)


@overload
def var_argument(option: str, *,
                 nargs: Nargs = ...,
                 action: Actions = ...,
                 const=...,
                 default=...,
                 type: Type | Callable[[str], T] = ...,
                 validator: Callable[[T], bool] = ...,
                 validate_on_set: bool = True,
                 choices: Sequence[str] = ...,
                 help: str = ...) -> list[T]:
    pass


def var_argument(option: str, *, nargs='*', action='extend', **kwargs):
    """create a variable-length positional argument, suitable for capturing multiple values into a list"""
    return Argument(metavar=option, nargs=nargs, action=action, **kwargs)


class AliasArgument(Argument):
    def __init__(self, *options,
                 aliases: dict[str, Any],
                 **kwargs):
        super().__init__(*options, **kwargs)
        self.aliases = aliases

    def add_argument(self, ap: ArgumentParser, owner):
        super().add_argument(ap, owner)

        primary = self.options[0]
        for name, values in self.aliases.items():
            kw = dict(self.kwargs)
            kw.pop('metavar', None)
            kw.pop('type', None)
            kw['action'] = 'store_const'
            kw['const'] = values
            kw['help'] = f'short for {primary}={values}.'
            ap.add_argument(name, **kw, dest=self.attr)


@overload
def aliased_argument(options: str, *,
                     aliases: dict[str, T],
                     nargs: Nargs = ...,
                     action: Actions = ...,
                     const=...,
                     default=...,
                     type: Type | Callable[[str], T] = ...,
                     validator: Callable[[T], bool] = ...,
                     validate_on_set: bool = True,
                     choices: Sequence[str] = ...,
                     help: str = ...,
                     group: str = None,
                     ex_group: str = None,
                     metavar: str = ...) -> T:
    pass


def aliased_argument(*options: str, aliases: dict[str, T], **kwargs):
    """create an argument that supports shorthand aliases for specific constant values"""
    return AliasArgument(*options, aliases=aliases, **kwargs)


def as_argument(a) -> Argument:
    """cast argument attribute as an :class:`~argp.core.Argument` for type checking framework/IDE."""
    if isinstance(a, Argument):
        return a
    raise TypeError


def foreach_arguments(instance: Union[T, type[T]]) -> Iterable[Argument]:
    """iterating all argument attributes in instance.

    This method will initialize Argument.

    :param instance:
    :return:
    """
    if isinstance(instance, type):
        clazz = instance
    else:
        clazz = type(instance)

    arg_set = set()
    for clz in reversed(clazz.mro()):
        if (ann := getattr(clz, '__annotations__', None)) is not None:
            for attr in ann:
                if isinstance((arg := getattr(clazz, attr, None)), Argument) and attr not in arg_set:
                    arg_set.add(attr)
                    yield arg


def new_parser(instance: Union[T, type[T]], reset=False, **kwargs) -> ArgumentParser:
    """Create ``ArgumentParser`` for instance.

    :param instance:
    :param reset: reset argument attributes. do nothing if *instance* isn't an instance.
    :param kwargs: keywords for creating :class:`argparse.ArgumentParser`.
    :return:
    """
    if isinstance(instance, AbstractParser) or (isinstance(instance, type) and issubclass(instance, AbstractParser)):
        usage = instance.USAGE
        if isinstance(usage, list):
            usage = '\n       '.join(usage)
        kwargs.setdefault('usage', usage)
        kwargs.setdefault('description', instance.DESCRIPTION)
        kwargs.setdefault('formatter_class', argparse.RawTextHelpFormatter)
        epilog = instance.EPILOG
        if callable(epilog):
            epilog = epilog()
        kwargs.setdefault('epilog', epilog)

    ap = ArgumentParser(**kwargs)

    groups: dict[str, list[Argument]] = collections.defaultdict(list)

    # setup non-grouped arguments
    mu_ex_groups: dict[str, argparse._ActionsContainer] = {}
    for arg in foreach_arguments(instance):
        if instance is not None and not isinstance(instance, type) and reset:
            arg.__delete__(instance)

        if arg.group is not None:
            groups[arg.group].append(arg)
            continue
        elif arg.ex_group is not None:
            try:
                tp = mu_ex_groups[arg.ex_group]
            except KeyError:
                # XXX current Python does not support add title and description into mutually exclusive group
                #   so the message in ex_group is dropped.
                mu_ex_groups[arg.ex_group] = tp = ap.add_mutually_exclusive_group()

            if arg.required:
                tp.required = True
        else:
            tp = ap

        arg.add_argument(tp, instance)

    # setup grouped arguments
    for group, args in groups.items():
        pp = ap.add_argument_group(group)
        mu_ex_groups: dict[str, argparse._ActionsContainer] = {}

        for arg in args:
            if arg.ex_group is not None:
                try:
                    tp = mu_ex_groups[arg.ex_group]
                except KeyError:
                    mu_ex_groups[arg.ex_group] = tp = pp.add_mutually_exclusive_group()

                if arg.required:
                    tp.required = True
            else:
                tp = pp

            arg.add_argument(tp, instance)

    return ap


def new_command_parser(parsers: dict[str, Union[AbstractParser, type[AbstractParser]]],
                       usage: str = None,
                       description: str = None,
                       reset=False) -> ArgumentParser:
    """Create ``ArgumentParser`` for :class:`~argp.core.AbstractParser` s.

    :param parsers: dict of command to :class:`~argp.core.AbstractParser`.
    :param usage: parser usage
    :param description: parser description
    :param reset: reset argument attributes. do nothing if *parsers*'s value isn't an instance.
    :return:
    """
    ap = ArgumentParser(
        usage=usage,
        description=description,
        formatter_class=argparse.RawDescriptionHelpFormatter
    )

    sp = ap.add_subparsers()

    for cmd, pp in parsers.items():
        ppap = new_parser(pp, reset=reset)
        ppap.set_defaults(main=pp)
        sp.add_parser(cmd, help=pp.DESCRIPTION, parents=[ppap], add_help=False)

    return ap


def set_options(instance: T, result: argparse.Namespace) -> T:
    """set argument attributes from ``argparse.Namespace`` .

    :param instance:
    :param result:
    :return: *instance* itself.
    """
    for arg in foreach_arguments(instance):
        try:
            value = getattr(result, arg.attr)
        except AttributeError:
            pass
        else:
            arg.__set__(instance, value)

    return instance


def parse_args(instance: T, args: list[str] = None) -> T:
    """Parse the provided list of command-line arguments and apply the parsed values to the given instance

    :param instance: An instance of a class derived from :class:`AbstractParser`
    :param args: A list of strings representing command-line arguments. If ``None``, uses ``sys.argv[1:]``
    :return: The same instance, with attributes populated
    """
    ap = new_parser(instance, reset=True)
    ot = ap.parse_args(args)
    if ap.exit_status != 0:
        raise RuntimeError(f'exit ({ap.exit_status}): {ap.exit_message}')
    return set_options(instance, ot)


def parse_command_args(parsers: dict[str, Union[AbstractParser, type[AbstractParser]]],
                       args: list[str] = None,
                       usage: str = None,
                       description: str = None,
                       parse_only=False,
                       system_exit: bool | Type[BaseException] = True) -> AbstractParser | ArgumentParsingResult | None:
    """Parse command-line arguments for subcommands, each associated with a different parser class

    :param parsers: dict of command to :class:`~argp.core.AbstractParser`.
    :param args: List of strings representing the command-line input (e.g. `sys.argv[1:]`). If ``None``, defaults to current process args
    :param usage: Optional usage string to override the auto-generated help
    :param description: Optional description for the main parser
    :param parse_only: If True, does not run the parser’s ``.run()`` method.
    :param system_exit: If True (default), calls ``sys.exit`` on parse errors. Set to False to return errors as result objects. You can also pass a custom exception type to raise on failure.
    :return: The parser instance that handled the command (or an :class:`ArgumentParsingResult` if ``parse_only`` or ``system_exit=False``)
    """
    parser = new_command_parser(parsers, usage, description, reset=True)
    result = parser.parse_args(args)

    ret = ArgumentParsingResult.of(parser)
    if not ret:
        if system_exit is True:
            if ret.exit_status != 0:
                parser.print_usage(sys.stderr)
                print(ret.exit_message, file=sys.stderr)
            sys.exit(ret.exit_status)
        elif system_exit is False:
            return ret
        elif issubclass(system_exit, BaseException):
            raise system_exit(ret.exit_status)
        else:
            sys.exit(ret.exit_status)

    pp: AbstractParser = getattr(result, 'main', None)
    if isinstance(pp, type):
        pp = pp()

    if pp is not None:
        set_options(pp, result)

    if parse_only:
        return pp

    if pp is not None:
        pp.run()

    return pp


@overload
def print_help(instance: T, file: TextIO = sys.stdout):
    pass


@overload
def print_help(instance: T, file: Literal[None]) -> str:
    pass


def print_help(instance: T, file: TextIO = sys.stdout):
    """print help to stdout"""
    buf = None
    if file is None:
        import io
        buf = file = io.StringIO()

    new_parser(instance).print_help(file)
    if buf is not None:
        return buf.getvalue()


def with_defaults(instance: T) -> T:
    """Initialize all argument attributes by assign the default value if provided.

    :param instance:
    :return: *instance* itself
    """
    for arg in foreach_arguments(instance):
        try:
            value = arg.default
        except ValueError:
            arg.__delete__(instance)
        else:
            arg.__set__(instance, value)
    return instance


def as_dict(instance: T) -> dict[str, Any]:
    """collect all argument attributes into a dictionary with attribute name to its value.

    :param instance: An instance of a class derived from :class:`AbstractParser`
    :return: A dictionary mapping argument attribute names to their current values
    """
    ret = {}
    for arg in foreach_arguments(instance):
        try:
            value = arg.__get__(instance)
        except AttributeError:
            pass
        else:
            ret[arg.attr] = value
    return ret


def copy_argument(opt: T, ref, **kwargs) -> T:
    """copy argument from ref to opt

    :param opt
    :param ref:
    :param kwargs:
    :return:
    """
    shadow = ShadowOption(ref, **kwargs)

    for arg in foreach_arguments(opt):
        try:
            value = getattr(shadow, arg.attr)
        except AttributeError:
            pass
        else:
            # print('set', arg.attr, value)
            arg.__set__(opt, value)
    return opt


class ShadowOption:
    """Shadow options, used to pass wrapped :class:`AbstractOptions`
    """

    def __init__(self, ref, **kwargs):
        self.__ref = ref
        self.__kwargs = kwargs

    def __getattr__(self, attr: str):
        if attr in self.__kwargs:
            return self.__kwargs[attr]

        if attr.startswith('_') and attr[1:] in self.__kwargs:
            return self.__kwargs[attr[1:]]

        if hasattr(self.__ref, attr):
            return getattr(self.__ref, attr)

        raise AttributeError(attr)
