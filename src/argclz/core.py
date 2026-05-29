from __future__ import annotations

import abc
import argparse
import collections
import sys
import warnings
from collections.abc import Sequence, Iterable, Callable
from typing import TYPE_CHECKING, Type, TypeVar, Literal, overload, Any, get_type_hints, TextIO

from typing_extensions import Self

if TYPE_CHECKING:
    from .validator import Validator

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
    'argument_group',
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

ARGCLZ_NAMESPACE = '__argclz_namespace__'


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

    def exit(self, status: int = 0, message: str | None = None):
        # raise our exception instead of SystemExit
        raise ArgumentParserInterrupt(status, message)

    def error(self, message: str):
        # raise our exception instead of SystemExit
        raise ArgumentParserInterrupt(2, message)


class AbstractParser(metaclass=abc.ABCMeta):
    """Commandline parser.

    >>> class Main(AbstractParser):
    ...     a: int = argument('-a')
    ...     def run(self):
    ...         pass
    ... Main().main()

    """

    USAGE: str | list[str] | None = None
    """parser usage."""

    DESCRIPTION: str | None = None
    """parser description. Could be override as a method if its content is dynamic-generated."""

    ARGUMENT_GROUP_LIST: list[str] | Callable[[str], int] | None = None
    """argument group list"""

    EPILOG: str | Callable[[], str] | None = None
    """parser epilog. Could be override as a method if its content is dynamic-generated."""

    def __new__(cls, *args, **kwargs):
        obj = object.__new__(cls)
        with_defaults(obj)
        return obj

    @classmethod
    def new_parser(cls, **kwargs) -> ArgumentParser:
        """create an :class:`~argclz.core.ArgumentParser`.

        Subclass can overwrite this method to pass additional argument to
        create an :class:`argparse.ArgumentParser`.

        **Note** Using :func:`~argclz.core.new_parser` to create an :class:`argparse.ArgumentParser`.

        :param kwargs: keyword parameters to :class:`argparse.ArgumentParser`
        :return: an ArgumentParser.
        """
        return new_parser(cls, **kwargs)

    def main(self, args: list[str] | None = None, *,
             parse_only=False,
             system_exit: Type[BaseException] = SystemExit) -> AbstractParser:
        """parsing the commandline input *args* and call :meth:`~argclz.core.ArgumentParser.run()`.

        :param args: command-line arguments. If omitted, use ``sys.args``.
        :param parse_only: parse command-line arguments only, do not raise error and invoke :meth:`~argclz.core.ArgumentParser.run()`
        :param system_exit: error raised when commandline parsed fail. default raise ``SystemExit``.
        :return: parser itself. If it has sub command, return sub parser when used.
        """
        parser = self.new_parser()

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
            elif isinstance(system_exit, type) and issubclass(system_exit, BaseException):
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

    # TODO do we need this repr which goes all of the arguments and properties?
    # def __repr__(self):
    #     """print key value pair content"""
    #     self_type = type(self)
    #     ret = []
    #     for a_name in dir(self_type):
    #         a_value = getattr(self_type, a_name)
    #         if isinstance(a_value, Argument) and not a_name.startswith('_'):
    #             try:
    #                 ret.append(f'{a_name} = {a_value.__get__(self, self_type)}')
    #             except:
    #                 ret.append(f'{a_name} = <error>')
    #         elif isinstance(a_value, property):
    #             try:
    #                 ret.append(f'{a_name} = {a_value.__get__(self, self_type)}')
    #             except:
    #                 ret.append(f'{a_name} = <error>')
    #
    #     return '\n'.join(ret)


