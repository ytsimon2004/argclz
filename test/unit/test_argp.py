import argparse
import builtins
import contextlib
import io
import re
import tempfile
import unittest
from pathlib import Path
from typing import Literal, Any
from unittest.mock import patch

from argclz import *
from argclz.clone import Cloneable
from argclz.core import foreach_arguments, with_defaults, as_dict, parse_args, copy_argument, new_parser, set_options, ArgumentParser, Argument

try:
    import polars as pl
except ImportError:
    pl = None

IMPORT = builtins.__import__


def block_polars_import(name, globals, locals, fromlist, level):
    if name == 'polars':
        raise ImportError

    return IMPORT(name, globals, locals, fromlist, level)


class WithDefaultTest(unittest.TestCase):
    def test_bool(self):
        class Opt:
            a: bool = argument('-a')

        opt = with_defaults(Opt())
        self.assertFalse(opt.a)

    def test_bool_set_false(self):
        class Opt:
            a: bool = argument('-a', default=True)

        opt = with_defaults(Opt())
        self.assertTrue(opt.a)

    def test_str(self):
        class Opt:
            a: str = argument('-a')

        opt = with_defaults(Opt())
        with self.assertRaises(AttributeError):
            _ = opt.a

    def test_optional(self):
        with self.subTest('optional'):
            class O2:
                a: str | None = argument('-a')

            self.assertIsNone(with_defaults(O2()).a)

        with self.subTest('union None'):
            class O3:
                a: str | int | None = argument('-a')

            self.assertIsNone(with_defaults(O3()).a)

    def test_default_str(self):
        class Opt:
            a: str = argument('-a', default='default')

        opt = with_defaults(Opt())
        self.assertEqual(opt.a, 'default')

    def test_int(self):
        class Opt:
            a: int = argument('-a')

        opt = with_defaults(Opt())
        with self.assertRaises(AttributeError):
            _ = opt.a

    def test_default_int(self):
        class Opt:
            a: int = argument('-a', default=101)

        opt = with_defaults(Opt())
        self.assertEqual(opt.a, 101)

    def test_float(self):
        class Opt:
            a: float = argument('-a')

        opt = with_defaults(Opt())
        with self.assertRaises(AttributeError):
            _ = opt.a

    def test_default_float(self):
        class Opt:
            a: float = argument('-a', default=3.14)

        opt = with_defaults(Opt())
        self.assertEqual(opt.a, 3.14)

    def test_literal(self):
        class Opt:
            a: Literal['A', 'B'] = argument('-a')

        opt = with_defaults(Opt())
        with self.assertRaises(AttributeError):
            _ = opt.a

    def test_default_literal(self):
        class Opt:
            a: Literal['A', 'B'] = argument('-a', default='C')

        opt = with_defaults(Opt())
        self.assertEqual(opt.a, 'C')


class AsDictTest(unittest.TestCase):
    def test_emtpy(self):
        class Opt:
            a: str = argument('-a', default='default')

        self.assertDictEqual(as_dict(Opt()), {})

    def test_as_dict(self):
        class Opt:
            a: str = argument('-a', default='default')

        opt = with_defaults(Opt())
        self.assertDictEqual(as_dict(opt), {'a': 'default'})

    def test_as_dict_on_list(self):
        class Opt(Cloneable):
            a: str = argument('-a', default='default')

        opt = [Opt(a=1), Opt(a=2), Opt(a=3)]
        self.assertListEqual(
            [{'a': 1}, {'a': 2}, {'a': 3}],
            as_dict(opt)
        )

        # on empty list
        self.assertListEqual([], as_dict([]))

    def test_on_sub_commands(self):
        class Opt(AbstractParser):
            a: str = argument('-a', default='Opt default')

            sub_command = sub_command_group()

            @sub_command('a')
            class Sub(AbstractParser):
                b: str = argument('-b', default='Sub default')

                def run(self):
                    pass

            def run(self):
                pass

        with self.subTest('none case'):
            main = Opt()
            ret = main.main([])
            self.assertIsInstance(ret, Opt)
            self.assertIsNone(main.sub_command)
            self.assertIsNone(ret.sub_command)
            self.assertDictEqual(as_dict(ret), {'a': 'Opt default', 'sub_command': None})

        with self.subTest('default case'):
            main = Opt()
            ret = main.main(['-a', '1'])
            self.assertIsInstance(ret, Opt)
            self.assertIsNone(main.sub_command)
            self.assertIsNone(ret.sub_command)
            self.assertDictEqual(as_dict(ret), {'a': '1', 'sub_command': None})

        with self.subTest('sub-command case'):
            main = Opt()
            ret = main.main(['a', '-b', '10'])
            self.assertIsInstance(main, Opt)
            self.assertIs(main.sub_command, Opt.Sub)
            self.assertIsInstance(ret, Opt.Sub)
            self.assertDictEqual(as_dict(ret), {'b': '10'})
            self.assertDictEqual(as_dict(main), {'a': 'Opt default', 'sub_command': Opt.Sub})

    @unittest.skipIf(pl is None, reason='no polars installed')
    def test_polars_data_frame_from_as_dict(self):
        from polars.testing import assert_frame_equal
        class Opt:
            a: int = argument('-a')
            b: str = argument('-b')

            def __init__(self, a, b):
                self.a, self.b = a, b

        df = pl.DataFrame(as_dict([Opt(1, '2'), Opt(3, '4')]))
        assert_frame_equal(df, pl.DataFrame({
            'a': [1, 3],
            'b': ['2', '4'],
        }))


class ForeachArgumentsTest(unittest.TestCase):
    def test_with_class(self):
        class Opt:
            a: str = argument('-a')
            b: str = argument('-b')

        args = list(foreach_arguments(Opt))
        self.assertEqual(2, len(args))
        self.assertEqual(args[0].attr, 'a')
        self.assertEqual(args[1].attr, 'b')

    def test_with_parent(self):
        class Parent:
            a: str = argument('-a')
            b: str = argument('-b')

        class Opt(Parent):
            c: str = argument('-c')
            d: str = argument('-d')

        args = list(foreach_arguments(Opt))
        self.assertEqual(4, len(args))
        # always start from Parent's arguments
        self.assertEqual(args[0].attr, 'a')
        self.assertEqual(args[1].attr, 'b')
        self.assertEqual(args[2].attr, 'c')
        self.assertEqual(args[3].attr, 'd')

    def test_with_argument_overwrite(self):
        class Parent:
            a: str = argument('-a')
            b: str = argument('-b')

        class Opt(Parent):
            c: str = argument('-c')
            b: str = as_argument(Parent.b).with_options()
            d: str = argument('-d')

        args = list(foreach_arguments(Opt))
        self.assertEqual(4, len(args))
        # always start from Parent's arguments
        self.assertEqual(args[0].attr, 'a')
        self.assertEqual(args[1].attr, 'b')
        self.assertEqual(args[2].attr, 'c')
        self.assertEqual(args[3].attr, 'd')

    def test_with_argument_remove(self):
        class Parent:
            a: str = argument('-a')
            b: str = argument('-b')

        class Opt(Parent):
            c: str = argument('-c')
            b: str = 'B'
            d: str = argument('-d')

        args = list(foreach_arguments(Opt))
        self.assertEqual(3, len(args))
        # always start from Parent's arguments
        self.assertEqual(args[0].attr, 'a')
        self.assertEqual(args[1].attr, 'c')
        self.assertEqual(args[2].attr, 'd')


