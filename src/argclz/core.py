from __future__ import annotations

import abc
import argparse
import collections
import sys
from collections.abc import Sequence, Iterable, Callable
from typing import Type, TypeVar, Literal, overload, Any, Optional, get_type_hints, TextIO

from typing_extensions import Self

__all__ = [
    # parser
    'AbstractParser',
    'new_parser',
    'parse_args',
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


class ArgumentParserInterrupt(RuntimeError):
    """(internal) Error raised when any error occurs during command-line parsing."""

    def __init__(self, status: int, message: str | None):
        """
        :param status: error code
        :param message: error message
        """
        if message is None:
            super().__init__(f'exit {status}')
        else:
            super().__init__(f'exit {status}: {message}')

        self.status = status
        self.message = message


class ArgumentParser(argparse.ArgumentParser):
    """(internal) override ``argparse.ArgumentParser``."""

    def exit(self, status: int = 0, message: str = None):
        raise ArgumentParserInterrupt(status, message)

    def error(self, message: str):
        raise ArgumentParserInterrupt(2, message)


class AbstractParser(metaclass=abc.ABCMeta):
    """Commandline parser."""

    USAGE: str | list[str] = None
    """parser usage."""

    DESCRIPTION: str = None
    """parser description. Could be override as a method if its content is dynamic-generated."""

    EPILOG: str = None
    """parser epilog. Could be override as a method if its content is dynamic-generated."""

    def __new__(cls, *args, **kwargs):
        obj = object.__new__(cls)
        with_defaults(obj)
        return obj

    @classmethod
    def new_parser(cls, **kwargs) -> ArgumentParser:
        """create an :class:`~argclz.core.ArgumentParser`.

        :param kwargs: keyword parameters to ``argparse.ArgumentParser``
        :return: an ArgumentParser.
        """
        return new_parser(cls, **kwargs)

    def main(self, args: list[str] | None = None, *,
             parse_only=False,
             system_exit: Type[BaseException] = SystemExit) -> AbstractParser:
        """parsing the commandline input *args* and call :meth:`~argclz.core.ArgumentParser.run()`.

        :param args: command-line arguments. If omitted, use ``sys.args``.
        :param parse_only: parse command-line arguments only, do not raise error and invoke :meth:`~argclz.core.ArgumentParser.run()`
        :param system_exit: error raised when commandline parsed fail.
        :return: parser itself. If it has sub command, return sub parser when used.
        """
        parser = self.new_parser(reset=True)

        try:
            result = parser.parse_args(args)
        except ArgumentParserInterrupt as e:
            exit_status = e.status
            exit_message = e.message
            result = None
        else:
            exit_status = None
            exit_message = None
            set_options(self, result)

        from .commands import init_sub_command
        pp = init_sub_command(self)
        if pp is not self and result is not None:
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

        pp.run()

        return pp

    def run(self):
        """called after :meth:`~argclz.core.ArgumentParser.main()`.
        Used for runs the main execution logic of the object"""
        pass

    def __str__(self):
        return type(self).__name__

    def __repr__(self):
        """print key value pair content"""
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
    """
    (internal) Do not use class directly.

    Commandline argument descriptor (https://docs.python.org/3/glossary.html#term-descriptor).
    Carried the arguments pass to ``argparse.ArgumentParser.add_argument``.

    """

    def __init__(self, *options,
                 validator: Callable[[T], bool] = None,
                 group: str = None,
                 ex_group: str = None,
                 hidden: bool = False,
                 **kwargs):
        """

        :param options: options
        :param validator: argument validator.
        :param group: argument group.
        :param ex_group: mutually exclusive group.
        :param hidden: hide this argument from help document
        :param kwargs:
        """
        from .validator import Validator
        if len(options) > 0 and isinstance(options[-1], Validator):
            if validator is not None:
                raise RuntimeError()
            validator = options[-1]
            options = options[:-1]

        if not all([it.startswith('-') for it in options]):
            raise RuntimeError(f'options should startswith "-". {options}')

        if isinstance(validator, Validator):
            validator = validator.freeze()

        self.attr = None
        self.attr_type = Any
        self.group = group
        self.ex_group = ex_group
        self.validator = validator
        self.options = options
        self.hidden = hidden
        self._kwargs = kwargs  # original kwargs
        self.kwargs = dict(kwargs)

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

        from ._types import complete_arg_kwargs
        complete_arg_kwargs(self)

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
        if (validator := self.validator) is not None:
            from .validator import Validator, ValidatorFailError
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

    def add_argument(self, ap: argparse._ActionsContainer, instance):
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
                     option: str | dict[str, str] = None,
                     *options: str,
                     action: Actions = None,
                     nargs: int | Nargs = None,
                     const: T = None,
                     default: T = None,
                     type: Type | Callable[[str], T] = None,
                     validator: Callable[[T], bool] = None,
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

        1. ``()``, ``(...)`` : do not update options
        2. ``('-a', '-b')`` : replace options
        3. ``(..., '-c')`` : additional options
        4. ``({'-a': '-A'})`` : rename options
        5. ``({'-a': ...})`` : remove options
        6. ``({'-a': '-A', '-b': ...}, '-c')`` : rename '-a', remove '-b', add '-c'

        general form:

            ``() | (dict?, ...?, *str)``

        :param options: change option flags
        :param kwargs: change keyword parameters, use `...` to unset parameter
        :return:
        """
        kw = dict(self._kwargs)  # use original kwargs
        kw['group'] = self.group
        kw['ex_group'] = self.ex_group
        kw['validator'] = self.validator
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
                    return cls(*self._map_options(d), **kw)
                case (dict(d), *o):
                    return cls(*self._map_options(d), *o, **kw)
                case _:
                    return cls(*options, **kw)
        else:
            if len(options) > 0:
                raise RuntimeError('cannot change positional argument to optional')

            return cls(**kw)

    def _map_options(self, mapping: dict[str, str]) -> list[str]:
        ret = []
        for old_opt in self.options:
            try:
                new_opt = mapping[old_opt]
            except KeyError:
                ret.append(old_opt)
            else:
                if new_opt is not ...:
                    ret.append(new_opt)
        return ret


@overload
def argument(*options: str,
             action: Actions = ...,
             nargs: int | Nargs = ...,
             const: T = ...,
             default: T = ...,
             type: Type | Callable[[str], T] = ...,
             validator: Callable[[T], bool] = ...,
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

    **Usage**

    >>> class Example:
    ...     a: str = argument('-a')

    **Type (caster)**

    The parameter ``type`` usually can be infered via the annotation of target attribute,
    like the `a: str` in above example.

    There are some special rules to treat common type:

    - **Literal types**: ``Literal[...]`` annotations create a caster that restricts values to the specified literals.
    - **Boolean flags**: annotating with ``bool`` automatically sets up a `store_true` or `store_false` action, making the option a flag.
    - **Container types**: ``list[T]`` annotations infer a repeated option with `append` (or `extend`) action, converting each input to type ``T``.
    - **Tuple types**: tuple annotations (e.g. ``tuple[int, ...]``) use a comma-separated parser to split and convert values into a tuple of ``T``.

    If the default type infered does not fit your application, you can give it directly.

    **Validator**

    Although parameter ``type`` can handle some validation works, it is ignored when user
    assign value to the attribute directly. The parameter ``validator`` is used to perform the assignment
    validation work and raise a ``ValueError`` (normal case) if any improper assignments.

    The parameter ``validator`` has been treated specially when use :attr:`~argclz.validator`, which it
    can put at lastest position of ``options``

    >>> from argclz import argument, validator
    >>> class Example:
    ...     a: str = argument('-a', validator.str.match(r'\d+'))

    :param options: options strings
    :param action: argument action. Please see ``argparse.ArgumentParser.add_argument(action)`` for detailed.
    :param nargs: number of following values. Please see ``argparse.ArgumentParser.add_argument(nargs)`` for detailed.
    :param const: Please see ``argparse.ArgumentParser.add_argument(const)`` for detailed.
    :param default: default value of argument. Please see ``argparse.ArgumentParser.add_argument(default)`` for detailed.
    :param type: type caster with signature ``(str) -> T``. Please see ``argparse.ArgumentParser.add_argument(type)`` for detailed.
    :param validator: value validator with signature ``(T) -> bool``.
    :param choices: Please see ``argparse.ArgumentParser.add_argument(choices)`` for detailed.
    :param required: Please see ``argparse.ArgumentParser.add_argument(required)`` for detailed.
    :param hidden: hide this argument from help document.
    :param help: help document for this argument.
    :param group: group name of this argument.
    :param ex_group: the mutually exclusive group name of this argument.
    :param metavar: name of argument value. Please see ``argparse.ArgumentParser.add_argument(metavar)`` for detailed.
    """
    return Argument(*options, **kwargs)


@overload
def pos_argument(option: str,
                 validator: Callable[[T], bool] = ..., *,
                 nargs: Nargs = None,
                 action: Actions = ...,
                 const=...,
                 default=...,
                 type: Type | Callable[[str], T] = ...,
                 choices: Sequence[str] = ...,
                 required: bool = False,
                 help: str = ..., ) -> T:
    pass


def pos_argument(option: str, validator: Callable[[T], bool] = ..., *, nargs=None, **kwargs):
    """create a positional (non-flag) command-line argument attribute.

    **Usage**

    >>> class Example:
    ...     a: str = pos_argument('A')

    shorten for ``argument(metavar=option, nargs=nargs, validator=validator, **kwargs)``

    :param option: The name for the positional argument shown in usage messages
    :param validator: value validator with signature ``(T) -> bool``.
    :param nargs: number of following values. Please see ``argparse.ArgumentParser.add_argument(nargs)`` for detailed.
    :param action: argument action. Please see ``argparse.ArgumentParser.add_argument(action)`` for detailed.
    :param const: Please see ``argparse.ArgumentParser.add_argument(const)`` for detailed.
    :param default: default value of argument. Please see ``argparse.ArgumentParser.add_argument(default)`` for detailed.
    :param type: type caster with signature ``(str) -> T``. Please see ``argparse.ArgumentParser.add_argument(type)`` for detailed.
    :param choices: Please see ``argparse.ArgumentParser.add_argument(choices)`` for detailed.
    :param required: Please see ``argparse.ArgumentParser.add_argument(required)`` for detailed.
    :param help: help document for this argument.
    """
    if validator is not ...:
        kwargs['validator'] = validator
    return Argument(metavar=option, nargs=nargs, **kwargs)


@overload
def var_argument(option: str,
                 validator: Callable[[T], bool] = ..., *,
                 nargs: Nargs = ...,
                 action: Actions = ...,
                 type: Type | Callable[[str], T] = ...,
                 help: str = ...) -> list[T]:
    pass


def var_argument(option: str, validator: Callable[[T], bool] = ..., *, nargs='*', action='extend', **kwargs):
    """
    create a variable-length positional argument, suitable for capturing multiple values into a list.

    **Usage**

    >>> class Example:
    ...     a: list[str] = var_argument('A')

    shorten for ``argument(metavar=option, nargs='*', action='extend', validator=validator, **kwargs)`` by default.

    :param option: The name for the vary-length positional argument shown in usage messages
    :param validator:  value validator with signature ``(T) -> bool``.
    :param nargs: number of following values. Please see ``argparse.ArgumentParser.add_argument(nargs)`` for detailed.
    :param action: argument action. Please see ``argparse.ArgumentParser.add_argument(action)`` for detailed.
    :param type: type caster with signature ``(str) -> T``. Please see ``argparse.ArgumentParser.add_argument(type)`` for detailed.
    :param help: help document for this argument.
    """
    if validator is not ...:
        kwargs['validator'] = validator
    return Argument(metavar=option, nargs=nargs, action=action, **kwargs)


class AliasArgument(Argument):
    """
    (internal) Do not use class directly.
    """

    def __init__(self, *options,
                 aliases: dict[str, Any],
                 **kwargs):
        super().__init__(*options, **kwargs)
        self.aliases = aliases

    def add_argument(self, ap: argparse._ActionsContainer, owner):
        gp = ap.add_mutually_exclusive_group(required=self.required)
        super().add_argument(gp, owner)

        primary = self.options[0]
        for name, values in self.aliases.items():
            kw = dict(self.kwargs)
            kw.pop('metavar', None)
            kw.pop('type', None)
            kw['action'] = 'store_const'
            kw['const'] = values
            kw['help'] = f'short for {primary}={values}.'
            gp.add_argument(name, **kw, dest=self.attr)


@overload
def aliased_argument(options: str, *,
                     aliases: dict[str, T],
                     nargs: Nargs = ...,
                     action: Actions = ...,
                     const=...,
                     default=...,
                     type: Type | Callable[[str], T] = ...,
                     validator: Callable[[T], bool] = ...,
                     choices: Sequence[str] = ...,
                     help: str = ...,
                     group: str = None,
                     ex_group: str = None,
                     metavar: str = ...) -> T:
    pass


def aliased_argument(*options: str, aliases: dict[str, T], **kwargs):
    """
    create an argument that supports shorthand aliases for specific constant values.

    **Usage**

    >>> class Example:
    ...     level: str = aliased_argument(
    ...         '--level',
    ...         aliases={
    ...             '--low': 'low',
    ...             '--mid': 'middle',
    ...             '--high': 'high',
    ...         },
    ...         choices=('low', 'middle', 'high')
    ...     )

    :param options: options strings
    :param aliases: a dictionary maps options to value.
    :param action: argument action. Please see ``argparse.ArgumentParser.add_argument(action)`` for detailed.
    :param nargs: number of following values. Please see ``argparse.ArgumentParser.add_argument(nargs)`` for detailed.
    :param const: Please see ``argparse.ArgumentParser.add_argument(const)`` for detailed.
    :param default: default value of argument. Please see ``argparse.ArgumentParser.add_argument(default)`` for detailed.
    :param type: type caster with signature ``(str) -> T``. Please see ``argparse.ArgumentParser.add_argument(type)`` for detailed.
    :param validator: value validator with signature ``(T) -> bool``.
    :param choices: Please see ``argparse.ArgumentParser.add_argument(choices)`` for detailed.
    :param required: Please see ``argparse.ArgumentParser.add_argument(required)`` for detailed.
    :param hidden: hide this argument from help document.
    :param help: help document for this argument.
    :param group: group name of this argument.
    :param ex_group: the mutually exclusive group name of this argument.
    :param metavar: name of argument value. Please see ``argparse.ArgumentParser.add_argument(metavar)`` for detailed.
    """
    return AliasArgument(*options, aliases=aliases, **kwargs)


def as_argument(a) -> Argument:
    """cast argument attribute as an :class:`~argclz.core.Argument` for type checking framework/IDE."""
    if isinstance(a, Argument):
        return a
    raise TypeError


def foreach_arguments(instance: T | Type[T]) -> Iterable[Argument]:
    """iterating all argument attributes in instance.

    :param instance: any instance that contains ``argument``.
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


def new_parser(instance: T | Type[T], reset=False, **kwargs) -> ArgumentParser:
    """Create ``ArgumentParser`` for instance.

    :param instance: any instance that contains ``argument``.
    :param reset: reset argument attributes. do nothing if *instance* isn't an instance.
    :param kwargs: Please see ``argparse.ArgumentParser(**kwargs)`` for detailed.
    :return:
    """
    if isinstance(instance, AbstractParser) or (isinstance(instance, type) and issubclass(instance, AbstractParser)):
        usage = instance.USAGE
        if isinstance(usage, list):
            usage = '\n       '.join(usage)
        kwargs.setdefault('usage', usage)

        description = instance.DESCRIPTION
        if callable(description):
            description = description()
        kwargs.setdefault('description', description)

        epilog = instance.EPILOG
        if callable(epilog):
            epilog = epilog()
        kwargs.setdefault('epilog', epilog)

        kwargs.setdefault('formatter_class', argparse.RawTextHelpFormatter)

    ap = ArgumentParser(**kwargs)

    groups: dict[str, list[Argument]] = collections.defaultdict(list)

    from .commands import get_sub_command_group
    if (sub := get_sub_command_group(instance)) is not None:
        sub.add_parser(ap)

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


def set_options(instance: T, result: argparse.Namespace) -> T:
    """set argument to ``instance``'s attributes from ``argparse.Namespace`` .

    :param instance: any instance that contains ``argument``.
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

    from .commands import get_sub_command_group
    if (sub := get_sub_command_group(instance)) is not None:
        try:
            value = getattr(result, sub.attr)
        except AttributeError:
            sub.__set__(instance, None)
        else:
            sub.__set__(instance, value)

    return instance


def parse_args(instance: T, args: list[str] = None) -> T:
    """Parse the command-list arguments and apply the parsed values to the given instance

    :param instance: any instance that contains ``argument``.
    :param args: A list of strings representing command-line arguments. If ``None``, uses ``sys.argv``
    :return: ``instance`` itself, with attributes populated
    """
    ap = new_parser(instance, reset=True)
    ot = ap.parse_args(args)
    return set_options(instance, ot)


@overload
def print_help(instance, file: TextIO = sys.stdout, prog: str = None):
    pass


@overload
def print_help(instance, file: Literal[None], prog: str = None) -> str:
    pass


def print_help(instance, file: TextIO = sys.stdout, prog: str = None):
    """
    print help document.

    :param instance: any instance that contains ``argument``.
    :param file: output stream.
    :param prog: program name.
    :return: help document string if ``file`` is ``None``. Otherwise, nothing return.
    """
    buf = None
    if file is None:
        import io
        buf = file = io.StringIO()

    if not isinstance(instance, ArgumentParser):
        instance = new_parser(instance, prog=prog)

    instance.print_help(file)
    if buf is not None:
        return buf.getvalue()
    else:
        return None


def with_defaults(instance: T) -> T:
    """Initialize all argument attributes by assign the default value if provided.

    :param instance: any instance that contains ``argument``.
    :return: *instance* itself, with attributes initialized with proper default.
    """
    for arg in foreach_arguments(instance):
        try:
            value = arg.default
        except ValueError:
            arg.__delete__(instance)
        else:
            arg.__set__(instance, value)

    from .commands import get_sub_command_group
    if (sub := get_sub_command_group(instance)) is not None:
        sub.__set__(instance, None)

    return instance


@overload
def as_dict(instance: list[T]) -> list[dict[str, Any]]:
    pass


@overload
def as_dict(instance: T) -> dict[str, Any]:
    pass


def as_dict(instance):
    """
    Collect all argument attributes into a dictionary with attribute name to its value.
    It *instance* is a list, it works like ``list(map(as_dict, instance))``.

    :param instance: any instance that contains ``argument``.
    :return: A dictionary mapping argument attribute names to their values
    """
    if isinstance(instance, list):
        if len(instance) == 0:
            return []

        return list(map(as_dict, instance))

    ret = {}
    for arg in foreach_arguments(instance):
        try:
            value = arg.__get__(instance)
        except AttributeError:
            pass
        else:
            ret[arg.attr] = value

    from .commands import get_sub_command_group
    if (sub := get_sub_command_group(instance)) is not None:
        try:
            value = sub.__get__(instance)
        except AttributeError:
            pass
        else:
            ret[sub.attr] = value

    return ret


def copy_argument(opt: T, ref, **kwargs) -> T:
    """copy argument from ref to opt

    :param opt: any instance that contains ``argument``.
    :param ref: any instance that contains ``argument``.
    :param kwargs: overwrite argument value mapping.
    :return: ``opt`` itself.
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

    from .commands import get_sub_command_group
    if (sub := get_sub_command_group(opt)) is not None:
        try:
            value = getattr(shadow, opt)
        except AttributeError:
            pass
        else:
            sub.__set__(opt, value)

    return opt


class ShadowOption:
    """
    (internal) Do not use class directly.

    Shadow options, used to pass wrapped :class:`AbstractOptions`
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