class Argument(object):
    """
    (internal) Do not use class directly.

    Commandline argument descriptor (https://docs.python.org/3/glossary.html#term-descriptor).
    Carried the arguments pass to ``argparse.ArgumentParser.add_argument``.

    """

    def __init__(self, *options,
                 validator: Callable[[T], bool] | None = None,
                 group: str | argument_group | None = None,
                 ex_group: str | None = None,
                 hidden: bool = False,
                 **kwargs):
        """

        :param options: options
        :param validator: argument validator.
        :param group: argument group.
        :param ex_group: (Deprecated) mutually exclusive group.
        :param hidden: hide this argument from help document
        :param kwargs:
        """
        from .validator import Validator
        if len(options) > 0 and isinstance(options[-1], Validator):
            if validator is not None:
                raise RuntimeError('multiple validators in both last position and keyword arguments.')
            validator = options[-1]
            options = options[:-1]

        if not all([it.startswith('-') for it in options]):
            raise RuntimeError(f'options should startswith "-". {options}')

        if isinstance(validator, Validator):
            validator = validator.freeze()

        if ex_group is not None and group is None:
            # Deprecated parameter
            warnings.warn('ex_group is deprecated', DeprecationWarning)
            group = argument_group(ex_group, exclusive=True)

        self.attr = None
        self.attr_type = Any
        self.group = group
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
    def metavar(self) -> str | None:
        return self.kwargs.get('metavar', None)

    @property
    def choices(self) -> tuple[Any, ...] | None:
        return self.kwargs.get('choices', None)

    @property
    def required(self) -> bool:
        return self.kwargs.get('required', False)

    @property
    def type(self) -> Type | Callable[[str], T]:
        try:
            return self.kwargs['type']
        except KeyError:
            pass

        if self.attr is None:
            raise RuntimeError('Argument is not setup properly.')

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
    def help(self) -> str | None:
        return self.kwargs.get('help', None)

    def __set_name__(self, owner: Type, name: str):
        if self.attr is not None:
            raise RuntimeError(f'Argument reused by {self.attr} and {name}')

        self.attr = name
        self.attr_type = get_type_hints(owner).get(name, Any)

        from ._types import complete_arg_kwargs
        complete_arg_kwargs(self)

    def __get__(self, instance, owner=None):
        if instance is None:
            if owner is not None:  # ad-hoc for the document building
                self.__doc__ = self.help
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
            namespace = {}
            setattr(instance, ARGCLZ_NAMESPACE, namespace)

    def add_argument(self, ap: argparse._ActionsContainer, instance):
        """Add this into `argparse.ArgumentParser`.

        :param ap:
        :param instance:
        :return:
        """
        try:
            kwargs = dict(self.kwargs)
            help_text = kwargs.pop('help', None)
            help_text = help_text if not self.hidden else argparse.SUPPRESS
            return ap.add_argument(*self.options, **kwargs, help=help_text, dest=self.attr)
        except TypeError as e:
            if isinstance(instance, type):
                name = instance.__name__
            else:
                name = type(instance).__name__
            raise RuntimeError(f'{name}.{self.attr} : ' + repr(e)) from e

    # noinspection PyOverloads
    @overload  # this overload is used to show the actual keyword arguments.
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
        kw['group'] = self._copy_group(self.group)
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

    @classmethod
    def _copy_group(cls, group: str | argument_group | None):

        match group:
            case None | str():
                return group
            case argument_group(name, description, exclusive, required):
                # argument_group  has internal attributes, so we create a new clone.
                return argument_group(name, description, exclusive=exclusive, required=required)
            case _:
                raise TypeError()

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


# noinspection PyOverloads
@overload  # this overload is used to show the actual keyword arguments.
def argument(*options: str,
             action: Actions = ...,
             nargs: int | Nargs = ...,
             const: T = ...,
             default: T = ...,
             type: Type | Callable[[str], T] = ...,
             validator: Callable[[T], bool] = ...,
             choices: Sequence[T] = ...,
             required: bool = False,
             hidden: bool = False,
             help: str = ...,
             group: str | argument_group | None = None,
             metavar: str = ...) -> T:
    ...


def argument(*options, **kwargs) -> Any:
    r"""create an argument attribute

    **Usage**

    >>> class Example:
    ...     a: str = argument('-a')

    **Type (caster)**

    The parameter ``type`` usually can be inferred via the annotation of target attribute,
    like the `a: str` in above example.

    There are some special rules to treat common type:

    - **Literal types**: ``Literal[...]`` annotations create a caster that restricts values to the specified literals.
    - **Boolean flags**: annotating with ``bool`` automatically sets up a `store_true` or `store_false` action, making the option a flag.
    - **Container types**: ``list[T]`` annotations infer a repeated option with `append` (or `extend`) action, converting each input to type ``T``.
    - **Tuple types**: tuple annotations (e.g. ``tuple[int, ...]``) use a comma-separated parser to split and convert values into a tuple of ``T``.

    If the default type inferred does not fit your application, you can give it directly.

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
    :param metavar: name of argument value. Please see ``argparse.ArgumentParser.add_argument(metavar)`` for detailed.
    """
    return Argument(*options, **kwargs)