class NewParserTest(unittest.TestCase):
    def test_new_parser_on_plain_class(self):
        class Opt:
            a: str = argument('-a')

        with self.subTest('prog'):
            ap = new_parser(Opt, prog='run.py')
            h = print_help(ap, None)
            self.assertEqual(h, """\
usage: run.py [-h] [-a A]

options:
  -h, --help  show this help message and exit
  -a A
""")

        with self.subTest('usage'):
            ap = new_parser(Opt, usage='python run.py [-h] [-a A]')
            h = print_help(ap, None)
            self.assertEqual(h, """\
usage: python run.py [-h] [-a A]

options:
  -h, --help  show this help message and exit
  -a A
""")

        with self.subTest('description'):
            ap = new_parser(Opt, prog='run.py', description='description text')
            h = print_help(ap, None)
            self.assertEqual(h, """\
usage: run.py [-h] [-a A]

description text

options:
  -h, --help  show this help message and exit
  -a A
""")

        with self.subTest('epilog'):
            ap = new_parser(Opt, prog='run.py', epilog='epilog text')
            h = print_help(ap, None)
            self.assertEqual(h, """\
usage: run.py [-h] [-a A]

options:
  -h, --help  show this help message and exit
  -a A

epilog text
""")

    def test_new_parser_on_abstract_parser(self):
        called = []

        class Main(AbstractParser):
            a: str = argument('-a', help='help text')

            @classmethod
            def new_parser(cls, **kwargs) -> ArgumentParser:
                called.append('yes')
                return super().new_parser(**kwargs)

        with self.subTest('new_parser(type)'):
            self.assertListEqual(called, [])
            _ = new_parser(Main)
            self.assertListEqual(called, ['yes'])

        with self.subTest('new_parser(instance)'):
            called.clear()
            self.assertListEqual(called, [])
            _ = new_parser(Main())
            self.assertListEqual(called, ['yes'])

    def test_new_parser_on_abstract_parser_overflow(self):
        called = []
        class Main(AbstractParser):
            a: str = argument('-a', help='help text')

            @classmethod
            def new_parser(cls, **kwargs) -> ArgumentParser:
                called.append('yes')
                # Here use wrong function to create new_parser.
                # It should be `super().new_parser(**kwargs)`.
                # However, using `new_parser` won't give caller a RecursionError.
                return new_parser(cls, **kwargs)

        with self.subTest('new_parser(type)'):
            self.assertListEqual(called, [])
            _ = new_parser(Main)
            self.assertListEqual(called, ['yes'])

        with self.subTest('new_parser(instance)'):
            called.clear()
            self.assertListEqual(called, [])
            _ = new_parser(Main())
            self.assertListEqual(called, ['yes'])

    def test_parse_args_on_abstract_parser(self):
        called = []

        class Main(AbstractParser):
            a: str = argument('-a', help='help text')

            @classmethod
            def new_parser(cls, **kwargs) -> ArgumentParser:
                called.append('yes')
                return super().new_parser(**kwargs)

        self.assertListEqual(called, [])
        _ = parse_args(Main(), [])
        self.assertListEqual(called, ['yes'])

    def test_new_parser_from_file_prefix(self):
        class Opt:
            a: str = argument('-a')

        with tempfile.NamedTemporaryFile('w+', dir='.', delete_on_close=False) as tf:
            print('-a', 'TEXT', sep='\n', file=tf)
            tf.close()

            opt = Opt()
            ap = new_parser(opt, fromfile_prefix_chars='@')
            set_options(opt, ap.parse_args([f'@{tf.name}']))

            self.assertEqual(opt.a, 'TEXT')

    def test_new_parser_allow_abbrev(self):
        class Opt:
            a: str = argument('--a-long-option-name')

        opt = Opt()

        with self.subTest('allow'):
            ap = new_parser(opt, allow_abbrev=True)
            set_options(opt, ap.parse_args(['--a-long', 'TEXT']))
            self.assertEqual(opt.a, 'TEXT')

        with self.subTest('not allow'):
            ap = new_parser(opt, allow_abbrev=False)
            with self.assertRaises(RuntimeError):
                ap.parse_args(['--a-long', 'TEXT'])

    # noinspection PyArgumentList
    def test_new_parser_unsupported_keywords(self):
        class Opt:
            a: str = argument('-a')

        with self.assertRaises(ValueError):
            new_parser(Opt, parents=[])

        with self.assertRaises(ValueError):
            new_parser(Opt, prefix_chars='/')

        with self.assertRaises(ValueError):
            new_parser(Opt, argument_default=object())

        with self.assertRaises(ValueError):
            new_parser(Opt, exit_on_error=False)

        with self.assertRaises(ValueError):
            new_parser(Opt, conflict_handler='error')


