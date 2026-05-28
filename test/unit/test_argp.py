import argparse
import builtins
import contextlib
import io
import re
import unittest
from typing import Literal
from unittest import skipIf
from unittest.mock import patch

from argclz import *
from argclz.clone import Cloneable
from argclz.core import foreach_arguments, with_defaults, as_dict, parse_args, copy_argument, new_parser

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

    @skipIf(pl is None, reason='no polars installed')
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


class AbstractParserTest(unittest.TestCase):
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
        self.assertEqual(re.sub(r'\w+\.py', 'run.py', output.getvalue()), """\
usage: run.py [-h] [-a A]

options:
  -h, --help  show this help message and exit
  -a A
""")

    def test_add_h_argument(self):
        class Main(AbstractParser):
            h: int = argument('-h')

        with self.assertRaises(argparse.ArgumentError):
            Main().main(['-h=1'])

    def test_add_h_argument_force(self):
        class Main(AbstractParser):
            h: int = argument('-h')

            @classmethod
            def new_parser(cls, **kwargs):
                return new_parser(cls, **kwargs, add_help=False)

        ret = Main().main(['-h=1'])
        self.assertEqual(ret.h, 1)


class TestArguments(unittest.TestCase):
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


class CopyArgsTest(unittest.TestCase):
    def test_copy_argument(self):
        class Opt:
            a: str = argument('-a')

        opt = parse_args(Opt(), ['-a=2'])
        self.assertEqual(opt.a, '2')
        ano = copy_argument(Opt(), opt)
        self.assertEqual(ano.a, '2')

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

    @skipIf(pl is None, reason='no polars installed')
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

    @skipIf(pl is None, reason='no polars installed')
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

        class Child(Parent):
            a: str = as_argument(Parent.a).with_options({'-a': ...})

        p = as_argument(Parent.a)
        c = as_argument(Child.a)
        self.assertEqual(p.options, ('-a', '--long'))
        self.assertEqual(c.options, ('--long',))
        self.assertEqual(p.kwargs, c.kwargs)

    def test_error_on_change_pos_to_opt(self):
        class Parent:
            a: str = pos_argument('A')

        with self.assertRaises(RuntimeError):
            class Child(Parent):
                a: str = as_argument(Parent.a).with_options('-a')

    def test_remove_keyword(self):
        class Parent:
            a: int = argument('-a', type=int)

        class Child(Parent):
            a: str = as_argument(Parent.a).with_options(type=...)

        self.assertEqual(parse_args(Parent(), ['-a=1']).a, 1)
        self.assertEqual(parse_args(Child(), ['-a=1']).a, '1')


if __name__ == '__main__':
    unittest.main()
