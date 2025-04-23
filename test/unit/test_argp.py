import builtins
import unittest
from typing import Literal
from unittest import skipIf
from unittest.mock import patch

from argclz import *
from argclz.clone import Cloneable
from argclz.core import with_defaults, as_dict, parse_args, copy_argument

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
            a = opt.a

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
            a = opt.a

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
            a = opt.a

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
            a = opt.a

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


class AbstractParserTest(unittest.TestCase):
    def test_exit_on_error(self):
        class Main(AbstractParser):
            a: str = argument('-a', default='default')

        with self.assertRaises(SystemExit):
            Main().main(['-b'], system_exit=True)

        with self.assertRaises(RuntimeError):
            Main().main(['-b'], system_exit=RuntimeError)

        ret = Main().main(['-b'], system_exit=False)
        self.assertNotEqual(ret.exit_status, 0)

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
        self.assertIsNone(ret.exit_status)
        self.assertEqual(main.a, 1)


class TestArguments(unittest.TestCase):
    def test_required_argument(self):
        class Opt:
            a: str = argument('-a', required=True)

        self.assertEqual(parse_args(Opt(), ['-a=1']).a, '1')

        with self.assertRaises(RuntimeError):
            parse_args(Opt(), [])

    def test_alias_argument(self):
        class Opt:
            a: str = aliased_argument('-a', aliases={
                '-b': 'B',
                '-c': 'C',
            })

        self.assertEqual(parse_args(Opt(), ['-a=1']).a, '1')
        self.assertEqual(parse_args(Opt(), ['-b']).a, 'B')
        self.assertEqual(parse_args(Opt(), ['-c']).a, 'C')


class CopyArgsTest(unittest.TestCase):
    def test_copy_argument(self):
        class Opt:
            a: str = argument('-a')

        opt = parse_args(Opt(), ['-a=2'])
        self.assertEqual(opt.a, '2')
        ano = copy_argument(Opt(), opt)
        self.assertEqual(ano.a, '2')

    def test_copy_argument_from_dict(self):
        class Opt:
            a: str = argument('-a')

        ano = copy_argument(Opt(), None, a='2')
        self.assertEqual(ano.a, '2')

    def test_copy_argument_from_distinct(self):
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

    @patch('builtins.__import__', block_polars_import)
    def test_cloneable_without_polars(self):
        try:
            import polars
        except ImportError:
            pass
        else:
            self.fail()

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


if __name__ == '__main__':
    unittest.main()