class AbstractParserTest(unittest.TestCase):
    def test_parser_init(self):
        class Main(AbstractParser):
            a: str = argument('-a')
            b: str = argument('-b', default=None)
            c: str = argument('-c', default='default')

        main = Main()
        with self.assertRaises(AttributeError):
            _ = main.a
        self.assertIsNone(main.b)
        self.assertEqual(main.c, 'default')

    def test_parser_init_type(self):
        class Main(AbstractParser):
            a: int = argument('-a')
            b: bool = argument('-b')
            b2: bool = argument('-b2', action='store_true')
            b3: bool = argument('-b3', action='store_false')
            c: list[str] = argument('-c', action='append')
            d: list[str] = argument('-d', action='extend')
            e: list[str] = argument('-e', action='append_const')

        main = Main()

        with self.subTest('AttributeError'):
            with self.assertRaises(AttributeError):
                _ = main.a

        with self.subTest('bool'):
            self.assertFalse(main.b)
            self.assertFalse(main.b2)
            self.assertTrue(main.b3)

        with self.subTest('list'):
            self.assertListEqual(main.c, [])
            self.assertListEqual(main.d, [])
            self.assertListEqual(main.e, [])

    def test_exit_on_error(self):
        class Main(AbstractParser):
            a: str = argument('-a', default='default')

        with contextlib.redirect_stderr(io.StringIO()):
            with self.assertRaises(SystemExit):
                Main().main(['-b'])

        with self.assertRaises(RuntimeError):
            Main().main(['-b'], system_exit=RuntimeError)

        with self.assertRaises(RuntimeError):
            parse_args(Main(), ['-b'])

    def test_parse_only(self):
        class Main(AbstractParser):
            a: int = argument('-a')

            def run(self):
                raise RuntimeError('message')

        with self.assertRaises(RuntimeError) as capture:
            Main().main(['-a=1'])

        self.assertEqual(capture.exception.args[0], 'message')

        main = Main()
        ret = main.main(['-a=1'], parse_only=True)
        self.assertIs(ret, main)
        self.assertEqual(ret.a, 1)

    def test_add_help(self):
        class Main(AbstractParser):
            a: int = argument('-a')

        output = io.StringIO()

        with contextlib.redirect_stdout(output):
            with self.assertRaises(SystemExit) as capture:
                Main().main(['-h'])

        self.assertEqual(capture.exception.args[0], 0)
        self.assertEqual(re.sub(r'usage: .* \[-h]', 'usage: run.py [-h]', output.getvalue()), """\
usage: run.py [-h] [-a A]

options:
  -h, --help  show this help message and exit
  -a A
""")

    def test_add_h_argument(self):
        class Main(AbstractParser):
            h: int = argument('-h')

        # conflict with ArgumentParser(add_help)
        # The error is raised during parser initialization phase rather parsing phase,
        # so argparse.ArgumentError is raised.
        with self.assertRaises(argparse.ArgumentError):
            Main().main(['-h=1'])

    def test_add_h_argument_force(self):
        class Main(AbstractParser):
            h: int = argument('-h')

            @classmethod
            def new_parser(cls, **kwargs):
                return super().new_parser(**kwargs, add_help=False)

        ret = Main().main(['-h=1'])
        self.assertEqual(ret.h, 1)

    def test_parer_with_empty_args(self):
        class Main(AbstractParser):
            h: int = argument('-a')

        ret = Main().main([])
        self.assertEqual(ret.h, None)

    def test_duplicate_argument_attr(self):
        # we have no way to detect this improper setup
        class Main(AbstractParser):
            a: int = argument('-a1')
            a: int = argument('-a2')

        Main.new_parser()

    def test_duplicate_argument_options(self):
        # we have no way to detect this improper setup during class declaration
        class Main(AbstractParser):
            a1: int = argument('-a')
            a2: int = argument('-a')

        with self.assertRaises(argparse.ArgumentError) as capture:
            Main.new_parser()
        self.assertEqual(str(capture.exception),
                         'argument -a: conflicting option string: -a')