# noinspection PyOverloads
@overload  # this overload is used to show the actual keyword arguments.
def pos_argument(option: str,
                 validator: Callable[[T], bool] = None, *,
                 nargs: Nargs | None = None,
                 action: Actions = ...,
                 const: T = ...,
                 default: T = ...,
                 type: Type | Callable[[str], T] = ...,
                 choices: Sequence[str] = ...,
                 required: bool = False,
                 help: str = ...) -> T:
    ...


def pos_argument(option: str, validator: Callable[[T], bool] | None = None, *, nargs=None, **kwargs) -> Any:
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
    if validator is not None:
        kwargs['validator'] = validator
    return Argument(metavar=option, nargs=nargs, **kwargs)


# noinspection PyOverloads
@overload  # this overload is used to show the actual keyword arguments.
def var_argument(option: str,
                 validator: Callable[[T], bool] = None, *,
                 nargs: Nargs = ...,
                 action: Actions = ...,
                 type: Type | Callable[[str], T] = ...,
                 help: str = ...) -> list[T]:
    ...


def var_argument(option: str, validator: Callable[[T], bool] | None = None, *, nargs='*', action='extend', **kwargs) -> Any:
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
    if validator is not None:
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

    def add_argument(self, ap: argparse._ActionsContainer, instance):
        gp = ap.add_mutually_exclusive_group(required=self.required)
        result = super().add_argument(gp, instance)

        assert len(self.options) > 0
        primary = self.options[0]
        for name, values in self.aliases.items():
            kw = dict(self.kwargs)
            kw.pop('metavar', None)
            kw.pop('type', None)
            kw.pop('choices', None)
            kw['action'] = 'store_const'
            kw['const'] = values
            kw['help'] = f'short for {primary}={values}.'
            gp.add_argument(name, **kw, dest=self.attr)

        return result


# noinspection PyOverloads
@overload  # this overload is used to show the actual keyword arguments.
def aliased_argument(options: str, *,
                     aliases: dict[str, T],
                     nargs: Nargs = ...,
                     action: Actions = ...,
                     const: T = ...,
                     default: T = ...,
                     type: Type | Callable[[str], T] = ...,
                     validator: Callable[[T], bool] | None = None,
                     choices: Sequence[str] = ...,
                     help: str = ...,
                     group: str | None = None,
                     metavar: str = ...) -> T:
    ...