class ArgumentsTest(unittest.TestCase):
    def test_argument_default(self):
        class Opt:
            a: str = argument('-a', default='DEFAULT')
            b: str = argument('-b')

        self.assertEqual(as_argument(Opt.a).default, 'DEFAULT')

        with self.assertRaises(ValueError):
            _ = as_argument(Opt.b).default

    def test_argument_default_inferred(self):
        class Opt:
            b: bool = argument('-b')
            b1: bool = argument('-b1', action='store_true')
            b2: bool = argument('-b2', action='store_false')
            c1: list[str] = argument('-c1', action='append')
            c2: list[str] = argument('-c2', action='extend')
            c3: list[str] = argument('-c3', action='append_const')

        self.assertFalse(as_argument(Opt.b).default)
        self.assertFalse(as_argument(Opt.b1).default)
        self.assertTrue(as_argument(Opt.b2).default)

        self.assertListEqual(as_argument(Opt.c1).default, [])
        self.assertListEqual(as_argument(Opt.c2).default, [])
        self.assertListEqual(as_argument(Opt.c3).default, [])

    def test_argument_const(self):
        class Opt:
            a: str = argument('-a', const='VALUE')
            b: str = argument('-b')

        self.assertEqual(as_argument(Opt.a).const, 'VALUE')

        with self.assertRaises(ValueError):
            _ = as_argument(Opt.b).const

    def test_argument_const_inferred(self):
        class Opt:
            b1: bool = argument('-a', action='store_true')
            b2: bool = argument('-a', action='store_false')

        self.assertTrue(as_argument(Opt.b1).const)
        self.assertFalse(as_argument(Opt.b2).const)

    def test_argument_metavar(self):
        class Opt:
            a: str = argument('-a', metavar='VALUE')
            b: str = argument('-b')

        self.assertEqual(as_argument(Opt.a).metavar, 'VALUE')
        self.assertIsNone(as_argument(Opt.b).metavar)

    def test_argument_nargs(self):
        class Opt:
            a: str = argument('-a', nargs=1)
            b: str = argument('-b', nargs='?')
            c: str = argument('-c')

        self.assertEqual(as_argument(Opt.a).nargs, 1)
        self.assertEqual(as_argument(Opt.b).nargs, '?')
        self.assertIsNone(as_argument(Opt.c).nargs)

    def test_argument_choices(self):
        class Opt:
            a: str = argument('-a', choices=('A', 'B'))
            b: str = argument('-b', choices=['A', 'B'])
            c: str = argument('-c')

        self.assertEqual(as_argument(Opt.a).choices, ('A', 'B'))
        self.assertEqual(as_argument(Opt.b).choices, ('A', 'B'))
        self.assertIsNone(as_argument(Opt.c).choices)

    def test_argument_required(self):
        class Opt:
            a: str = argument('-a', required=True)
            b: str = argument('-b')

        self.assertTrue(as_argument(Opt.a).required)
        self.assertFalse(as_argument(Opt.b).required)

    def test_argument_help(self):
        class Opt:
            a: str = argument('-a', help='HELP')
            b: str = argument('-b', help='{DEFAULT}', default='TEXT')
            c: str = argument('-c')

        self.assertEqual(as_argument(Opt.a).help, 'HELP')
        self.assertEqual(as_argument(Opt.b).help, "'TEXT'")
        self.assertIsNone(as_argument(Opt.c).help)

    def test_argument_type(self):
        def e_type(a: str):
            raise NotImplementedError

        class FType:
            pass

        class Opt:
            a: str = argument('-a')
            b: int = argument('-b')
            c: float = argument('-c')
            d: bool = argument('-d')
            e: Any = argument('-e', type=e_type)
            f: FType = argument('-f')
            g: list[str] = argument('-g')
            p: Path = argument('-p')

        with self.subTest('value type'):
            self.assertIs(as_argument(Opt.a).type, str)
            self.assertIs(as_argument(Opt.b).type, int)
            self.assertIs(as_argument(Opt.c).type, float)

        with self.subTest('simple type'):
            from argclz.types import bool_type
            self.assertIs(as_argument(Opt.d).type, bool_type)

        with self.subTest('user given'):
            self.assertIs(as_argument(Opt.e).type, e_type)

        with self.subTest('class case'):
            self.assertIs(as_argument(Opt.f).type, FType)
            self.assertIs(as_argument(Opt.p).type, Path)

        with self.subTest('collection case'):
            self.assertIs(as_argument(Opt.g).type, str)

    def test_argument_type_tuple(self):
        # we do not interpret Opt.a case as same as Opt.b case,
        # because tuple_type does the value parsing (value splitting)
        class Opt:
            a: tuple[str, ...] = argument('-a')
            b: tuple[str, ...] = argument('-b', type=tuple_type(str, ...))
            c: tuple[str, str, str] = argument('-c', nargs=3, type=str)

        with self.subTest('tuple'):
            self.assertIs(as_argument(Opt.a).type, tuple)
            opt = parse_args(Opt(), ['-a=TEXT'])
            self.assertTupleEqual(opt.a, ('T', 'E', 'X', 'T'))

        with self.subTest('tuple_type'):
            self.assertIsNot(as_argument(Opt.b).type, tuple)
            opt = parse_args(Opt(), ['-b=TEXT'])
            self.assertTupleEqual(opt.b, ('TEXT',))
            opt = parse_args(Opt(), ['-b=T1,T2,T3'])
            self.assertTupleEqual(opt.b, ('T1', 'T2', 'T3'))

        with self.subTest('type=str'):
            opt = parse_args(Opt(), ['-c', 'T1', 'T2', 'T3'])
            # noinspection PyTypeChecker
            self.assertListEqual(opt.c, ['T1', 'T2', 'T3'])  # not a tuple

    def test_argument_type_list(self):
        class Opt:
            a: list[str] = argument('-a')
            b: list[str] = argument('-b', nargs='+')
            c: list[str] = argument('-c', nargs='+', action='extend')
            d: list[str] = var_argument('...')  # positional arguments

        with self.subTest('list'):
            self.assertIs(as_argument(Opt.a).type, str)
            self.assertEqual(as_argument(Opt.a).kwargs['action'], 'append')

            opt = parse_args(Opt(), ['-a=TEXT'])
            self.assertListEqual(opt.a, ['TEXT'])

        with self.subTest('nargs append'):
            self.assertIs(as_argument(Opt.b).type, str)
            self.assertEqual(as_argument(Opt.b).kwargs['action'], 'append')
            self.assertEqual(as_argument(Opt.b).nargs, '+')

            opt = parse_args(Opt(), ['-b', 'T1', 'T2', 'T3'])
            self.assertListEqual(opt.b, [['T1', 'T2', 'T3']])

        with self.subTest('nargs extend'):
            self.assertIs(as_argument(Opt.c).type, str)
            self.assertEqual(as_argument(Opt.c).kwargs['action'], 'extend')
            self.assertEqual(as_argument(Opt.c).nargs, '+')

            opt = parse_args(Opt(), ['-c', 'T1', 'T2', 'T3'])
            self.assertListEqual(opt.c, ['T1', 'T2', 'T3'])

        with self.subTest('var_argument'):
            self.assertIs(as_argument(Opt.d).type, str)
            self.assertEqual(as_argument(Opt.d).kwargs['action'], 'extend')
            self.assertEqual(as_argument(Opt.d).nargs, '*')

            opt = parse_args(Opt(), ['T1', 'T2', 'T3'])
            self.assertListEqual(opt.d, ['T1', 'T2', 'T3'])

    def test_argument_type_dict(self):
        class Opt:
            a: dict[str, str] = argument('-a')
            b: dict[str, str] = argument('-b', type=dict_type(str))

        with self.subTest('dict'):
            self.assertIs(as_argument(Opt.a).type, dict)

            with self.assertRaises(RuntimeError) as capture:
                parse_args(Opt(), ['-aK=TEXT'])
            self.assertEqual(capture.exception.args[0],
                             "exit 2: argument -a: invalid dict value: 'K=TEXT'")

        with self.subTest('dict_type'):
            self.assertIsNot(as_argument(Opt.b).type, dict)
            self.assertIsInstance(as_argument(Opt.b).type, dict_type)  # abstract leak

            opt = parse_args(Opt(), ['-bK=TEXT'])
            self.assertDictEqual(opt.b, {'K': 'TEXT'})

    # noinspection PyUnusedLocal
    def test_option_wrong_prefix(self):
        with self.assertRaises(ValueError):
            class Opt:
                a: str = argument('@a')

    def test_set_argument_repeat(self):
        class Opt:
            a: str = argument('-a')

        with self.assertRaises(RuntimeError) as capture:
            parse_args(Opt(), ['-a', '-a'])
        self.assertEqual(capture.exception.args[0],
                         'exit 2: argument -a: expected one argument')

    def test_required_argument(self):
        class Opt:
            a: str = argument('-a', required=True)

        self.assertEqual(parse_args(Opt(), ['-a=1']).a, '1')

        with self.assertRaises(RuntimeError) as capture:
            parse_args(Opt(), [])
        self.assertEqual(capture.exception.args[0],
                         'exit 2: the following arguments are required: -a')

    def test_alias_argument(self):
        class Opt:
            a: str = aliased_argument('-a', aliases={
                '-b': 'B',
                '-c': 'C',
            })

        self.assertEqual(parse_args(Opt(), ['-a=1']).a, '1')
        self.assertEqual(parse_args(Opt(), ['-b']).a, 'B')
        self.assertEqual(parse_args(Opt(), ['-c']).a, 'C')

        with self.assertRaises(RuntimeError) as capture:
            parse_args(Opt(), ['-b', '-c'])
        self.assertEqual(capture.exception.args[0],
                         'exit 2: argument -c: not allowed with argument -b')

    def test_attribute_naming(self):
        class Opt:
            a: str = argument('-a')

            def __init__(self):
                self._a = 'one underscore'
                self.__a = 'two underscores'

            def get_a(self):
                return self._a

            def get__a(self):
                return self.__a

        # command-line argument should not affect other attributes
        opt = parse_args(Opt(), ['-a=from_command_line'])
        self.assertEqual(opt.a, 'from_command_line')
        self.assertEqual(opt.get_a(), 'one underscore')
        self.assertEqual(opt.get__a(), 'two underscores')

    def test_option_reuse(self):
        class Opt:
            a: str = argument('-a')
            b: str = argument('-b')

        opt = parse_args(Opt(), ['-a=A', '-b=B'])
        self.assertEqual(opt.a, 'A')
        self.assertEqual(opt.b, 'B')
        opt = parse_args(opt, ['-a=B'])
        self.assertEqual(opt.a, 'B')
        self.assertEqual(opt.b, None)

    def test_argument_with_default_value(self):
        class Opt:
            a: str = argument('-a').with_default('DEFAULT')

        with self.subTest('attribute'):
            arg = as_argument(Opt.a)
            self.assertEqual(arg.default, 'DEFAULT')

            with self.assertRaises(ValueError):
                _ = arg.const

        with self.subTest('parsing'):
            opt = parse_args(Opt(), [])
            self.assertEqual(opt.a, 'DEFAULT')
            opt = parse_args(Opt(), ['-a=TEXT'])
            self.assertEqual(opt.a, 'TEXT')

            with self.assertRaises(RuntimeError):
                parse_args(Opt(), ['-a'])

    def test_argument_with_omit_value(self):
        class Opt:
            a: str = argument('-a').with_default('DEFAULT', 'VALUE')

        with self.subTest('attribute'):
            arg = as_argument(Opt.a)
            self.assertEqual(arg.default, 'DEFAULT')
            self.assertEqual(arg.const, 'VALUE')
            self.assertEqual(arg.nargs, '?')

        with self.subTest('parsing'):
            opt = parse_args(Opt(), [])
            self.assertEqual(opt.a, 'DEFAULT')
            opt = parse_args(Opt(), ['-a'])
            self.assertEqual(opt.a, 'VALUE')
            opt = parse_args(Opt(), ['-a=TEXT'])
            self.assertEqual(opt.a, 'TEXT')

    def test_unknown_argument(self):
        class Opt:
            a: str = argument('-a', default='default')

        with self.assertRaises(RuntimeError) as capture:
            parse_args(Opt(), ['-b'])
        self.assertEqual(capture.exception.args[0],
                         'exit 2: unrecognized arguments: -b')

    def test_pos_argument(self):
        class Opt:
            a: str = pos_argument('A')

        self.assertEqual(as_argument(Opt.a).metavar, 'A')
        self.assertTupleEqual(as_argument(Opt.a).options, ())
        opt = parse_args(Opt(), ['TEXT'])
        self.assertEqual(opt.a, 'TEXT')

    # noinspection PyUnusedLocal
    def test_pos_argument_with_dash(self):
        with self.assertRaises(ValueError) as capture:
            class Opt:
                a: str = pos_argument('-a')
        self.assertEqual(capture.exception.args[0],
                         "positional argument startswith '-': -a")

class ArgumentDescriptorTest(unittest.TestCase):
    def test_replace_descriptor(self):
        namespace = {}

        class Descriptor:
            def __get_arg__(self, instance, name: str):
                try:
                    return namespace[name]
                except KeyError:
                    pass

                raise AttributeError(name)

            def __set_arg__(self, instance, name: str, value):
                namespace[name] = value

            def __del_arg__(self, instance, name: str):
                try:
                    del namespace[name]
                except (AttributeError, KeyError):
                    pass

        class Opt:
            a: str = argument('-a', descriptor=Descriptor)

        self.assertIsInstance(as_argument(Opt.a).descriptor, Descriptor)

        opt = parse_args(Opt(), ['-a=test'])
        self.assertEqual(opt.a, 'test')
        self.assertDictEqual(namespace, {'a': 'test'})

    def test_use_case(self):
        # It is idea proof case that shows we can do more things on the end of argument parsing.
        # In the same case but without this approach, we might need to write hidden attribute and
        # property, etc. The benefit of using descriptor class is that class is reusable.
        from argclz.desp import DefaultArgumentDescriptor

        class Descriptor(DefaultArgumentDescriptor):
            def __get_arg__(self, instance, name: str):
                file = super().__get_arg__(instance, name)
                if file is None:
                    return None

                content_attr = f'__{name}_content'
                try:
                    content = super().__get_arg__(instance, content_attr)
                except AttributeError:
                    content = Path(file).read_text()
                    self.__set_arg__(instance, content_attr, content)

                return content

            @classmethod
            def clear_content(cls, instance, arg: Argument | Any):
                # Use Any on *arg* type to avoid using as_argument() on caller side
                # It skips hinter complain and additional import.
                # However, we still need type checking.
                if not isinstance(arg, Argument):
                    raise TypeError('not an argument')

                descriptor = arg.descriptor
                if not isinstance(descriptor, Descriptor):
                    raise RuntimeError('argument does have correct descriptor')

                content_attr = f'__{arg.attr}_content'
                descriptor.__set_arg__(instance, content_attr, None)

        # a convenient function
        def file_argument(*options, **kwargs) -> str:
            return argument(*options, **kwargs, descriptor=Descriptor())

        class Opt:
            a: str = file_argument('-a')

            def clear_a_content(self):
                Descriptor.clear_content(self, Opt.a)

            # equivalent without descriptor
            _b: str = argument('-b')
            _b_content: str | None

            @property
            def b(self) -> str | None:
                if self._b is None:
                    return None

                try:
                    content = self._b_content
                except AttributeError:
                    content = Path(self._b).read_text()
                    self._b_content = content

                return content

            def clear_b_content(self):
                self._b_content = None

        def read_text(self: Path):
            if self.name == '123.txt':
                return '321'
            else:
                raise FileNotFoundError()

        with patch.object(Path, 'read_text', new=read_text):
            opt = parse_args(Opt(), ['-a=123.txt'])
            self.assertEqual(opt.a, '321')
            opt.clear_a_content()
            self.assertIsNone(opt.a)

            opt = parse_args(Opt(), ['-b=123.txt'])
            self.assertEqual(opt.b, '321')
            opt.clear_b_content()
            self.assertIsNone(opt.b)