def aliased_argument(*options: str, aliases: dict[str, T], **kwargs) -> Any:
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
    :param metavar: name of argument value. Please see ``argparse.ArgumentParser.add_argument(metavar)`` for detailed.
    """
    return AliasArgument(*options, aliases=aliases, **kwargs)


def as_argument(a) -> Argument:
    """cast argument attribute as an :class:`~argclz.core.Argument` for type checking framework/IDE."""
    if isinstance(a, Argument):
        return a
    raise TypeError('not an argument')


class argument_group:
    __match_args__ = 'name', 'description', 'exclusive', 'required'

    def __init__(self, name: str = None, description: str = None, *,
                 exclusive=False, required: bool = False):
        """

        :param name: The name of this group.
        :param description: The description of this group
        :param exclusive: mutually exclusive
        :param required: Is this mutually exclusive group required?
        """
        self.name: str | None = name
        self.description: str | None = description
        self.exclusive = exclusive
        self.required: bool = required
        self._attr: str | None = None

    def __set_name__(self, owner, name):
        if self._attr is None:
            self._attr = name

    # noinspection PyOverloads
    @overload  # this overload is used to show the actual keyword arguments.
    def argument(self,
                 *options: str,
                 action: Actions = ...,
                 nargs: int | Nargs = ...,
                 const: T = ...,
                 default: T = ...,
                 type: Type | Callable[[str], T] = ...,
                 validator: Callable[[T], bool] = ...,
                 choices: Sequence[T] = ...,
                 required: bool = False,
                 hidden: bool = False,
                 help: str = ...,
                 metavar: str = ...) -> T:
        ...

    def argument(self,
                 *options, **kwargs) -> Any:
        r"""create an argument under this mutually exclusive group.

        **Usage**

        >>> class Example:
        ...     g = mutually_exclusive_group()
        ...     a: str = g.argument('-a')

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
        :param metavar: name of argument value. Please see ``argparse.ArgumentParser.add_argument(metavar)`` for detailed.
        """
        return Argument(*options, group=self, **kwargs)

    def __eq__(self, other):
        match other:
            case str(name):
                return self.name == name
            case argument_group(name, description) as group:
                return self.name == name and self.description == description and self._attr == group._attr \
                    and self.exclusive == group.exclusive and (not self.exclusive or self.required == group.required)
            case _:
                return False

    def __hash__(self):
        return hash((self._attr, self.name, self.description))


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


def new_parser(instance: T | Type[T], **kwargs) -> ArgumentParser:
    """Create ``ArgumentParser`` for instance.

    :param instance: any instance that contains ``argument``.
    :param kwargs: Please see ``argparse.ArgumentParser(**kwargs)`` for detailed.
    :return: an :class:``~argparse.ArgumentParser`` instance.
    """
    if isinstance(instance, AbstractParser) or (isinstance(instance, type) and issubclass(instance, AbstractParser)):
        kwargs.setdefault('usage', _parser_usage(instance))
        kwargs.setdefault('description', _parser_description(instance))
        kwargs.setdefault('epilog', _parser_epilog(instance))
        # we do not need special handle for help text.
        kwargs.setdefault('formatter_class', argparse.RawTextHelpFormatter)

    ap = ArgumentParser(**kwargs)
    # TODO python 3.14 add keyword color=
    # TODO python 3.14 add keyword suggest_on_error=

    groups: dict[argument_group, list[Argument]] = collections.defaultdict(list)

    from .commands import get_sub_command_group
    if (sub := get_sub_command_group(instance)) is not None:
        sub.add_parser(ap)

    # setup non-grouped arguments
    ex_groups: dict[argument_group, argparse._MutuallyExclusiveGroup] = {}
    for arg in foreach_arguments(instance):
        if (tp := _init_group(ap, groups, ex_groups, arg)) is not None:
            arg.add_argument(tp, instance)

    # setup grouped arguments
    for group, args in _iter_grouped_arguments_in_order(instance, groups):
        pp = ap.add_argument_group(group.name, group.description)

        for arg in args:
            arg.add_argument(pp, instance)

    return ap


def _parser_usage(instance: AbstractParser | Type[AbstractParser]) -> str | None:
    usage = instance.USAGE
    if isinstance(usage, list):
        usage = '\n       '.join(usage)
    return usage


def _parser_description(instance: AbstractParser | Type[AbstractParser]) -> str | None:
    description = instance.DESCRIPTION
    if callable(description):
        description = description()
    return description


def _parser_epilog(instance: AbstractParser | Type[AbstractParser]) -> str | None:
    epilog = instance.EPILOG
    if callable(epilog):
        epilog = epilog()

    assert epilog is None or isinstance(epilog, str)

    # special handler for Dispatch for command sections.
    # it put above epilog, but as part of epilog.
    from argclz.dispatch import Dispatch
    if isinstance(instance, Dispatch) or (isinstance(instance, type) and issubclass(instance, Dispatch)):
        command_help = instance.COMMAND_HELP_DOC
        if command_help is None:
            command_help = instance.build_command_usages()
        elif callable(command_help):
            command_help = command_help()

        assert isinstance(command_help, str)

        if len(command_help):
            if epilog is not None:
                if not command_help.endswith('\n'):
                    command_help += '\n'
                epilog = command_help + "\n" + epilog
            else:
                epilog = command_help

    return epilog


def _init_group(parser: ArgumentParser,
                groups: dict[argument_group, list[Argument]],
                ex_groups: dict[argument_group, argparse._MutuallyExclusiveGroup],
                arg: Argument):
    match arg.group:
        case None:
            return parser

        case str(group):
            # groups is defaultdict, so we do not need to check key exist.
            groups[argument_group(group)].append(arg)
            return None

        case argument_group(exclusive=False) as group:
            # groups is defaultdict, so we do not need to check key exist.
            groups[group].append(arg)
            return None

        case argument_group(None, None, _, required) as group:
            try:
                return ex_groups[group]
            except KeyError:
                ret = parser.add_mutually_exclusive_group(required=required)
                ex_groups[group] = ret
                return ret

        case argument_group(name, description, _, required) as group:
            try:
                return ex_groups[group]
            except KeyError:
                ret = parser.add_argument_group(name, description).add_mutually_exclusive_group(required=required)
                ex_groups[group] = ret
                return ret

        case _:
            raise TypeError()


def _iter_grouped_arguments_in_order(instance: T | Type[T],
                                     groups: dict[argument_group, list[Argument]]) -> Iterable[tuple[argument_group, list[Argument]]]:
    if not isinstance(instance, type):
        instance = type(instance)

    if not issubclass(instance, AbstractParser) or instance.ARGUMENT_GROUP_LIST is None:
        yield from groups.items()

    else:
        name_map_group = {g.name: g for g in groups}
        argument_group_list = instance.ARGUMENT_GROUP_LIST
        if isinstance(argument_group_list, list):
            for name in argument_group_list:
                try:
                    group = name_map_group[name]
                except KeyError:
                    pass
                else:
                    yield group, groups[group]

            for group, args in groups.items():
                if group.name not in argument_group_list:
                    yield group, args

        elif callable(argument_group_list):
            argument_group_list_func = argument_group_list
            argument_group_list = list(name_map_group)
            argument_group_list.sort(key=argument_group_list_func)

            for name in argument_group_list:
                try:
                    group = name_map_group[name]
                except KeyError:
                    pass
                else:
                    yield group, groups[group]

        else:
            raise TypeError('ARGUMENT_GROUP_LIST not a list')


def set_options(instance: T, result: argparse.Namespace) -> T:
    """set argument to ``instance``'s attributes from ``argparse.Namespace`` .

    :param instance: any instance that contains ``argument``.
    :param result:
    :return: *instance* itself.
    """
    for arg in foreach_arguments(instance):
        assert arg.attr is not None

        try:
            value = getattr(result, arg.attr)
        except AttributeError:
            pass
        else:
            arg.__set__(instance, value)

    from .commands import get_sub_command_group
    if (sub := get_sub_command_group(instance)) is not None:
        assert sub.attr is not None

        try:
            value = getattr(result, sub.attr)
        except AttributeError:
            sub.__set__(instance, None)
        else:
            sub.__set__(instance, value)

    return instance


def parse_args(instance: T, args: list[str] | None = None) -> T:
    """Parse the command-list arguments and apply the parsed values to the given instance

    :param instance: any instance that contains ``argument``.
    :param args: A list of strings representing command-line arguments. If ``None``, uses ``sys.argv``
    :return: ``instance`` itself, with attributes populated
    """
    if isinstance(instance, type):
        raise TypeError('not an instance')

    ap = new_parser(instance)
    ot = ap.parse_args(args)
    return set_options(instance, ot)


@overload
def print_help(instance, file: TextIO = sys.stdout, prog: str | None = None) -> None:
    pass


@overload
def print_help(instance, file: Literal[None], prog: str | None = None) -> str:
    pass


def print_help(instance, file: TextIO | None = sys.stdout, prog: str | None = None):
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

    if isinstance(instance, type) and issubclass(instance, AbstractParser):
        # respect AbstractParser custom new_parser
        instance = instance.new_parser(prog=prog)

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
    If *instance* is a list, it works like ``list(map(as_dict, instance))``.

    If ``instance`` is an :class:`~argclz.core.AbstractParser` and has sub commands,
    the returned dict contains the name of the attribute of :func:`~argclz.commands.sub_command_group`
    maps to the corresponding to the class of the sub command.

    :param instance: any instance that contains ``argument``.
    :return: A dictionary mapping argument attribute names to their values
    """
    if isinstance(instance, list):
        if len(instance) == 0:
            return []

        return list(map(as_dict, instance))

    ret = {}
    for arg in foreach_arguments(instance):
        assert arg.attr is not None

        try:
            value = arg.__get__(instance)
        except AttributeError:
            pass
        else:
            ret[arg.attr] = value

    from .commands import get_sub_command_group
    if (sub := get_sub_command_group(instance)) is not None:
        assert sub.attr is not None

        try:
            value = sub.__get__(instance)
        except AttributeError:
            pass
        else:
            if value is None:
                ret[sub.attr] = None
            else:
                ret[sub.attr] = value

    return ret


def copy_argument(opt: T, ref, **kwargs) -> T:
    """copy argument from ``ref`` to ``opt``.

    :param opt: any instance that contains ``argument``.
    :param ref: any instance that contains ``argument``.
    :param kwargs: overwrite argument value mapping.
    :return: ``opt`` itself.
    """
    shadow = ShadowOption(ref, **kwargs)

    for arg in foreach_arguments(opt):
        assert arg.attr is not None

        try:
            value = getattr(shadow, arg.attr)
        except AttributeError:
            pass
        else:
            # print('set', arg.attr, value)
            arg.__set__(opt, value)

    from .commands import get_sub_command_group
    if (sub := get_sub_command_group(opt)) is not None:
        assert sub.attr is not None

        try:
            value = getattr(shadow, sub.attr)
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