class GroupTest(unittest.TestCase):
    # XXX Is help text the only way to test argument grouping?

    # grouping doesn't affect paring behavior, so we do not need to test it.

    def test_group_literal_str(self):
        class Opt:
            a: str = argument('-a', help='not in group')
            b: str = argument('-b', group='Group', help='in group')
            c: str = argument('-c', group='Group', help='in group')

        h = print_help(Opt, None, prog='run.py')
        self.assertEqual(h, """\
usage: run.py [-h] [-a A] [-b B] [-c C]

options:
  -h, --help  show this help message and exit
  -a A        not in group

Group:
  -b B        in group
  -c C        in group
""")

    def test_group_argument_group(self):
        class Opt:
            g = argument_group('Group', 'Group Description')
            a: str = argument('-a', help='not in group')
            b: str = argument('-b', group=g, help='in group')
            c: str = argument('-c', group=g, help='in group')

        h = print_help(Opt, None, prog='run.py')
        self.assertEqual(h, """\
usage: run.py [-h] [-a A] [-b B] [-c C]

options:
  -h, --help  show this help message and exit
  -a A        not in group

Group:
  Group Description

  -b B        in group
  -c C        in group
""")

    def test_argument_group_argument(self):
        class Opt:
            g = argument_group('Group', 'Group Description')
            a: str = argument('-a', help='not in group')
            b: str = g.argument('-b', help='in group')
            c: str = g.argument('-c', help='in group')

        h = print_help(Opt, None, prog='run.py')
        self.assertEqual(h, """\
usage: run.py [-h] [-a A] [-b B] [-c C]

options:
  -h, --help  show this help message and exit
  -a A        not in group

Group:
  Group Description

  -b B        in group
  -c C        in group
""")

    def test_unnamed_group_are_distinct(self):
        class Opt:
            g1 = argument_group()
            g2 = argument_group()
            a: str = argument('-a', group=g1)
            b: str = argument('-b', group=g1)
            c: str = argument('-c', group=g2)
            d: str = argument('-d', group=g2)

        h = print_help(Opt, None, prog='run.py')
        self.assertEqual(h, """\
usage: run.py [-h] [-a A] [-b B] [-c C] [-d D]

options:
  -h, --help  show this help message and exit

  -a A
  -b B

  -c C
  -d D
""")

    def test_ex_group_argument_group(self):
        class Opt:
            g = argument_group('Group', 'Group Description', exclusive=True)
            a: str = argument('-a', help='not in group')
            b: str = argument('-b', group=g, help='in group')
            c: str = argument('-c', group=g, help='in group')

        h = print_help(Opt, None, prog='run.py')
        self.assertEqual(h, """\
usage: run.py [-h] [-a A] [-b B | -c C]

options:
  -h, --help  show this help message and exit
  -a A        not in group

Group:
  Group Description

  -b B        in group
  -c C        in group
""")

    def test_ex_argument_group_argument(self):
        class Opt:
            g = argument_group('Group', 'Group Description', exclusive=True)
            a: str = argument('-a', help='not in group')
            b: str = g.argument('-b', help='in group')
            c: str = g.argument('-c', help='in group')

        h = print_help(Opt, None, prog='run.py')
        self.assertEqual(h, """\
usage: run.py [-h] [-a A] [-b B | -c C]

options:
  -h, --help  show this help message and exit
  -a A        not in group

Group:
  Group Description

  -b B        in group
  -c C        in group
""")

    def test_ex_argument_group_argument_required(self):
        class Opt:
            g = argument_group('Group', 'Group Description', exclusive=True, required=True)
            a: str = argument('-a', help='not in group')
            b: str = g.argument('-b', help='in group')
            c: str = g.argument('-c', help='in group')

        h = print_help(Opt, None, prog='run.py')
        self.assertEqual(h, """\
usage: run.py [-h] [-a A] (-b B | -c C)

options:
  -h, --help  show this help message and exit
  -a A        not in group

Group:
  Group Description

  -b B        in group
  -c C        in group
""")

    def test_ex_group(self):
        class Opt:
            g = argument_group(exclusive=True)
            a: bool = argument('-a')
            b: bool = argument('-b', group=g)
            c: bool = argument('-c', group=g)

        with self.subTest('normal case'):
            opt = parse_args(Opt(), ['-a', '-b'])
            self.assertTrue(opt.a)
            self.assertTrue(opt.b)
            self.assertFalse(opt.c)

            opt = parse_args(Opt(), ['-c'])
            self.assertFalse(opt.a)
            self.assertFalse(opt.b)
            self.assertTrue(opt.c)

        with self.subTest('error case'):
            with self.assertRaises(RuntimeError) as capture:
                parse_args(Opt(), ['-b', '-c'])
            self.assertEqual(capture.exception.args[0],
                             'exit 2: argument -c: not allowed with argument -b')

    def test_ex_group_required(self):
        class Opt:
            g = argument_group(exclusive=True, required=True)
            a: bool = argument('-a')
            b: bool = argument('-b', group=g)
            c: bool = argument('-c', group=g)

        with self.subTest('normal case'):
            opt = parse_args(Opt(), ['-a', '-b'])
            self.assertTrue(opt.a)
            self.assertTrue(opt.b)
            self.assertFalse(opt.c)

            opt = parse_args(Opt(), ['-c'])
            self.assertFalse(opt.a)
            self.assertFalse(opt.b)
            self.assertTrue(opt.c)

        with self.subTest('error case'):
            with self.assertRaises(RuntimeError) as capture:
                parse_args(Opt(), ['-a'])
            self.assertEqual(capture.exception.args[0],
                             'exit 2: one of the arguments -b -c is required')

    def test_unnamed_ex_group_are_distinct(self):
        class Opt:
            g1 = argument_group(exclusive=True)
            g2 = argument_group(exclusive=True)
            a: str = argument('-a', group=g1)
            b: str = argument('-b', group=g1)
            c: str = argument('-c', group=g2)
            d: str = argument('-d', group=g2)

        with self.subTest('parsing success'):
            opt = parse_args(Opt(), ['-aT', '-cT'])
            self.assertEqual(opt.a, 'T')
            self.assertEqual(opt.b, None)
            self.assertEqual(opt.c, 'T')
            self.assertEqual(opt.d, None)

        with self.subTest('parsing fail'):
            with self.assertRaises(RuntimeError):
                parse_args(Opt(), ['-aT', '-bT'])
            with self.assertRaises(RuntimeError):
                parse_args(Opt(), ['-cT', '-dT'])

        with self.subTest('help text'):
            # show distinct in usage
            h = print_help(Opt, None, prog='run.py')
            self.assertEqual(h, """\
usage: run.py [-h] [-a A | -b B] [-c C | -d D]

options:
  -h, --help  show this help message and exit
  -a A
  -b B
  -c C
  -d D
""")

    def test_back_compatible_ex_group(self):
        # argument(ex_group) is deprecated now, but it is not removed yet.
        with self.assertWarns(DeprecationWarning) as capture:
            class Opt:
                a: str = argument('-a', help='not in group')
                b: str = argument('-b', ex_group='Group', help='in group')
                c: str = argument('-c', ex_group='Group', help='in group')

            h = print_help(Opt, None, prog='run.py')

        self.assertEqual(capture.warnings[0].message.args[0], 'ex_group is deprecated')
        self.assertEqual(h, """\
usage: run.py [-h] [-a A] [-b B | -c C]

options:
  -h, --help  show this help message and exit
  -a A        not in group

Group:
  -b B        in group
  -c C        in group
""")


class CopyArgsTest(unittest.TestCase):
    def test_copy_argument(self):
        class Opt:
            a: str = argument('-a')

        opt = parse_args(Opt(), ['-a=2'])
        self.assertEqual(opt.a, '2')
        ano = copy_argument(Opt(), opt)
        self.assertEqual(ano.a, '2')

    def test_copy_argument_partial_updating(self):
        class Opt:
            a: str = argument('-a')
            b: str = argument('-b')

        opt = parse_args(Opt(), [])
        self.assertEqual(opt.a, None)
        self.assertEqual(opt.b, None)

        ano = copy_argument(opt, None, a='2')
        self.assertIs(opt, ano)
        self.assertEqual(ano.a, '2')
        self.assertEqual(ano.b, None)

        ret = copy_argument(opt, ano, b='B')
        self.assertIs(ret, ano)
        self.assertEqual(ret.a, '2')
        self.assertEqual(ret.b, 'B')

    def test_copy_from_dict(self):
        class Opt:
            a: str = argument('-a')

        ano = copy_argument(Opt(), None, a='2')
        self.assertEqual(ano.a, '2')

    def test_with_dongle_attr(self):
        class Opt:
            _a: str = argument('-a')

        opt = copy_argument(Opt(), None, a='A')
        self.assertEqual(opt._a, 'A')

    def test_copy_argument_from_opt_and_dict(self):
        class Opt:
            a: str = argument('-a')
            b: str = argument('-b')

        opt = copy_argument(Opt(), None, a='A', b='B')
        self.assertEqual(opt.a, 'A')
        self.assertEqual(opt.b, 'B')

        ano = copy_argument(Opt(), opt, b='C')
        self.assertEqual(ano.a, 'A')
        self.assertEqual(ano.b, 'C')

    def test_copy_also_include_parent_opts(self):
        class Parent:
            a: str = argument('-a')

        class Opt(Parent):
            b: str = argument('-b')

        opt = copy_argument(Opt(), None, a='A', b='B')
        self.assertEqual(opt.a, 'A')
        self.assertEqual(opt.b, 'B')

        ano = copy_argument(Opt(), opt, b='C')
        self.assertEqual(ano.a, 'A')
        self.assertEqual(ano.b, 'C')

    @unittest.skipIf(pl is None, reason='no polars installed')
    def test_set_from_polars_data_frame(self):
        class Opt:
            a: int = argument('-a')
            b: str = argument('-b')

        df = pl.DataFrame({'a': [0, 1], 'b': ['2', '3']})
        for row in df.iter_rows(named=True):
            opt = copy_argument(Opt(), None, **row)
            self.assertEqual(opt.a, row['a'])
            self.assertEqual(opt.b, row['b'])

    def test_copy_argument_from_distinct_opt_class(self):
        class Opt1:
            a: str = argument('-a')

        class Opt2:
            a: str = argument('-a')

        opt = parse_args(Opt1(), ['-a=2'])
        self.assertEqual(opt.a, '2')

        ano = copy_argument(Opt2(), opt)
        self.assertEqual(ano.a, '2')

    def test_cloneable(self):
        class Opt(Cloneable):
            a: str = argument('-a')

        opt = parse_args(Opt(), ['-a=2'])
        self.assertEqual(opt.a, '2')

        ano = Opt(opt)
        self.assertEqual(ano.a, '2')

    def test_cloneable_on_dict(self):
        class Opt(Cloneable):
            a: str = argument('-a')
            b: str = argument('-b')

        opt = Opt({'a': 'A', 'b': 'B'})
        self.assertEqual(opt.a, 'A')
        self.assertEqual(opt.b, 'B')

    def test_cloneable_by_keywords(self):
        class Opt(Cloneable):
            a: str = argument('-a')
            b: str = argument('-b')

        opt = Opt(a='A', b='B')
        self.assertEqual(opt.a, 'A')
        self.assertEqual(opt.b, 'B')

    @patch('builtins.__import__', block_polars_import)
    def test_cloneable_without_polars(self):
        try:
            import polars
        except ImportError:
            pass
        else:
            self.fail('polar should not be imported in this test')

        class Opt(Cloneable):
            a: str = argument('-a')

        opt = parse_args(Opt(), ['-a=2'])
        self.assertEqual(opt.a, '2')

        ano = Opt(opt)
        self.assertEqual(ano.a, '2')

    @unittest.skipIf(pl is None, reason='no polars installed')
    def test_cloneable_from_dataframe(self):
        class Opt(Cloneable):
            a: str = argument('-a')

        data = pl.DataFrame([{'a': '2'}])
        opt = Opt(data)
        self.assertEqual(opt.a, '2')

    def test_with_sub_commands(self):
        class Opt(AbstractParser):
            a: str = argument('-a', default='Opt default')

            sub_command = sub_command_group()

            @sub_command('a')
            class Sub(AbstractParser):
                b: str = argument('-b', default='Sub default')

                def run(self):
                    pass

            def run(self):
                pass

        with self.subTest('empty case'):
            main = Opt()
            ret = main.main([])
            self.assertIsInstance(ret, Opt)
            self.assertIsNone(main.sub_command)
            self.assertIsNone(ret.sub_command)

            ano = copy_argument(Opt(), ret)
            self.assertIsInstance(ano, Opt)
            self.assertIsNone(ano.sub_command)
            self.assertIsNone(ano.sub_command)

        with self.subTest('parent case'):
            main = Opt()
            ret = main.main(['-a', '10'])
            self.assertIsInstance(ret, Opt)
            self.assertIsNone(main.sub_command)
            self.assertIsNone(ret.sub_command)
            self.assertEqual(ret.a, '10')

            ano = copy_argument(Opt(), ret)
            self.assertIsInstance(ano, Opt)
            self.assertIsNone(ano.sub_command)
            self.assertIsNone(ano.sub_command)
            self.assertEqual(ano.a, '10')

        with self.subTest('sub command case'):
            main = Opt()
            ret = main.main(['a', '-b', '10'])
            self.assertIsInstance(ret, Opt.Sub)
            self.assertIs(main.sub_command, Opt.Sub)
            self.assertEqual(main.a, 'Opt default')
            self.assertEqual(ret.b, '10')

            ano = copy_argument(Opt(), main)
            self.assertIsInstance(ano, Opt)
            self.assertIs(ano.sub_command, Opt.Sub)
            self.assertEqual(ano.a, 'Opt default')

            ano = copy_argument(Opt.Sub(), ret)
            self.assertIsInstance(ano, Opt.Sub)
            self.assertEqual(ano.b, '10')

    def test_copy_argument_used_as_option_extending(self):
        class Main(AbstractParser):
            a: str = argument('-a')
            b: str = argument('-b')
            c: str = argument('-c')  # protected
            d: dict[str, str] = argument('-d', type=dict_type(str))

            def run(self):
                if len(self.d):
                    d = dict(self.d)
                    d.pop('c', None)  # c is protected
                    copy_argument(self, None, **d)

        with self.subTest('no copy_argument'):
            ret = Main().main(['-aA', '-bB', '-cC'])
            self.assertEqual(ret.a, 'A')
            self.assertEqual(ret.b, 'B')
            self.assertEqual(ret.c, 'C')
            self.assertDictEqual(ret.d, {})

        with self.subTest('parse_only'):
            ret = Main().main(['-da=A', '-db=B', '-dc=C'], parse_only=True)
            self.assertEqual(ret.a, None)
            self.assertEqual(ret.b, None)
            self.assertEqual(ret.c, None)
            self.assertDictEqual(ret.d, {'a': 'A', 'b': 'B', 'c': 'C'})

        with self.subTest('with copy_argument'):
            ret = Main().main(['-da=A', '-db=B', '-dc=C'])
            self.assertEqual(ret.a, 'A')
            self.assertEqual(ret.b, 'B')
            self.assertEqual(ret.c, None)
            self.assertDictEqual(ret.d, {'a': 'A', 'b': 'B', 'c': 'C'})


class WithOptionsTest(unittest.TestCase):
    def test_no_args(self):
        class Parent:
            a: str = argument('-a')

        class Child(Parent):
            a: str = as_argument(Parent.a).with_options()

        p = as_argument(Parent.a)
        c = as_argument(Child.a)
        self.assertEqual(p.options, c.options)
        self.assertEqual(p.kwargs, c.kwargs)

    def test_replace_options(self):
        class Parent:
            a: str = argument('-a')

        class Child(Parent):
            a: str = as_argument(Parent.a).with_options('-b')

        p = as_argument(Parent.a)
        c = as_argument(Child.a)
        self.assertEqual(p.options, ('-a',))
        self.assertEqual(c.options, ('-b',))
        self.assertEqual(p.kwargs, c.kwargs)

    def test_add_options(self):
        class Parent:
            a: str = argument('-a')

        class Child(Parent):
            a: str = as_argument(Parent.a).with_options(..., '-b')

        p = as_argument(Parent.a)
        c = as_argument(Child.a)
        self.assertEqual(p.options, ('-a',))
        self.assertEqual(c.options, ('-a', '-b'))
        self.assertEqual(p.kwargs, c.kwargs)

    def test_rename_options(self):
        class Parent:
            a: str = argument('-a', '--long')

        class Child(Parent):
            a: str = as_argument(Parent.a).with_options({'-a': '-b'})

        p = as_argument(Parent.a)
        c = as_argument(Child.a)
        self.assertEqual(p.options, ('-a', '--long'))
        self.assertEqual(c.options, ('-b', '--long'))
        self.assertEqual(p.kwargs, c.kwargs)

    def test_remove_options(self):
        class Parent:
            a: str = argument('-a', '--long')

        for new_value in [..., None]:
            with self.subTest(f'rename({new_value})'):
                class Child(Parent):
                    a: str = as_argument(Parent.a).with_options({'-a': new_value})

                p = as_argument(Parent.a)
                c = as_argument(Child.a)
                self.assertEqual(p.options, ('-a', '--long'))
                self.assertEqual(c.options, ('--long',))
                self.assertEqual(p.kwargs, c.kwargs)

    def test_change_pos_arg(self):
        class Parent:
            a: str = pos_argument('A')

        with self.subTest('by metavar'):
            class Child(Parent):
                a: str = as_argument(Parent.a).with_options(metavar='B')

            self.assertEqual(as_argument(Parent.a).metavar, 'A')
            self.assertEqual(as_argument(Child.a).metavar, 'B')
            self.assertTupleEqual(as_argument(Parent.a).options, ())
            self.assertTupleEqual(as_argument(Child.a).options, ())

        with self.subTest('by options'):
            class Child(Parent):
                a: str = as_argument(Parent.a).with_options('B')

            self.assertEqual(as_argument(Parent.a).metavar, 'A')
            self.assertEqual(as_argument(Child.a).metavar, 'B')
            self.assertTupleEqual(as_argument(Parent.a).options, ())
            self.assertTupleEqual(as_argument(Child.a).options, ())

    # noinspection PyUnusedLocal,PyRedeclaration
    def test_change_pos_by_removing(self):
        class Parent:
            a: str = pos_argument('A')

        # Although argparse still works, which might take dest (aka 'a') as its metavar,
        # we do not want that.
        with self.subTest('metavar=...'):
            with self.assertRaises(ValueError) as capture:
                class Child(Parent):
                    a: str = as_argument(Parent.a).with_options(metavar=...)
            self.assertEqual(capture.exception.args[0],
                             'missing metavar')

        with self.subTest('metavar=None'):
            with self.assertRaises(ValueError) as capture:
                class Child(Parent):
                    a: str = as_argument(Parent.a).with_options(metavar=None)
            self.assertEqual(capture.exception.args[0],
                             'missing metavar')

    # noinspection PyUnusedLocal,PyRedeclaration
    def test_error_on_change_pos_to_opt(self):
        class Parent:
            a: str = pos_argument('A')

        with self.subTest('single options'):
            with self.assertRaises(ValueError) as capture:
                class Child(Parent):
                    a: str = as_argument(Parent.a).with_options('-a')
            self.assertEqual(capture.exception.args[0],
                             'cannot change positional argument to optional')

        with self.subTest('many options'):
            with self.assertRaises(ValueError) as capture:
                class Child(Parent):
                    a: str = as_argument(Parent.a).with_options('-a', '--aa')
            self.assertEqual(capture.exception.args[0],
                             'cannot change positional argument to optional')

    # noinspection PyUnusedLocal
    def test_error_on_change_opt_to_pos(self):
        class Parent:
            a: str = argument('-a')

        with self.assertRaises(ValueError) as capture:
            class Child(Parent):
                a: str = as_argument(Parent.a).with_options('a')
        self.assertEqual(capture.exception.args[0],
                         "options should startswith '-': a")

    def test_remove_keyword(self):
        class Parent:
            a: int = argument('-a', type=int)

        class Child(Parent):
            a: str = as_argument(Parent.a).with_options(type=...)

        self.assertEqual(parse_args(Parent(), ['-a=1']).a, 1)
        self.assertEqual(parse_args(Child(), ['-a=1']).a, '1')


if __name__ == '__main__':
    unittest.main()
